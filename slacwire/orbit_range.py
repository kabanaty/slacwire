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
    half_window_um: int = 2000,
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
    bpm_names = _resolve_bpm_names(wire, bpm_name)
    if not bpm_names:
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

    bpm_positions = _read_multiple_bpm_positions(wire.area, bpm_names)
    if not bpm_positions:
        return SuggestedRange(
            x_center=None,
            y_center=None,
            x_range=None,
            y_range=None,
            u_range=None,
            bpm_name=bpm_names[0],
            bpm_x_mm=None,
            bpm_y_mm=None,
            status="bpm_offline",
            message="Could not read position from any upstream BPM.",
        )

    try:
        x_wire_mm, y_wire_mm = _propagate_to_wire(
            bpm_positions, wire, beampath, physics_model
        )
    except Exception as exc:
        logger.warning("Model lookup failed: %s", exc)
        first_pos = next(iter(bpm_positions.values()))
        return SuggestedRange(
            x_center=None,
            y_center=None,
            x_range=None,
            y_range=None,
            u_range=None,
            bpm_name=next(iter(bpm_positions)),
            bpm_x_mm=first_pos[0],
            bpm_y_mm=first_pos[1],
            status="model_unavailable",
            message=f"Could not retrieve R-matrix: {exc}",
        )

    x_deviation_um = x_wire_mm * 1000.0
    y_deviation_um = y_wire_mm * 1000.0

    # Offset into motor coordinates: midpoint of current range = design orbit
    x_ref_um = sum(wire.x_range) / 2.0
    y_ref_um = sum(wire.y_range) / 2.0

    x_center_um = x_ref_um + x_deviation_um
    y_center_um = y_ref_um + y_deviation_um

    x_range = _compute_range(x_center_um, half_window_um)
    y_range = _compute_range(y_center_um, half_window_um)

    u_ref_um = sum(wire.u_range) / 2.0
    u_range = _compute_u_range(
        x_deviation_um, y_deviation_um, half_window_um, wire.install_angle, u_ref_um
    )

    bpm_names_used = ", ".join(bpm_positions.keys())
    first_bpm = next(iter(bpm_positions))
    first_pos = bpm_positions[first_bpm]

    return SuggestedRange(
        x_center=x_center_um,
        y_center=y_center_um,
        x_range=x_range,
        y_range=y_range,
        u_range=u_range,
        bpm_name=bpm_names_used,
        bpm_x_mm=first_pos[0],
        bpm_y_mm=first_pos[1],
        status="ok",
        message=f"Range suggestion ready ({len(bpm_positions)} BPMs used).",
    )


def _resolve_bpm_names(wire, override: str | None) -> list[str]:
    if override:
        return [override]
    tmitloss = getattr(wire.metadata, "tmitloss", None)
    if tmitloss and tmitloss.upstream:
        return list(tmitloss.upstream)
    return []


def _read_multiple_bpm_positions(
    area: str, bpm_names: list[str]
) -> dict[str, tuple[float, float]]:
    """Read positions from all available BPMs, skipping any that are offline."""
    from slac_devices.reader import create_bpm

    positions = {}
    for name in bpm_names:
        bpm = create_bpm(area=area, name=name)
        if bpm is None:
            continue
        try:
            x = bpm.x
            y = bpm.y
        except Exception:
            continue
        if x is None or y is None:
            continue
        positions[name] = (float(x), float(y))
    return positions


def _propagate_to_wire(
    bpm_positions: dict[str, tuple[float, float]],
    wire,
    beampath: str,
    physics_model: str,
) -> tuple[float, float]:
    """Propagate BPM readings to wire position using R-matrices.

    With 1 BPM: zero-angle approximation (position-only).
    With 2+ BPMs: least-squares fit for [position, angle] at the first BPM,
    then full state propagation to the wire.
    """
    from meme.model import Model

    model = Model(beampath, model_source=physics_model, use_design=False)
    bpm_names = list(bpm_positions.keys())
    ref_bpm = bpm_names[0]

    rmat_to_wire = model.get_rmat(from_device=ref_bpm, to_device=wire.name)

    if len(bpm_names) == 1:
        x_mm, y_mm = bpm_positions[ref_bpm]
        x_wire = rmat_to_wire[0, 0] * x_mm
        y_wire = rmat_to_wire[2, 2] * y_mm
        return x_wire, y_wire

    # Build overdetermined system: for each BPM i,
    #   x_i = R_i[0,0] * x0 + R_i[0,1] * x0'
    # where R_i is the R-matrix from ref_bpm to bpm_i.
    x_measurements = []
    y_measurements = []
    Ax_rows = []
    Ay_rows = []

    for name in bpm_names:
        x_mm, y_mm = bpm_positions[name]
        if name == ref_bpm:
            Ax_rows.append([1.0, 0.0])
            Ay_rows.append([1.0, 0.0])
        else:
            rmat_i = model.get_rmat(from_device=ref_bpm, to_device=name)
            Ax_rows.append([rmat_i[0, 0], rmat_i[0, 1]])
            Ay_rows.append([rmat_i[2, 2], rmat_i[2, 3]])
        x_measurements.append(x_mm)
        y_measurements.append(y_mm)

    Ax = np.array(Ax_rows)
    Ay = np.array(Ay_rows)
    bx = np.array(x_measurements)
    by = np.array(y_measurements)

    # Least-squares: solve for [x0, x0'] and [y0, y0'] at ref_bpm
    x_state, _, _, _ = np.linalg.lstsq(Ax, bx, rcond=None)
    y_state, _, _, _ = np.linalg.lstsq(Ay, by, rcond=None)

    # Propagate full state vector to wire
    x_wire = rmat_to_wire[0, 0] * x_state[0] + rmat_to_wire[0, 1] * x_state[1]
    y_wire = rmat_to_wire[2, 2] * y_state[0] + rmat_to_wire[2, 3] * y_state[1]

    return x_wire, y_wire


def _compute_range(center_um: float, half_window_um: int) -> tuple[int, int]:
    inner = int(round(center_um - half_window_um))
    outer = int(round(center_um + half_window_um))
    return (inner, outer)


def _compute_u_range(
    x_deviation_um: float,
    y_deviation_um: float,
    half_window_um: int,
    install_angle_deg: float | None,
    u_ref_um: float = 0.0,
) -> tuple[int, int]:
    angle_deg = install_angle_deg if install_angle_deg else 45.0
    angle_rad = math.radians(angle_deg)
    u_deviation = x_deviation_um * math.cos(angle_rad) + y_deviation_um * math.sin(angle_rad)
    u_center_um = u_ref_um + u_deviation
    return _compute_range(u_center_um, half_window_um)
