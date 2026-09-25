from __future__ import annotations

from pathlib import Path


class CompareMixin:
    """Multi-detector comparison plotting for completed scans."""

    def compare_detectors(
        self,
        wire: str,
        detectors: list[str] | None = None,
    ) -> Path | None:
        """Render a multi-detector overlay for the latest scan of a wire.

        Each detector's raw trace is min-max normalized so signals with
        different amplitudes are visually comparable.  Wire position is
        shown on the left axis, normalized detector traces on the right.

        Args:
            wire: Wire name whose latest result will be compared.
            detectors: Detector names to include.  Defaults to all
                detectors listed in the collection metadata.

        Returns:
            Path to saved PNG, or None if saving is disabled.
        """
        data = self.latest_run(wire)

        method = "otf"
        for entry in reversed(self.registry.entries):
            if entry.get("wire") == wire:
                method = entry.get("method", "otf")
                break
        file_prefix = "OTF" if method == "otf" else "Step"

        return self.view.render_detector_comparison(
            data,
            wire=wire,
            detectors=detectors,
            file_prefix=file_prefix,
            plotdir=self.plotdir,
            stamp=self._stamp(),
            show=self.show,
            save=self.save_plots,
        )
