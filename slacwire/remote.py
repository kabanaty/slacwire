"""stdin/stdout remote-control protocol for the Wire Scan GUI.

Enables MATLAB (or any parent process) to keep the PyDM window alive
and send commands over stdin while reading responses from stdout.

Launch:  pydm ws_gui.py --remote [--wire WS28144] [--beampath CU_HXR]

Protocol
--------
Commands (stdin, one per line):
    SCAN <wire> [<detector>]   Navigate to wire, start scan.
    SELECT <wire> [<detector>] Navigate to wire without scanning.
    GET <wire>                 Save the wire's current result to H5 (no scan).
    STATUS                     Print current wire name and scan state.
    QUIT                       Close the GUI.

Responses (stdout, one per line):
    READY                      GUI ready for next command.
    H5_PATH:<path>             Scan data file written.
    SCANNING:<wire>            Scan started.
    SELECTED:<wire>            Wire changed.
    ERROR:<message>            Command failed.
    BUSY                       Scan in progress; command rejected.

SCAN, GET and unknown commands always end with READY (or BUSY), including
after an ERROR line, so a client can wait for READY without hanging.
Closing stdin without QUIT is treated as QUIT.
"""

import sys

from PyQt5.QtCore import QThread, pyqtSignal


class StdinCommandReader(QThread):
    """Reads lines from stdin on a background thread, emitting each as a Qt signal."""

    commandReceived = pyqtSignal(str)

    def run(self):
        try:
            for line in sys.stdin:
                text = line.strip()
                if not text:
                    continue
                self.commandReceived.emit(text)
                if text.upper() == "QUIT":
                    return
        except (EOFError, ValueError):
            pass
        # stdin closed without QUIT: the controlling process is gone, so
        # close the GUI rather than leave an orphaned window.
        self.commandReceived.emit("QUIT")
