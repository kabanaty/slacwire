"""Qt-free display and logging rules for the wire speed status widget."""

import logging

from slac_devices.wire import SpeedState

PLANES = ("x", "y", "u")

ALARM_STATES = (SpeedState.TOO_FAST, SpeedState.TOO_SLOW)
ALARM_TEXT = {SpeedState.TOO_FAST: "Too Fast", SpeedState.TOO_SLOW: "Too Slow"}

OK_STYLE = "color: darkgreen;"
ALARM_STYLE = "color: red; font-weight: bold;"
ALARM_FIELD_STYLE = "border: 2px solid red;"

UNKNOWN = "unknown"


def speed_summary(status) -> str:
    """Short status text for display next to the range fields."""
    match status.state:
        case SpeedState.OK:
            return "OK"
        case SpeedState.TOO_FAST:
            return "Too fast: range too large"
        case SpeedState.TOO_SLOW:
            return "Too slow: range too small"
        case SpeedState.NO_BEAM:
            return "No beam rate"
        case SpeedState.BAD_RANGE:
            return "Inner must be less than outer"


def speed_advice(status) -> str:
    """How to fix an invalid speed, as a range-width target ('' when OK).

    Never suggests changing scan pulses: operators fix speed with the range.
    """
    match status.state:
        case SpeedState.OK:
            return ""
        case SpeedState.TOO_FAST:
            return f"Narrow the range to less than {status.max_width:.0f} um"
        case SpeedState.TOO_SLOW:
            return f"Widen the range to more than {status.min_width:.0f} um"
        case SpeedState.NO_BEAM:
            return "Wait for beam to return"
        case SpeedState.BAD_RANGE:
            return "Inner must be less than outer"


def in_alarm(status, active: bool) -> bool:
    """True when an active plane's speed is too fast or too slow."""
    return active and status is not None and status.state in ALARM_STATES


def column_visible(statuses, active) -> bool:
    """The Speed column is shown only while at least one plane is in alarm."""
    return any(in_alarm(statuses.get(p), p in active) for p in PLANES)


def describe_plane(status, active: bool):
    """Return (label text, label style, tooltip, field style) for one plane.

    Alarmed planes show "Too Fast" or "Too Slow" with the fix in the tooltip;
    other active planes show "OK". Inactive or unreadable planes are blank.
    """
    if in_alarm(status, active):
        return (
            ALARM_TEXT[status.state],
            ALARM_STYLE,
            speed_advice(status),
            ALARM_FIELD_STYLE,
        )
    if active and status is not None and status.valid:
        return ("OK", OK_STYLE, "", "")
    return ("", "", "", "")


def profile_message(plane: str, status) -> str:
    """One-line log message, e.g. 'X Profile too slow: range too small. Widen ...'."""
    name = f"{plane.upper()} Profile"
    if status is None:
        return f"{name} speed unknown: PVs unavailable"
    if status.valid:
        return f"{name} speed OK"
    summary = speed_summary(status)
    advice = speed_advice(status)
    message = f"{name} {summary.lower()}"
    if not advice or advice.lower() == summary.lower():
        return message
    return f"{message}. {advice}"


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
