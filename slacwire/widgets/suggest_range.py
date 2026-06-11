"""Widget for suggesting scan ranges from BPM orbit data."""

from __future__ import annotations

from PyQt5.QtCore import QThread, pyqtSignal
from qtpy.QtWidgets import (
    QGroupBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
)

from slacwire.orbit_range import SuggestedRange, suggest_scan_range


class _PredictionThread(QThread):
    finished = pyqtSignal(object)

    def __init__(self, wire, beampath, half_window_um, parent=None):
        super().__init__(parent)
        self.wire = wire
        self.beampath = beampath
        self.half_window_um = half_window_um

    def run(self):
        result = suggest_scan_range(
            wire=self.wire,
            beampath=self.beampath,
            half_window_um=self.half_window_um,
        )
        self.finished.emit(result)


class SuggestRangeWidget(QGroupBox):
    """Reads BPM orbit and suggests scan range centered on the beam."""

    rangeAccepted = pyqtSignal(str, list)

    def __init__(self, parent=None):
        super().__init__("Range Suggestion", parent)
        self._wire = None
        self._beampath = ""
        self._thread = None
        self._result: SuggestedRange | None = None

        self._build_ui()

    def _build_ui(self):
        layout = QGridLayout()

        self.suggest_btn = QPushButton("Suggest Range")
        self.suggest_btn.setEnabled(False)
        self.suggest_btn.clicked.connect(self._on_suggest_clicked)
        layout.addWidget(self.suggest_btn, 0, 0, 1, 2)

        layout.addWidget(QLabel("Half window (um):"), 1, 0)
        self.half_window_spin = QSpinBox()
        self.half_window_spin.setRange(1000, 20000)
        self.half_window_spin.setSingleStep(500)
        self.half_window_spin.setValue(5000)
        layout.addWidget(self.half_window_spin, 1, 1)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label, 2, 0, 1, 2)

        self.x_label = QLabel("X: —")
        self.y_label = QLabel("Y: —")
        self.u_label = QLabel("U: —")
        layout.addWidget(self.x_label, 3, 0, 1, 2)
        layout.addWidget(self.y_label, 4, 0, 1, 2)
        layout.addWidget(self.u_label, 5, 0, 1, 2)

        btn_layout = QHBoxLayout()
        self.accept_btn = QPushButton("Accept All")
        self.accept_btn.setEnabled(False)
        self.accept_btn.clicked.connect(self._on_accept_all)
        btn_layout.addWidget(self.accept_btn)
        layout.addLayout(btn_layout, 6, 0, 1, 2)

        self.setLayout(layout)

    def set_context(self, wire, beampath: str):
        self._wire = wire
        self._beampath = beampath
        self.suggest_btn.setEnabled(wire is not None)
        self._clear_results()

    def _clear_results(self):
        self._result = None
        self.x_label.setText("X: —")
        self.y_label.setText("Y: —")
        self.u_label.setText("U: —")
        self.status_label.setText("")
        self.accept_btn.setEnabled(False)

    def _on_suggest_clicked(self):
        if self._wire is None:
            return
        self.suggest_btn.setEnabled(False)
        self.status_label.setText("Reading BPM orbit...")

        self._thread = _PredictionThread(
            wire=self._wire,
            beampath=self._beampath,
            half_window_um=self.half_window_spin.value(),
        )
        self._thread.finished.connect(self._on_prediction_complete)
        self._thread.start()

    def _on_prediction_complete(self, result: SuggestedRange):
        self._result = result
        self.suggest_btn.setEnabled(True)

        if result.status != "ok":
            self.status_label.setText(f"⚠ {result.message}")
            self.accept_btn.setEnabled(False)
            return

        self.status_label.setText(f"BPM: {result.bpm_name} (x={result.bpm_x_mm:.2f}, y={result.bpm_y_mm:.2f} mm)")
        self.x_label.setText(f"X: {result.x_range[0]} → {result.x_range[1]} um  (center {result.x_center:.0f})")
        self.y_label.setText(f"Y: {result.y_range[0]} → {result.y_range[1]} um  (center {result.y_center:.0f})")
        self.u_label.setText(f"U: {result.u_range[0]} → {result.u_range[1]} um")
        self.accept_btn.setEnabled(True)

    def _on_accept_all(self):
        if self._result is None or self._result.status != "ok":
            return
        if self._result.x_range:
            self.rangeAccepted.emit("x", list(self._result.x_range))
        if self._result.y_range:
            self.rangeAccepted.emit("y", list(self._result.y_range))
        if self._result.u_range:
            self.rangeAccepted.emit("u", list(self._result.u_range))
        self.status_label.setText("Ranges applied.")
