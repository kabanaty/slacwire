import pytest

from slacwire.plot_navigation import WHEEL_NOTCH, pan_limits, zoom_limits


def test_pan_wheel_up_moves_view_toward_lower_values():
    assert pan_limits((0.0, 100.0), WHEEL_NOTCH) == pytest.approx((-10.0, 90.0))


def test_pan_wheel_down_moves_view_toward_higher_values():
    assert pan_limits((0.0, 100.0), -WHEEL_NOTCH) == pytest.approx((10.0, 110.0))


def test_pan_preserves_span_for_fractional_trackpad_delta():
    lo, hi = pan_limits((-50.0, 50.0), 30)
    assert hi - lo == pytest.approx(100.0)


def test_zoom_in_keeps_center_fixed():
    lo, hi = zoom_limits((0.0, 100.0), 25.0, WHEEL_NOTCH)
    assert (lo, hi) == pytest.approx((5.0, 85.0))
    # Cursor point stays at the same fraction of the view
    assert (25.0 - lo) / (hi - lo) == pytest.approx(0.25)


def test_zoom_out_then_in_round_trips():
    zoomed = zoom_limits((0.0, 100.0), 40.0, -WHEEL_NOTCH)
    assert zoom_limits(zoomed, 40.0, WHEEL_NOTCH) == pytest.approx((0.0, 100.0))
