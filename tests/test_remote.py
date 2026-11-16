"""Tests for the stdin/stdout remote-control protocol (slacwire.remote, ws_gui)."""

import contextlib
import io
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

try:
    from slacwire.remote import StdinCommandReader
except ModuleNotFoundError:  # PyQt5 not installed
    StdinCommandReader = None

try:
    from slacwire.ws_gui import WireScanSuiteGUI
except ModuleNotFoundError:  # pydm / Qt not installed
    WireScanSuiteGUI = None


@unittest.skipIf(StdinCommandReader is None, "PyQt5 not available")
class StdinCommandReaderTests(unittest.TestCase):
    def _run(self, stdin_text):
        reader = StdinCommandReader()
        received = []
        reader.commandReceived.connect(received.append)
        with patch("sys.stdin", io.StringIO(stdin_text)):
            reader.run()  # synchronous; no thread needed
        return received

    def test_blank_lines_are_skipped(self):
        self.assertEqual(
            self._run("SCAN WS1\n\n  \nGET WS1\nQUIT\n"),
            ["SCAN WS1", "GET WS1", "QUIT"],
        )

    def test_stops_reading_after_quit(self):
        self.assertEqual(self._run("QUIT\nSCAN WS1\n"), ["QUIT"])

    def test_eof_without_quit_emits_quit(self):
        self.assertEqual(self._run("SCAN WS1\n"), ["SCAN WS1", "QUIT"])

    def test_empty_stdin_emits_quit(self):
        self.assertEqual(self._run(""), ["QUIT"])


@unittest.skipIf(WireScanSuiteGUI is None, "pydm not available")
class HandleRemoteCommandTests(unittest.TestCase):
    """Every SCAN/GET/unknown-command error must be followed by READY."""

    def _gui(self, idle=True, wire_found=True):
        def navigate(wire, detector=None):
            if not wire_found:
                print(f"ERROR:Wire '{wire}' not found", flush=True)
            return wire_found

        return SimpleNamespace(
            ui=SimpleNamespace(startButton=SimpleNamespace(isEnabled=lambda: idle)),
            _navigate_and_select=navigate,
            start_scan_callback=MagicMock(),
            _latest_result_for_wire=lambda wire: None,
        )

    def _handle(self, gui, line):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            WireScanSuiteGUI._handle_remote_command(gui, line)
        return buf.getvalue().splitlines()

    def test_scan_unknown_wire_ends_with_ready(self):
        gui = self._gui(wire_found=False)
        self.assertEqual(
            self._handle(gui, "SCAN WSXX"),
            ["ERROR:Wire 'WSXX' not found", "READY"],
        )
        gui.start_scan_callback.assert_not_called()

    def test_scan_without_wire_ends_with_ready(self):
        self.assertEqual(
            self._handle(self._gui(), "SCAN"),
            ["ERROR:SCAN requires a wire name", "READY"],
        )

    def test_scan_starts_and_announces_wire(self):
        gui = self._gui()
        self.assertEqual(self._handle(gui, "SCAN WS28144"), ["SCANNING:WS28144"])
        gui.start_scan_callback.assert_called_once()

    def test_scan_while_busy(self):
        self.assertEqual(self._handle(self._gui(idle=False), "SCAN WS28144"), ["BUSY"])

    def test_get_without_wire_ends_with_ready(self):
        self.assertEqual(
            self._handle(self._gui(), "GET"),
            ["ERROR:GET requires a wire name", "READY"],
        )

    def test_get_no_data_ends_with_ready(self):
        self.assertEqual(
            self._handle(self._gui(), "GET WS28144"),
            ["ERROR:No data available for WS28144", "READY"],
        )

    def test_unknown_command_ends_with_ready(self):
        self.assertEqual(
            self._handle(self._gui(), "FOO"),
            ["ERROR:Unknown command 'FOO'", "READY"],
        )


if __name__ == "__main__":
    unittest.main()
