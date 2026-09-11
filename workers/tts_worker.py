from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from domain.generated_audio import GeneratedAudio
from domain.narration import NarrationProgress
from domain.voice_config import VoiceConfig
from services.narration_service import NarrationService
from workers.base import JobInfo, JobState
from workers.cancellation import CancellationToken


@dataclass(slots=True)
class TTSWorker:
    service: NarrationService
    project_id: str
    voice_config: VoiceConfig
    section_id: str | None = None
    cancellation: CancellationToken | None = None
    progress_callback: Callable[[NarrationProgress], None] | None = None
    job: JobInfo | None = None

    def run(self) -> GeneratedAudio:
        token = self.cancellation or CancellationToken()
        job = self.job or JobInfo(name="tts_generation")
        self.job = job
        job.state = JobState.PREPARING
        try:
            def progress(value: NarrationProgress) -> None:
                job.state = JobState.RUNNING
                job.progress = value.ratio
                if self.progress_callback:
                    self.progress_callback(value)

            result = (
                self.service.generate_section(self.project_id, self.section_id, self.voice_config, token, progress)
                if self.section_id
                else self.service.generate_full(self.project_id, self.voice_config, token, progress)
            )
            job.state = JobState.COMPLETED
            job.progress = 1.0
            return result
        except Exception as exc:
            job.state = JobState.CANCELLED if token.is_cancelled else JobState.FAILED
            job.error = str(exc)
            raise
