import logging
import unittest
from types import SimpleNamespace

from slac_devices.wire import SpeedState

from slacwire.speed_status import (
    ALARM_FIELD_STYLE,
    PLANES,
    column_visible,
    describe_plane,
    profile_message,
    transition_level,
)


def _status(state, plane="x", summary="", advice=""):
    return SimpleNamespace(
        plane=plane,
        state=state,
        valid=state == SpeedState.OK,
        summary=summary,
        advice=advice,
    )


class TestDescribePlane(unittest.TestCase):
    def test_alarm_states_are_terse(self):
        for state, text in [
            (SpeedState.TOO_FAST, "Too Fast"),
            (SpeedState.TOO_SLOW, "Too Slow"),
        ]:
            label, _, tooltip, field_style = describe_plane(
                _status(state, advice="Widen the range"), active=True
            )
            self.assertEqual(label, text)
            self.assertEqual(tooltip, "Widen the range")
            self.assertEqual(field_style, ALARM_FIELD_STYLE)

    def test_ok_plane_reads_ok(self):
        label, _, _, field_style = describe_plane(_status(SpeedState.OK), active=True)
        self.assertEqual(label, "OK")
        self.assertEqual(field_style, "")

    def test_inactive_plane_is_blank(self):
        label, _, _, field_style = describe_plane(
            _status(SpeedState.TOO_FAST), active=False
        )
        self.assertEqual(label, "")
        self.assertEqual(field_style, "")


class TestColumnVisible(unittest.TestCase):
    def test_hidden_when_all_ok(self):
        statuses = {p: _status(SpeedState.OK, p) for p in PLANES}
        self.assertFalse(column_visible(statuses, ["x", "y", "u"]))

    def test_shown_when_any_active_plane_alarms(self):
        statuses = {p: _status(SpeedState.OK, p) for p in PLANES}
        statuses["y"] = _status(SpeedState.TOO_SLOW, "y")
        self.assertTrue(column_visible(statuses, ["x", "y", "u"]))

    def test_inactive_alarm_does_not_show_column(self):
        statuses = {p: _status(SpeedState.OK, p) for p in PLANES}
        statuses["u"] = _status(SpeedState.TOO_FAST, "u")
        self.assertFalse(column_visible(statuses, ["x", "y"]))


class TestProfileMessage(unittest.TestCase):
    def test_alarm_message(self):
        status = _status(
            SpeedState.TOO_SLOW,
            summary="Too slow: range too small",
            advice="Widen the range to more than 2917 um",
        )
        self.assertEqual(
            profile_message("x", status),
            "X Profile too slow: range too small. Widen the range to more than 2917 um",
        )

    def test_recovery_message(self):
        self.assertEqual(profile_message("y", _status(SpeedState.OK)), "Y Profile speed OK")


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
