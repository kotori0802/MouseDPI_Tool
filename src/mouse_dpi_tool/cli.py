from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mouse-dpi-tool", description="Mouse DPI Tool")
    parser.add_argument(
        "command",
        nargs="?",
        default="version",
        choices=["version", "self-test", "ui"],
        help="CLI surface (ui launches the PySide6 shell)",
    )
    args = parser.parse_args(argv)

    if args.command == "version":
        from mouse_dpi_tool import __schema_version__, __version__

        print(f"mouse-dpi-tool {__version__}")
        print(f"session_schema {__schema_version__}")
        return 0

    if args.command == "ui":
        from mouse_dpi_tool.ui.app import main as ui_main

        return ui_main(argv)

    if args.command == "self-test":
        from mouse_dpi_tool.capture import CaptureEngine, SyntheticEventSource
        from mouse_dpi_tool.contracts.movement import MovementSample
        from mouse_dpi_tool.measurement.group import build_group_summaries
        from mouse_dpi_tool.measurement.ratio import build_ratio_analysis
        from mouse_dpi_tool.measurement.settings import normalize_settings
        from mouse_dpi_tool.measurement.synthetic import make_synthetic_trials
        from mouse_dpi_tool.path_quality import StreamingPathQualityAccumulator

        settings = normalize_settings(
            {
                "distance_input": 100.0,
                "distance_unit": "mm",
                "dpi_steps": [400, 800],
                "trials_per_group": 2,
                "min_valid_trials_per_group": 2,
            }
        )
        trials = make_synthetic_trials([400, 800], distance_mm=100.0, trials_per_group=2)
        groups = build_group_summaries(trials, settings)
        ratios = build_ratio_analysis(groups, settings)

        samples = [MovementSample(dx=10, dy=0, device_id="synthetic") for _ in range(20)]
        pq = StreamingPathQualityAccumulator()
        engine = CaptureEngine(source=SyntheticEventSource(samples))
        engine.subscribe(pq.on_sample)
        engine.start()
        engine.wait_until_idle()
        engine.stop()
        snap = pq.snapshot()
        print(
            f"self-test ok: trials={len(trials)} groups={len(groups)} ratios={len(ratios)} "
            f"capture_net=({engine.net_counts_x},{engine.net_counts_y}) "
            f"path_total={snap['path_total_counts']} pq={snap['status']}"
        )
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
