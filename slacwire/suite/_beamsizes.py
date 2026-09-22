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
