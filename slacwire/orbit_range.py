"""Predict wire scan ranges from BPM orbit data."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SuggestedRange:
    x_center: float | None
    y_center: float | None
    x_range: tuple[int, int] | None
    y_range: tuple[int, int] | None
    u_range: tuple[int, int] | None
    bpm_name: str
    bpm_x_mm: float | None
    bpm_y_mm: float | None
    status: str
    message: str


def suggest_scan_range(
    wire,
    beampath: str,
    half_window_um: int = 5000,
    bpm_name: str | None = None,
    physics_model: str = "BMAD",
) -> SuggestedRange:
    """Read BPM orbit and suggest a scan range centered on the beam.

    Parameters
    ----------
    wire : Wire
        Wire device object with metadata.tmitloss.upstream populated.
    beampath : str
        Beampath identifier for model lookup (e.g. "CU_HXR").
    half_window_um : int
        Half-width of scan window in micrometers.
    bpm_name : str | None
        Override BPM to use. Defaults to first upstream BPM.
    physics_model : str
        Model source ("BMAD" or "BLEM").

    Returns
    -------
    SuggestedRange
    """
    chosen_bpm = _resolve_bpm_name(wire, bpm_name)
    if chosen_bpm is None:
        return SuggestedRange(
            x_center=None,
            y_center=None,
            x_range=None,
            y_range=None,
            u_range=None,
            bpm_name="",
            bpm_x_mm=None,
            bpm_y_mm=None,
            status="no_bpm_configured",
            message="No upstream BPM found in wire metadata.",
        )

    bpm_x_mm, bpm_y_mm = _read_bpm_position(wire.area, chosen_bpm)
    if bpm_x_mm is None or bpm_y_mm is None:
        return SuggestedRange(
            x_center=None,
            y_center=None,
            x_range=None,
            y_range=None,
            u_range=None,
            bpm_name=chosen_bpm,
            bpm_x_mm=bpm_x_mm,
            bpm_y_mm=bpm_y_mm,
            status="bpm_offline",
            message=f"Could not read position from {chosen_bpm}.",
        )

    try:
        rmat = _get_rmat(chosen_bpm, wire, beampath, physics_model)
    except Exception as exc:
        logger.warning("Model lookup failed: %s", exc)
        return SuggestedRange(
            x_center=None,
            y_center=None,
            x_range=None,
            y_range=None,
            u_range=None,
            bpm_name=chosen_bpm,
            bpm_x_mm=bpm_x_mm,
            bpm_y_mm=bpm_y_mm,
            status="model_unavailable",
            message=f"Could not retrieve R-matrix: {exc}",
        )

    x_wire_mm = rmat[0, 0] * bpm_x_mm
    y_wire_mm = rmat[2, 2] * bpm_y_mm

    x_deviation_um = x_wire_mm * 1000.0
    y_deviation_um = y_wire_mm * 1000.0

    # Offset into motor coordinates: midpoint of current range = design orbit
    x_ref_um = sum(wire.x_range) / 2.0
    y_ref_um = sum(wire.y_range) / 2.0

    x_center_um = x_ref_um + x_deviation_um
    y_center_um = y_ref_um + y_deviation_um

    x_range = _compute_range(x_center_um, half_window_um)
    y_range = _compute_range(y_center_um, half_window_um)
    u_range = _compute_u_range(
        x_center_um, y_center_um, half_window_um, wire.install_angle
    )

    return SuggestedRange(
        x_center=x_center_um,
        y_center=y_center_um,
        x_range=x_range,
        y_range=y_range,
        u_range=u_range,
        bpm_name=chosen_bpm,
        bpm_x_mm=bpm_x_mm,
        bpm_y_mm=bpm_y_mm,
        status="ok",
        message="Range suggestion ready.",
    )


def _resolve_bpm_name(wire, override: str | None) -> str | None:
    if override:
        return override
    tmitloss = getattr(wire.metadata, "tmitloss", None)
    if tmitloss and tmitloss.upstream:
        return tmitloss.upstream[0]
    return None


def _read_bpm_position(area: str, bpm_name: str) -> tuple[float | None, float | None]:
    from slac_devices.reader import create_bpm

    bpm = create_bpm(area=area, name=bpm_name)
    if bpm is None:
        return None, None
    try:
        x = bpm.x
        y = bpm.y
    except Exception:
        return None, None
    if x is None or y is None:
        return None, None
    return float(x), float(y)


def _get_rmat(
    bpm_name: str, wire, beampath: str, physics_model: str
) -> np.ndarray:
    from meme.model import Model

    model = Model(beampath, model_source=physics_model, use_design=False)
    return model.get_rmat(from_device=bpm_name, to_device=wire.name)


def _compute_range(center_um: float, half_window_um: int) -> tuple[int, int]:
    inner = int(round(center_um - half_window_um))
    outer = int(round(center_um + half_window_um))
    return (inner, outer)


def _compute_u_range(
    x_center_um: float,
    y_center_um: float,
    half_window_um: int,
    install_angle_deg: float | None,
) -> tuple[int, int]:
    angle_deg = install_angle_deg if install_angle_deg else 45.0
    angle_rad = math.radians(angle_deg)
    u_center_um = x_center_um * math.cos(angle_rad) + y_center_um * math.sin(angle_rad)
    return _compute_range(u_center_um, half_window_um)
