"""Live per-plane wire speed status for the Parameters panel.

The IOC calculates each plane's scan speed from the range, beam rate and scan
pulses. Inner and outer are separate PVs, so the speed can be briefly invalid
while an operator is part way through editing a range. Instead of checking
each write, this widget re-checks the current settings once a second and
shows a Speed column only while an active plane is too fast or too slow:
alarmed planes read "Too Fast"/"Too Slow" (fix in the tooltip, red border on
the range fields) and the other active planes read "OK".

Polling runs on a worker thread because ``PV.get()`` blocks on a
disconnected PV, which would freeze the GUI.
"""

import logging

from PyQt5.QtCore import QObject, QThread, QTimer, pyqtSignal, pyqtSlot
from qtpy.QtWidgets import QLabel

from slacwire.speed_status import (
    PLANES,
    UNKNOWN,
    column_visible,
    describe_plane,
    profile_message,
    transition_level,
)

POLL_INTERVAL_MS = 1000


class _SpeedPoller(QObject):
    """Reads plane statuses off the GUI thread."""

    statusesReady = pyqtSignal(object, object)

    @pyqtSlot(object)
    def poll(self, wire):
        statuses = {}
        active = []
        try:
            active = wire.active_profiles()
        except Exception:
            pass
        for plane in PLANES:
            try:
                statuses[plane] = wire.range_status(plane)
            except Exception:
                statuses[plane] = None
        self.statusesReady.emit(wire, (statuses, active))


class SpeedStatusMonitor(QObject):
    """Keeps the per-plane speed labels and range-field borders up to date."""

    pollRequested = pyqtSignal(object)

    def __init__(
        self, header, labels, range_fields, logger: logging.Logger, parent=None
    ):
        """
        Args:
            header: QLabel heading the Speed column.
            labels: {plane: QLabel} status label for each plane.
            range_fields: {plane: [QWidget, ...]} inner/outer fields per plane.
            logger: Logger shown in the GUI's activity log.
        """
        super().__init__(parent)
        self.header = header
        self.labels = labels
        self.range_fields = range_fields
        self.logger = logger
        self.wire = None
        self._paused = False
        self._busy = False
        self._last = {}
        self._default_field_styles = {
            plane: [w.styleSheet() for w in widgets]
            for plane, widgets in range_fields.items()
        }

        self._thread = QThread(self)
        self._poller = _SpeedPoller()
        self._poller.moveToThread(self._thread)
        self.pollRequested.connect(self._poller.poll)
        self._poller.statusesReady.connect(self._on_statuses)
        self._thread.start()

        self._timer = QTimer(self)
        self._timer.setInterval(POLL_INTERVAL_MS)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()

    def set_wire(self, wire) -> None:
        """Switch to a new wire and refresh immediately."""
        self.wire = wire
        self._last = {}
        self.refresh()

    def pause(self) -> None:
        """Stop polling, e.g. while a scan is running."""
        self._paused = True

    def resume(self) -> None:
        self._paused = False
        self.refresh()

    def refresh(self) -> None:
        if self.wire is None or self._paused or self._busy:
            return
        self._busy = True
        self.pollRequested.emit(self.wire)

    def stop(self) -> None:
        self._timer.stop()
        self._thread.quit()
        self._thread.wait()

    def _on_statuses(self, wire, result) -> None:
        self._busy = False
        if wire is not self.wire:
            return
        statuses, active = result
        self._set_column_visible(column_visible(statuses, active))
        for plane in PLANES:
            status = statuses.get(plane)
            is_active = plane in active
            self._update_plane(plane, status, is_active)
            self._log_transition(plane, status, is_active)

    def _set_column_visible(self, visible: bool) -> None:
        self.header.setVisible(visible)
        for label in self.labels.values():
            label.setVisible(visible)

    def _update_plane(self, plane: str, status, active: bool) -> None:
        text, style, tooltip, field_style = describe_plane(status, active)
        label = self.labels.get(plane)
        if label is not None:
            label.setText(text)
            label.setStyleSheet(style)
            label.setToolTip(tooltip)
        defaults = self._default_field_styles.get(plane, [])
        for widget, default in zip(self.range_fields.get(plane, []), defaults):
            widget.setStyleSheet(field_style or default)
            widget.setToolTip(tooltip if field_style else "")

    def _log_transition(self, plane: str, status, active: bool) -> None:
        state = status.state if status is not None else UNKNOWN
        current = (state, active)
        previous = self._last.get(plane)
        self._last[plane] = current
        level = transition_level(previous, current)
        if level is None:
            return
        self.logger.log(level, profile_message(plane, status))


def build_speed_labels(grid_layout, column: int = 3):
    """Add a hidden Speed column (header + one label per plane) to the grid.

    Rows follow the Parameters grid: header in row 0, X/Y/U in rows 1-3.
    Returns (header, {plane: label}).
    Object names end in ``Label`` so ``update_parameters`` does not try to
    bind them to PVs.
    """
    header = QLabel("Speed")
    header.setObjectName("SpeedStatusHeaderLabel")
    grid_layout.addWidget(header, 0, column)
    labels = {}
    for row, plane in enumerate(PLANES, start=1):
        label = QLabel("")
        label.setObjectName(f"{plane}_speed_statusLabel")
        label.setVisible(False)
        grid_layout.addWidget(label, row, column)
        labels[plane] = label
    header.setVisible(False)
    return header, labels


__all__ = [
    "PLANES",
    "SpeedStatusMonitor",
    "build_speed_labels",
]
