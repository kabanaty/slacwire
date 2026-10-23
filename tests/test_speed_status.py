import logging
import unittest
from types import SimpleNamespace

from slac_devices.wire import SpeedState

from slacwire.speed_status import (
    INVALID_FIELD_STYLE,
    describe_plane,
    transition_level,
)


def _status(state, valid):
    return SimpleNamespace(
        state=state, valid=valid, summary=f"summary {state}", advice=f"advice {state}"
    )


class TestDescribePlane(unittest.TestCase):
    def test_invalid_active_plane_gets_red_fields_and_advice(self):
        text, _, tooltip, field_style = describe_plane(
            _status(SpeedState.TOO_FAST, False), active=True
        )
        self.assertEqual(text, "summary SpeedState.TOO_FAST")
        self.assertEqual(tooltip, "advice SpeedState.TOO_FAST")
        self.assertEqual(field_style, INVALID_FIELD_STYLE)

    def test_inactive_plane_is_not_flagged(self):
        text, _, _, field_style = describe_plane(
            _status(SpeedState.TOO_FAST, False), active=False
        )
        self.assertEqual(text, "Not used")
        self.assertEqual(field_style, "")

    def test_valid_plane(self):
        _, _, _, field_style = describe_plane(_status(SpeedState.OK, True), active=True)
        self.assertEqual(field_style, "")

    def test_unreadable_pvs(self):
        text, _, _, _ = describe_plane(None, active=True)
        self.assertEqual(text, "Speed unknown")


class TestTransitionLevel(unittest.TestCase):
    def test_first_reading_ok_is_quiet(self):
        self.assertIsNone(transition_level(None, (SpeedState.OK, True)))

    def test_first_reading_invalid_warns(self):
        self.assertEqual(
            transition_level(None, (SpeedState.TOO_SLOW, True)), logging.WARNING
        )

    def test_repeated_state_is_quiet(self):
        state = (SpeedState.TOO_FAST, True)
        self.assertIsNone(transition_level(state, state))

    def test_recovery_logs_info(self):
        self.assertEqual(
            transition_level((SpeedState.TOO_FAST, True), (SpeedState.OK, True)),
            logging.INFO,
        )

    def test_change_between_problems_warns(self):
        self.assertEqual(
            transition_level((SpeedState.TOO_FAST, True), (SpeedState.TOO_SLOW, True)),
            logging.WARNING,
        )

    def test_inactive_plane_is_quiet(self):
        self.assertIsNone(transition_level(None, (SpeedState.TOO_FAST, False)))

    def test_ok_after_inactive_is_quiet(self):
        self.assertIsNone(
            transition_level((SpeedState.TOO_FAST, False), (SpeedState.OK, True))
        )


if __name__ == "__main__":
    unittest.main()
