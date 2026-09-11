from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Callable

from domain.media import MediaStatus, MediaType
from domain.model_installation import ModelInstallStatus
from domain.project import utc_now_iso
from domain.settings import PerformanceProfile
from domain.transcript import Transcript, TranscriptStatus
from domain.transcript_segment import TranscriptSegment
from domain.transcript_word import TranscriptWord
from engines.stt.errors import (
    STTCancelled,
    STTDependencyMissing,
    STTInvalidMedia,
    STTInvalidRequest,
    STTModelNotInstalled,
    STTOutOfMemory,
    STTResourceConflict,
    STTUnsupportedDevice,
)
from engines.stt.manager import STTEngineManager
from engines.stt.types import TranscriptionRequest
from services.ai_resource_manager import AIResourceConflict, AIResourceManager
from services.media_service import MediaService
from services.model_service import ModelService
from services.settings_service import SettingsService
from services.system_readiness_service import SystemReadinessService
from services.transcript_analysis_service import TranscriptAnalysisService, seconds_to_ms
from storage.repositories.transcript_repository import TranscriptRepository
from workers.cancellation import CancellationToken

ProgressCallback = Callable[[str, float | None, int, int, str], None]


class TranscriptionService:
    FAMILY = "faster-whisper"

    def __init__(
        self,
        repository: TranscriptRepository,
        media_service: MediaService,
        model_service: ModelService,
        manager: STTEngineManager,
        readiness: SystemReadinessService,
        settings: SettingsService,
        analysis: TranscriptAnalysisService,
        resource_manager: AIResourceManager | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.repository = repository
        self.media_service = media_service
        self.model_service = model_service
        self.manager = manager
        self.readiness = readiness
        self.settings = settings
        self.analysis = analysis
        self.resource_manager = resource_manager
        self.logger = logger or logging.getLogger("sp_video_studio.transcription")
        self._loaded_model_id: str | None = None
        self._loaded_device = ""
        self._loaded_compute = ""
        self._loaded_batch_mode = False
        self._active_jobs = 0

    @property
    def active_jobs(self) -> int:
        return self._active_jobs

    def supported_models(self):
        return self.model_service.registry.list_family(self.FAMILY)

    def recommended_model_id(self) -> str:
        installed = {m.model_id for m in self.supported_models() if self._is_installed(m.model_id)}
        profile = str(self.settings.current.performance_profile)
        order = {
            PerformanceProfile.LOW_MEMORY.value: ("whisper-small", "whisper-medium", "whisper-large-v3"),
            PerformanceProfile.BALANCED.value: ("whisper-medium", "whisper-small", "whisper-large-v3"),
            PerformanceProfile.MAXIMUM_QUALITY.value: ("whisper-large-v3", "whisper-medium", "whisper-small"),
        }.get(profile, ("whisper-medium", "whisper-small", "whisper-large-v3"))
        for model_id in order:
            if model_id in installed:
                return model_id
        return next(iter(installed), "")

    def resolve_device(self, requested: str) -> str:
        requested = (requested or "auto").lower()
        if requested not in {"auto", "cpu", "cuda"} and not requested.startswith("cuda:"):
            raise STTUnsupportedDevice()
        if requested == "cpu":
            return "cpu"
        if requested.startswith("cuda"):
            self._validate_ctranslate2_cuda()
            return requested
        readiness = self.readiness.detect()
        if readiness.cuda_status == "available" and self._ctranslate2_cuda_ready():
            return "cuda"
        return "cpu"

    def resolve_compute_type(self, requested: str, device: str) -> str:
        requested = (requested or "auto").lower()
        if requested == "auto":
            if device.startswith("cuda"):
                return "int8_float16" if self.settings.current.performance_profile == PerformanceProfile.LOW_MEMORY.value else "float16"
            return "int8"
        allowed = {"cpu": {"int8", "float32"}, "cuda": {"float16", "int8_float16", "int8"}}
        key = "cuda" if device.startswith("cuda") else "cpu"
        if requested not in allowed[key]:
            raise STTInvalidRequest("The selected precision is not supported on this device.")
        supported = self._supported_compute_types(key)
        if supported and requested not in supported:
            raise STTInvalidRequest("The selected precision is not supported by this CTranslate2 runtime.")
        return requested

    def load(self, model_id: str, *, device: str = "auto", compute_type: str = "auto", batch_mode: bool = False) -> tuple[str, str]:
        model = self._model(model_id)
        self._ensure_model_ready(model_id)
        resolved_device = self.resolve_device(device)
        resolved_compute = self.resolve_compute_type(compute_type, resolved_device)
        if self.resource_manager is not None:
            try:
                self.resource_manager.prepare("stt", resolved_device)
            except AIResourceConflict as exc:
                raise STTResourceConflict(str(exc)) from exc
        path = self.model_service.install_path(model)
        if self._loaded_model_id and (
            self._loaded_model_id != model_id
            or self._loaded_device != resolved_device
            or self._loaded_compute != resolved_compute
            or self._loaded_batch_mode != bool(batch_mode)
        ):
            self.unload()
        if not self.manager.engine.is_available():
            raise STTDependencyMissing()
        if not self.manager.engine.is_loaded():
            self.manager.load(
                model_path=str(path), device=resolved_device, compute_type=resolved_compute, batch_mode=batch_mode
            )
            self.model_service.acquire_model(model_id, loaded=True)
            self._loaded_model_id = model_id
            self._loaded_device = resolved_device
            self._loaded_compute = resolved_compute
            self._loaded_batch_mode = bool(batch_mode)
        return resolved_device, resolved_compute

    def unload(self) -> None:
        model_id = self._loaded_model_id
        self.manager.unload()
        self._loaded_model_id = None
        self._loaded_device = ""
        self._loaded_compute = ""
        self._loaded_batch_mode = False
        if model_id:
            self.model_service.release_model(model_id, unload=True)

    def transcribe(
        self,
        request: TranscriptionRequest,
        cancellation: CancellationToken | None = None,
        progress: ProgressCallback | None = None,
    ) -> tuple[Transcript, list[TranscriptSegment]]:
        cancellation = cancellation or CancellationToken()
        request = self._prepare_request(request)
        self.manager.engine.validate_request(request)
        asset = self.media_service.get_media(request.project_id, request.media_id)
        if asset.type not in {MediaType.AUDIO.value, MediaType.VIDEO.value}:
            raise STTInvalidMedia("Only audio and video can be transcribed.")
        if str(asset.status) != MediaStatus.READY.value or not Path(asset.project_path).is_file():
            raise STTInvalidMedia("The project media is missing or not ready.")

        if progress:
            progress("loading_model", None, 0, max(0, int(asset.duration_ms or 0)), "Loading Whisper model…")
        device, compute = self.load(
            request.model_id, device=request.device, compute_type=request.compute_type, batch_mode=request.batch_mode
        )
        request.device = device
        request.compute_type = compute
        cancellation.raise_if_cancelled()
        self.model_service.acquire_model(request.model_id, loaded=True)
        self._active_jobs += 1
        try:
            if progress:
                progress("transcribing", 0.0 if asset.duration_ms else None, 0, int(asset.duration_ms or 0), "Transcribing…")
            output = self.manager.engine.transcribe(request)
            transcript = Transcript(
                project_id=request.project_id,
                media_id=request.media_id,
                engine="faster-whisper",
                model_id=request.model_id,
                model_version=output.info.model_version or self._model(request.model_id).version,
                language_mode=request.language,
                detected_language=output.info.language,
                language_probability=output.info.language_probability,
                device=device,
                compute_type=compute,
                duration_ms=seconds_to_ms(output.info.duration_seconds) or int(asset.duration_ms or 0),
                status=TranscriptStatus.PROCESSING,
                source_fingerprint=self.analysis.fingerprint(asset.asset_id, Path(asset.project_path)),
                settings={
                    "word_timestamps": request.word_timestamps,
                    "vad_enabled": request.vad_enabled,
                    "vad_settings": dict(request.vad_settings),
                    "beam_size": request.beam_size,
                    "batch_mode": request.batch_mode,
                    "batch_size": request.batch_size,
                    "initial_prompt": request.initial_prompt,
                    "hotwords": request.hotwords,
                },
                metadata={
                    "faster_whisper_version": output.info.faster_whisper_version,
                    "ctranslate2_version": output.info.ctranslate2_version,
                    "duration_after_vad_ms": seconds_to_ms(output.info.duration_after_vad_seconds),
                },
                active=True,
            )
            segments: list[TranscriptSegment] = []
            previous_end = 0
            for order, raw in enumerate(output.segments):
                if cancellation.is_cancelled:
                    raise STTCancelled()
                start_ms = seconds_to_ms(raw.start)
                end_ms = seconds_to_ms(raw.end)
                self.analysis.validate_timestamps(
                    start_ms, end_ms, previous_end_ms=previous_end, duration_ms=transcript.duration_ms
                )
                segment = TranscriptSegment(
                    transcript_id=transcript.transcript_id,
                    order=order,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    text=raw.text,
                    original_text=raw.text,
                    confidence=raw.avg_logprob,
                    no_speech_probability=raw.no_speech_probability,
                    temperature=raw.temperature,
                )
                for word_order, raw_word in enumerate(raw.words):
                    word = TranscriptWord(
                        segment_id=segment.segment_id,
                        order=word_order,
                        start_ms=seconds_to_ms(raw_word.start),
                        end_ms=seconds_to_ms(raw_word.end),
                        text=raw_word.text,
                        probability=raw_word.probability,
                    )
                    segment.words.append(word)
                segment.validate()
                segments.append(segment)
                previous_end = end_ms
                if progress:
                    fraction = self.analysis.progress(end_ms, transcript.duration_ms)
                    progress("transcribing", fraction, end_ms, transcript.duration_ms, f"Transcribing segment {order + 1}")
            transcript.status = TranscriptStatus.READY
            transcript.updated_at = utc_now_iso()
            self.repository.create_with_segments(transcript, segments)
            self.logger.info(
                "Transcription completed: media=%s model=%s device=%s compute=%s language=%s segments=%s",
                request.media_id, request.model_id, device, compute, transcript.detected_language, len(segments),
            )
            if progress:
                progress("completed", 1.0, transcript.duration_ms, transcript.duration_ms, "Transcript ready")
            return transcript, segments
        except RuntimeError as exc:
            if cancellation.is_cancelled or "cancelled" in str(exc).lower():
                raise STTCancelled() from exc
            raise
        finally:
            self._active_jobs = max(0, self._active_jobs - 1)
            self.model_service.release_model(request.model_id, unload=False)
            if (
                self.settings.current.performance_profile == PerformanceProfile.LOW_MEMORY.value
                and self._active_jobs == 0
                and self._loaded_model_id == request.model_id
            ):
                self.unload()

    def get_active(self, project_id: str, media_id: str) -> tuple[Transcript | None, list[TranscriptSegment]]:
        transcript = self.repository.active_for_media(project_id, media_id)
        if transcript is None:
            return None, []
        asset = self.media_service.get_media(project_id, media_id)
        if Path(asset.project_path).is_file():
            current = self.analysis.fingerprint(asset.asset_id, Path(asset.project_path))
            if transcript.source_fingerprint != current and transcript.status_code == TranscriptStatus.READY.value:
                transcript.status = TranscriptStatus.OUTDATED
                self.repository.update_status(transcript.transcript_id, TranscriptStatus.OUTDATED.value)
        return transcript, self.repository.segments(transcript.transcript_id)

    def list_history(self, project_id: str, media_id: str) -> list[Transcript]:
        return self.repository.list_for_media(project_id, media_id)

    def set_active(self, project_id: str, media_id: str, transcript_id: str) -> None:
        self.repository.set_active(project_id, media_id, transcript_id)

    def update_segment(self, project_id: str, transcript_id: str, segment_id: str, text: str) -> None:
        transcript = self._owned(project_id, transcript_id)
        segments = self.repository.segments(transcript.transcript_id)
        original = next((item for item in segments if item.segment_id == segment_id), None)
        if original is None:
            raise KeyError("Transcript segment not found.")
        self.repository.update_segment_text(transcript_id, segment_id, text, edited=(text != original.original_text))

    def reset_segment(self, project_id: str, transcript_id: str, segment_id: str) -> None:
        self._owned(project_id, transcript_id)
        self.repository.reset_segment(transcript_id, segment_id)

    def search(self, project_id: str, transcript_id: str, query: str) -> list[TranscriptSegment]:
        self._owned(project_id, transcript_id)
        return self.repository.search_segments(transcript_id, query)

    def combined_text(self, project_id: str, transcript_id: str) -> str:
        self._owned(project_id, transcript_id)
        return "\n".join(segment.text.strip() for segment in self.repository.segments(transcript_id) if segment.text.strip())

    def export_txt(self, project_id: str, transcript_id: str, destination: Path) -> Path:
        self._owned(project_id, transcript_id)
        from services.transcript_analysis_service import format_timestamp_ms
        lines: list[str] = []
        for segment in self.repository.segments(transcript_id):
            lines.append(f"[{format_timestamp_ms(segment.start_ms)} - {format_timestamp_ms(segment.end_ms)}]")
            lines.append(segment.text)
            lines.append("")
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return destination

    def delete(self, project_id: str, transcript_id: str) -> None:
        self._owned(project_id, transcript_id)
        self.repository.delete(project_id, transcript_id)

    def duplicate_project_transcripts(self, source_project_id: str, target_project_id: str, media_map: dict[str, str]) -> int:
        created = 0
        for source in self.repository.list_for_project(source_project_id):
            target_media_id = media_map.get(source.media_id)
            if not target_media_id:
                continue
            from uuid import uuid4
            new = Transcript(
                project_id=target_project_id,
                media_id=target_media_id,
                engine=source.engine,
                model_id=source.model_id,
                model_version=source.model_version,
                language_mode=source.language_mode,
                detected_language=source.detected_language,
                language_probability=source.language_probability,
                device=source.device,
                compute_type=source.compute_type,
                duration_ms=source.duration_ms,
                status=source.status,
                source_fingerprint="",
                settings=dict(source.settings),
                metadata=dict(source.metadata),
                active=source.active,
            )
            target_asset = self.media_service.get_media(target_project_id, target_media_id)
            if Path(target_asset.project_path).is_file():
                new.source_fingerprint = self.analysis.fingerprint(target_media_id, Path(target_asset.project_path))
            cloned_segments: list[TranscriptSegment] = []
            for segment in self.repository.segments(source.transcript_id):
                clone_segment = TranscriptSegment(
                    transcript_id=new.transcript_id,
                    order=segment.order,
                    start_ms=segment.start_ms,
                    end_ms=segment.end_ms,
                    text=segment.text,
                    original_text=segment.original_text,
                    confidence=segment.confidence,
                    no_speech_probability=segment.no_speech_probability,
                    temperature=segment.temperature,
                    edited=segment.edited,
                    metadata=dict(segment.metadata),
                )
                clone_segment.words = [
                    TranscriptWord(
                        segment_id=clone_segment.segment_id,
                        order=word.order,
                        start_ms=word.start_ms,
                        end_ms=word.end_ms,
                        text=word.text,
                        probability=word.probability,
                        metadata=dict(word.metadata),
                    )
                    for word in segment.words
                ]
                cloned_segments.append(clone_segment)
            self.repository.create_with_segments(new, cloned_segments)
            created += 1
        return created

    def _prepare_request(self, request: TranscriptionRequest) -> TranscriptionRequest:
        if request.language not in {"auto", "en", "km"}:
            raise STTInvalidRequest("Language must be Auto Detect, English, or Khmer.")
        if request.beam_size < 1 or request.beam_size > 20:
            raise STTInvalidRequest("Beam size must be between 1 and 20.")
        if request.batch_size < 1 or request.batch_size > 64:
            raise STTInvalidRequest("Batch size must be between 1 and 64.")
        return request

    def _model(self, model_id: str):
        try:
            model = self.model_service.registry.get(model_id)
        except KeyError as exc:
            raise STTModelNotInstalled("Unknown Whisper model.") from exc
        if model.family != self.FAMILY:
            raise STTInvalidRequest("The selected model is not a speech recognition model.")
        return model

    def _ensure_model_ready(self, model_id: str) -> None:
        model = self._model(model_id)
        installation = self.model_service.repository.get(model_id)
        path = self.model_service.install_path(model)
        if installation is None or installation.status_code != ModelInstallStatus.INSTALLED.value or not path.is_dir():
            raise STTModelNotInstalled(f"{model.name} is not installed.")

    def _is_installed(self, model_id: str) -> bool:
        try:
            model = self._model(model_id)
        except Exception:
            return False
        installation = self.model_service.repository.get(model_id)
        return bool(installation and installation.status_code == ModelInstallStatus.INSTALLED.value and self.model_service.install_path(model).is_dir())

    def _owned(self, project_id: str, transcript_id: str) -> Transcript:
        transcript = self.repository.get(transcript_id)
        if transcript is None or transcript.project_id != project_id:
            raise KeyError("Transcript does not belong to this project.")
        return transcript

    def _ctranslate2_cuda_ready(self) -> bool:
        try:
            return bool(self._supported_compute_types("cuda"))
        except Exception:
            return False

    def _validate_ctranslate2_cuda(self) -> None:
        if not self._ctranslate2_cuda_ready():
            raise STTUnsupportedDevice("Speech recognition could not start with CUDA. Use CPU or install the required CTranslate2 CUDA runtime.")

    @staticmethod
    def _supported_compute_types(device: str) -> set[str]:
        try:
            ct2 = importlib.import_module("ctranslate2")
            values = ct2.get_supported_compute_types(device)
            return {str(item) for item in values}
        except ModuleNotFoundError:
            return set()
        except Exception:
            return set()
