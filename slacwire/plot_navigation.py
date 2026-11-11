"""Qt-free axis-limit math for interactive plot panning and zooming.

Wheel deltas use Qt's ``angleDelta`` units: one standard mouse-wheel notch
is 120. Trackpads report smaller, continuous values in the same units.
"""

WHEEL_NOTCH = 120
PAN_FRACTION_PER_NOTCH = 0.1
ZOOM_FACTOR_PER_NOTCH = 0.8


def pan_limits(limits: tuple[float, float], delta: float) -> tuple[float, float]:
    """Shift limits by a fraction of the visible span.

    Positive ``delta`` (wheel up / swipe left) moves the view toward lower values.
    """
    lo, hi = limits
    shift = -(delta / WHEEL_NOTCH) * PAN_FRACTION_PER_NOTCH * (hi - lo)
    return lo + shift, hi + shift


def zoom_limits(
    limits: tuple[float, float], center: float, delta: float
) -> tuple[float, float]:
    """Scale limits about ``center``, keeping that point fixed on screen.

    Positive ``delta`` (wheel up) zooms in; negative zooms out.
    """
    lo, hi = limits
    factor = ZOOM_FACTOR_PER_NOTCH ** (delta / WHEEL_NOTCH)
    return center - (center - lo) * factor, center + (hi - center) * factor
