"""Tests for orbit_range prediction logic."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from slacwire.orbit_range import (
    SuggestedRange,
    suggest_scan_range,
    _compute_range,
    _compute_u_range,
)


@pytest.fixture
def mock_wire():
    wire = MagicMock()
    wire.name = "WS01"
    wire.area = "HTR"
    wire.install_angle = 45.0
    wire.metadata.tmitloss.upstream = ["BPM0H04", "BPM0H01"]
    wire.metadata.beam_path = ["CU_HXR"]
    return wire


class TestComputeRange:
    def test_symmetric_window(self):
        assert _compute_range(10000.0, 5000) == (5000, 15000)

    def test_negative_center(self):
        assert _compute_range(-3000.0, 2000) == (-5000, -1000)

    def test_rounding(self):
        assert _compute_range(1500.7, 1000) == (501, 2501)


class TestComputeURange:
    def test_45_degree_projection(self):
        inner, outer = _compute_u_range(1000.0, 1000.0, 5000, 45.0)
        # u_center = 1000*cos(45) + 1000*sin(45) = 1414.2
        assert inner == pytest.approx(-3586, abs=1)
        assert outer == pytest.approx(6414, abs=1)

    def test_zero_positions(self):
        inner, outer = _compute_u_range(0.0, 0.0, 5000, 45.0)
        assert inner == -5000
        assert outer == 5000

    def test_none_angle_defaults_to_45(self):
        result_default = _compute_u_range(1000.0, 1000.0, 5000, None)
        result_45 = _compute_u_range(1000.0, 1000.0, 5000, 45.0)
        assert result_default == result_45


class TestSuggestScanRange:
    @patch("slacwire.orbit_range._get_rmat")
    @patch("slacwire.orbit_range._read_bpm_position")
    def test_happy_path(self, mock_read_bpm, mock_get_rmat, mock_wire):
        mock_read_bpm.return_value = (2.0, -1.5)
        rmat = np.eye(6)
        rmat[0, 0] = 1.2
        rmat[2, 2] = 0.8
        mock_get_rmat.return_value = rmat

        result = suggest_scan_range(mock_wire, beampath="CU_HXR", half_window_um=5000)

        assert result.status == "ok"
        assert result.bpm_name == "BPM0H04"
        assert result.bpm_x_mm == 2.0
        assert result.bpm_y_mm == -1.5
        # x_wire_mm = 1.2 * 2.0 = 2.4 -> 2400 um
        assert result.x_center == pytest.approx(2400.0)
        assert result.x_range == (2400 - 5000, 2400 + 5000)
        # y_wire_mm = 0.8 * -1.5 = -1.2 -> -1200 um
        assert result.y_center == pytest.approx(-1200.0)
        assert result.y_range == (-1200 - 5000, -1200 + 5000)

    def test_no_upstream_bpm(self, mock_wire):
        mock_wire.metadata.tmitloss = None

        result = suggest_scan_range(mock_wire, beampath="CU_HXR")

        assert result.status == "no_bpm_configured"
        assert result.x_range is None

    @patch("slacwire.orbit_range._read_bpm_position")
    def test_bpm_offline(self, mock_read_bpm, mock_wire):
        mock_read_bpm.return_value = (None, None)

        result = suggest_scan_range(mock_wire, beampath="CU_HXR")

        assert result.status == "bpm_offline"
        assert result.bpm_name == "BPM0H04"

    @patch("slacwire.orbit_range._get_rmat")
    @patch("slacwire.orbit_range._read_bpm_position")
    def test_model_unavailable(self, mock_read_bpm, mock_get_rmat, mock_wire):
        mock_read_bpm.return_value = (1.0, 1.0)
        mock_get_rmat.side_effect = RuntimeError("MEME service down")

        result = suggest_scan_range(mock_wire, beampath="CU_HXR")

        assert result.status == "model_unavailable"
        assert "MEME service down" in result.message

    @patch("slacwire.orbit_range._get_rmat")
    @patch("slacwire.orbit_range._read_bpm_position")
    def test_explicit_bpm_override(self, mock_read_bpm, mock_get_rmat, mock_wire):
        mock_read_bpm.return_value = (0.5, 0.5)
        mock_get_rmat.return_value = np.eye(6)

        result = suggest_scan_range(
            mock_wire, beampath="CU_HXR", bpm_name="BPM_CUSTOM"
        )

        assert result.bpm_name == "BPM_CUSTOM"
        mock_read_bpm.assert_called_once_with("HTR", "BPM_CUSTOM")
