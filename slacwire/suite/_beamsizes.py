from __future__ import annotations

import numpy as np


class BeamsizesMixin:
    """Extract beam sizes from scan results for multi-device emittance measurements."""

    def get_beamsizes(self, **run_kwargs) -> np.ndarray:
        """Return beam sizes for all configured wires as an (n, 2) array in microns.

        Runs scans for any wires that don't already have results stored.
        Keyword arguments are forwarded to ``run_all()`` (e.g. ``scan_mode``,
        ``rms_detector``).

        Returns:
            ndarray of shape (n_wires, 2) with columns [sigma_x, sigma_y].
            Missing values are NaN.
        """
        missing = [w for w in self.wires if not self.results.get(w)]
        if missing:
            self.run_all(**run_kwargs)

        sizes = []
        for wire in self.wires:
            rms = self.latest_run(wire).rms_sizes
            sigma_x = rms[0] if rms[0] is not None else np.nan
            sigma_y = rms[1] if rms[1] is not None else np.nan
            sizes.append([sigma_x, sigma_y])

        return np.array(sizes)

    def get_beamsize_errors(self, **run_kwargs) -> np.ndarray:
        """Return beam size uncertainties for all configured wires.

        Same contract as ``get_beamsizes`` but returns the 1-sigma
        uncertainties on each beam size.

        Returns:
            ndarray of shape (n_wires, 2) with columns [sigma_x_err, sigma_y_err].
            Missing values are NaN.
        """
        missing = [w for w in self.wires if not self.results.get(w)]
        if missing:
            self.run_all(**run_kwargs)

        errors = []
        for wire in self.wires:
            result = self.latest_run(wire)
            rms_err = getattr(result, "rms_sizes_err", None)
            if rms_err is not None:
                ex = rms_err[0] if rms_err[0] is not None else np.nan
                ey = rms_err[1] if rms_err[1] is not None else np.nan
            else:
                ex, ey = np.nan, np.nan
            errors.append([ex, ey])

        return np.array(errors)
