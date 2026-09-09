"""In-process sample source for tests and self-test (no Windows Raw Input)."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from mouse_dpi_tool.contracts.movement import MovementSample


class SyntheticEventSource:
    def __init__(self, samples: Iterable[MovementSample]) -> None:
        self._samples = list(samples)
        self._stopped = False

    def start(
        self,
        emit_sample: Callable[[MovementSample], None],
        emit_status: Callable[[str], None],
    ) -> None:
        emit_status("synthetic_event_source_started")
        for sample in self._samples:
            if self._stopped:
                break
            emit_sample(sample)
        emit_status("synthetic_event_source_finished")

    def stop(self) -> None:
        self._stopped = True
