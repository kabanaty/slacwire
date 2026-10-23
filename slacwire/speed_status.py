"""Qt-free display and logging rules for the wire speed status widget."""

import logging

from slac_devices.wire import SpeedState

PLANES = ("x", "y", "u")

OK_STYLE = "color: darkgreen;"
INVALID_STYLE = "color: red; font-weight: bold;"
INACTIVE_STYLE = "color: gray;"
UNKNOWN_STYLE = "color: darkorange;"
INVALID_FIELD_STYLE = "border: 2px solid red;"

UNKNOWN = "unknown"


def describe_plane(status, active: bool):
    """Return (label text, label style, tooltip, field style) for one plane.

    ``status`` is a RangeStatus, or None when the PVs could not be read.
    """
    if status is None:
        return (
            "Speed unknown",
            UNKNOWN_STYLE,
            "Could not read the wire speed PVs.",
            "",
        )
    if not active:
        return ("Not used", INACTIVE_STYLE, status.advice, "")
    if status.valid:
        return (status.summary, OK_STYLE, status.advice, "")
    return (status.summary, INVALID_STYLE, status.advice, INVALID_FIELD_STYLE)


def transition_level(previous, current):
    """Return the log level for a plane's state change, or None to stay quiet.

    ``previous`` and ``current`` are (state, active) tuples, where state is a
    SpeedState or UNKNOWN. ``previous`` is None on the first reading.

    - Inactive planes are never logged.
    - Becoming invalid or unknown logs a warning (including on first reading).
    - Recovering to OK logs info, but only after a logged problem.
    """
    state, active = current
    if not active or previous == current:
        return None
    was_problem = previous is not None and previous[1] and previous[0] != SpeedState.OK
    if state == SpeedState.OK:
        return logging.INFO if was_problem else None
    return logging.WARNING
