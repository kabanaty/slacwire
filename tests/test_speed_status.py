import logging
import unittest
from slac_devices.wire import RangeStatus, SpeedState

from slacwire.speed_status import (
    ALARM_FIELD_STYLE,
    PLANES,
    column_visible,
    describe_plane,
    profile_message,
    speed_advice,
    speed_summary,
    transition_level,
)

# Representative speed for each state with a 1000 um range,
# speed_floor 100 um/s and speed_max 1200 um/s.
_SPEEDS = {
    SpeedState.OK: 500.0,
    SpeedState.TOO_FAST: 1500.0,  # max_width 800 um
    SpeedState.TOO_SLOW: 50.0,  # min_width 2000 um
    SpeedState.NO_BEAM: 500.0,
    SpeedState.BAD_RANGE: 500.0,
}


def _status(state, profile="x"):
    return RangeStatus(
        profile=profile,
        state=state,
        speed=_SPEEDS[state],
        speed_floor=100.0,
        speed_max=1200.0,
        inner=0.0,
        outer=1000.0,
        scan_pulses=240,
        beam_rate=0.0 if state == SpeedState.NO_BEAM else 120.0,
    )


class TestSpeedText(unittest.TestCase):
    def test_summary_per_state(self):
        expected = {
            SpeedState.OK: "OK",
            SpeedState.TOO_FAST: "Too fast: range too large",
            SpeedState.TOO_SLOW: "Too slow: range too small",
            SpeedState.NO_BEAM: "No beam rate",
            SpeedState.BAD_RANGE: "Inner must be less than outer",
        }
        for state, text in expected.items():
            self.assertEqual(speed_summary(_status(state)), text)

    def test_advice_per_state(self):
        expected = {
            SpeedState.OK: "",
            SpeedState.TOO_FAST: "Narrow the range to less than 800 um",
            SpeedState.TOO_SLOW: "Widen the range to more than 2000 um",
            SpeedState.NO_BEAM: "Wait for beam to return",
            SpeedState.BAD_RANGE: "Inner must be less than outer",
        }
        for state, text in expected.items():
            self.assertEqual(speed_advice(_status(state)), text)

    def test_every_state_has_text(self):
        for state in SpeedState:
            self.assertTrue(speed_summary(_status(state)))
            self.assertIsNotNone(speed_advice(_status(state)))

    def test_advice_never_mentions_scan_pulses(self):
        for state in SpeedState:
            self.assertNotIn("pulses", speed_advice(_status(state)))


class TestDescribePlane(unittest.TestCase):
    def test_alarm_states_are_terse(self):
        for state, text, tip in [
            (SpeedState.TOO_FAST, "Too Fast", "Narrow the range to less than 800 um"),
            (SpeedState.TOO_SLOW, "Too Slow", "Widen the range to more than 2000 um"),
        ]:
            label, _, tooltip, field_style = describe_plane(_status(state), active=True)
            self.assertEqual(label, text)
            self.assertEqual(tooltip, tip)
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
        status = _status(SpeedState.TOO_SLOW)
        self.assertEqual(
            profile_message("x", status),
            "X Profile too slow: range too small. Widen the range to more than 2000 um",
        )

    def test_advice_matching_summary_is_not_repeated(self):
        status = _status(SpeedState.BAD_RANGE)
        self.assertEqual(
            profile_message("x", status), "X Profile inner must be less than outer"
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
