from __future__ import annotations

import logging

from slacwire.speed_status import profile_message

logger = logging.getLogger("wire_scan_logger")


def format_invalid_planes(wire_name: str, invalid_planes) -> str:
    """One line per invalid plane, e.g. 'WS28144 X Profile too fast: ...'."""
    return "\n".join(
        f"{wire_name} {profile_message(s.profile, s)}" for s in invalid_planes
    )


class PreflightMixin:
    """Checks run before a scan moves the wire with beam."""

    def _check_scan_speed(self, device) -> None:
        """Refuse to scan when an active plane's speed is out of limits.

        The IOC calculates the on-the-fly scan speed for each plane from the
        range, beam rate and scan pulses. A scan is only allowed when every
        active plane is between the speed floor and the maximum speed.

        Raises:
            ValueError: If any active plane has an invalid speed.
        """
        invalid = device.invalid_profiles()
        if invalid:
            message = format_invalid_planes(device.name, invalid)
            raise ValueError(f"Scan refused, invalid wire speed:\n{message}")
