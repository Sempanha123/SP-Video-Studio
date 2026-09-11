from __future__ import annotations

from collections.abc import Callable

from domain.dubbing_errors import DubCancelled
from workers.base import WorkerTask
from workers.cancellation import CancellationToken


class DubbingWorker(WorkerTask):
    """Sequential segment worker. VoxCPM2 remains serialized through the existing TTS service."""

    def __init__(self, service, project_id: str, *, selected_ids: set[str] | None=None,
                 cancellation: CancellationToken | None=None, progress_callback: Callable[[int,int,str],None] | None=None) -> None:
        self.service=service; self.project_id=project_id; self.selected_ids=selected_ids
        self.cancellation=cancellation or CancellationToken(); self.progress_callback=progress_callback

    def run(self) -> list[str]:
        candidates=self.service.generation_candidates(self.project_id,self.selected_ids); completed:list[str]=[]; total=len(candidates)
        for index,segment in enumerate(candidates,1):
            if self.cancellation.is_cancelled:
                raise DubCancelled("Dub generation cancelled after the last completed segment.")
            self.service.generate_segment(self.project_id,segment.id,cancellation=self.cancellation)
            completed.append(segment.id)
            if self.progress_callback: self.progress_callback(index,total,segment.id)
        return completed
