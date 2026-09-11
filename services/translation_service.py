from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable
from uuid import uuid4

from domain.model_installation import ModelInstallStatus
from domain.project import utc_now_iso
from domain.translation import Translation, TranslationSourceType, TranslationStatus
from domain.translation_segment import (
    TranslationSegment,
    TranslationSegmentStatus,
    translation_source_hash,
)
from engines.translation.errors import (
    TranslationCancelled,
    TranslationError,
    TranslationInvalidRequest,
    TranslationModelNotInstalled,
    TranslationUnsupportedLanguagePair,
)
from engines.translation.manager import TranslationEngineManager
from engines.translation.types import TranslationRequest
from services.ai_resource_manager import AIResourceConflict, AIResourceManager
from services.model_service import ModelService
from services.translation_chunking_service import TranslationChunkingService
from services.translation_review_service import TranslationReviewService
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.script_repository import ScriptRepository
from storage.repositories.transcript_repository import TranscriptRepository
from storage.repositories.translation_repository import TranslationRepository
from workers.cancellation import CancellationToken

ProgressCallback = Callable[[int, int, str], None]


@dataclass(frozen=True, slots=True)
class SourceUnit:
    source_segment_id: str
    order: int
    text: str
    start_ms: int | None = None
    end_ms: int | None = None
    metadata: dict[str, object] | None = None


class TranslationService:
    LOCAL_ENGINE_ID = "local-marian"
    MANUAL_ENGINE_ID = "manual"
    MODEL_FAMILY = "marian-translation"

    def __init__(
        self,
        repository: TranslationRepository,
        project_repository: ProjectRepository,
        transcript_repository: TranscriptRepository,
        script_repository: ScriptRepository,
        model_service: ModelService,
        manager: TranslationEngineManager,
        chunking: TranslationChunkingService,
        review: TranslationReviewService,
        resource_manager: AIResourceManager | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.repository = repository
        self.project_repository = project_repository
        self.transcript_repository = transcript_repository
        self.script_repository = script_repository
        self.model_service = model_service
        self.manager = manager
        self.chunking = chunking
        self.review = review
        self.resource_manager = resource_manager
        self.logger = logger or logging.getLogger("sp_video_studio.translation")
        self._loaded_model_id = ""
        self._loaded_device = ""
        self._active_jobs = 0

    @property
    def active_jobs(self) -> int:
        return self._active_jobs

    def providers(self) -> tuple[dict[str, object], ...]:
        local = self.manager.get(self.LOCAL_ENGINE_ID).get_capabilities()
        return (
            {
                "id": self.LOCAL_ENGINE_ID,
                "name": "Local Translation",
                "offline": local.supports_offline,
                "requiresModel": True,
                "privacy": "Source text stays on this computer.",
            },
            {
                "id": self.MANUAL_ENGINE_ID,
                "name": "Manual Translation",
                "offline": True,
                "requiresModel": False,
                "privacy": "No AI provider is used.",
            },
        )

    def supported_models(self):
        return self.model_service.registry.list_family(self.MODEL_FAMILY)

    def resolve_model_id(self, source_language: str, target_language: str) -> str:
        for model in self.supported_models():
            meta = dict(model.metadata)
            if meta.get("sourceLanguage") == source_language and meta.get("targetLanguage") == target_language:
                return model.model_id
        raise TranslationUnsupportedLanguagePair()

    def model_ready(self, model_id: str) -> bool:
        try:
            model = self.model_service.registry.get(model_id)
        except KeyError:
            return False
        installation = self.model_service.repository.get(model_id)
        return bool(
            installation
            and installation.status_code == ModelInstallStatus.INSTALLED.value
            and self.model_service.install_path(model).is_dir()
        )

    def load(self, model_id: str, *, device: str = "auto") -> str:
        model = self._translation_model(model_id)
        if not self.model_ready(model_id):
            raise TranslationModelNotInstalled(f"{model.name} is not installed.")
        resolved_device = "cpu" if (device or "auto") == "auto" else device
        if resolved_device not in {"cpu", "cuda"} and not resolved_device.startswith("cuda:"):
            raise TranslationInvalidRequest("Device must be Auto, CPU, or CUDA.")
        if self.resource_manager is not None:
            try:
                self.resource_manager.prepare("translation", resolved_device)
            except AIResourceConflict as exc:
                raise TranslationInvalidRequest(str(exc)) from exc
        if self._loaded_model_id and (
            self._loaded_model_id != model_id or self._loaded_device != resolved_device
        ):
            self.unload()
        engine = self.manager.get(self.LOCAL_ENGINE_ID)
        if not engine.is_available():
            raise TranslationInvalidRequest(
                'Install the optional translation runtime with pip install -e ".[translation]".'
            )
        if not engine.is_loaded():
            path = self.model_service.install_path(model)
            self.model_service.acquire_model(model_id, loaded=True)
            try:
                engine.load(model_path=str(path), model_id=model_id, device=resolved_device)
            except Exception:
                self.model_service.release_model(model_id, unload=True)
                raise
            # Loaded but not actively translating yet.
            self.model_service.release_model(model_id, unload=False)
            self._loaded_model_id = model_id
            self._loaded_device = resolved_device
        return resolved_device

    def unload(self) -> None:
        model_id = self._loaded_model_id
        self.manager.get(self.LOCAL_ENGINE_ID).unload()
        self._loaded_model_id = ""
        self._loaded_device = ""
        if model_id:
            self.model_service.release_model(model_id, unload=True)

    def create_from_transcript(
        self,
        project_id: str,
        transcript_id: str,
        target_language: str,
        *,
        engine_id: str = LOCAL_ENGINE_ID,
        model_id: str = "",
        device: str = "auto",
        keep_terms: Iterable[str] = (),
    ) -> Translation:
        transcript = self.transcript_repository.get(transcript_id)
        if transcript is None or transcript.project_id != project_id:
            raise TranslationInvalidRequest("The selected transcript does not belong to this project.")
        source_language = transcript.detected_language or (transcript.language_mode if transcript.language_mode != "auto" else "")
        if source_language not in {"en", "km"}:
            raise TranslationInvalidRequest("Choose the transcript source language before translating.")
        units = [
            SourceUnit(
                source_segment_id=item.segment_id,
                order=item.order,
                text=item.text,
                start_ms=item.start_ms,
                end_ms=item.end_ms,
                metadata={"sourceKind": "transcript_segment"},
            )
            for item in self.transcript_repository.segments(transcript_id)
        ]
        return self._create(
            project_id,
            TranslationSourceType.TRANSCRIPT.value,
            transcript_id,
            source_language,
            target_language,
            units,
            engine_id=engine_id,
            model_id=model_id,
            device=device,
            keep_terms=keep_terms,
        )

    def create_from_script(
        self,
        project_id: str,
        script_id: str,
        target_language: str,
        *,
        engine_id: str = LOCAL_ENGINE_ID,
        model_id: str = "",
        device: str = "auto",
        keep_terms: Iterable[str] = (),
    ) -> Translation:
        script = self.script_repository.get_by_id(script_id)
        if script is None or script.project_id != project_id:
            raise TranslationInvalidRequest("The selected script does not belong to this project.")
        units = [
            SourceUnit(
                source_segment_id=item.section_id,
                order=item.order,
                text=item.content,
                metadata={"sourceKind": "script_section", "sectionTitle": item.title},
            )
            for item in self.script_repository.list_sections(script_id)
            if item.enabled
        ]
        return self._create(
            project_id,
            TranslationSourceType.SCRIPT.value,
            script_id,
            script.language,
            target_language,
            units,
            engine_id=engine_id,
            model_id=model_id,
            device=device,
            keep_terms=keep_terms,
        )

    def create_manual(
        self,
        project_id: str,
        text: str,
        source_language: str,
        target_language: str,
    ) -> Translation:
        self._require_project(project_id)
        if not text.strip():
            raise TranslationInvalidRequest("Enter text to translate.")
        unit = SourceUnit("manual", 0, text)
        return self._create(
            project_id,
            TranslationSourceType.MANUAL_TEXT.value,
            f"manual:{uuid4()}",
            source_language,
            target_language,
            [unit],
            engine_id=self.MANUAL_ENGINE_ID,
            model_id="",
            device="cpu",
            keep_terms=(),
        )

    def _create(
        self,
        project_id: str,
        source_type: str,
        source_id: str,
        source_language: str,
        target_language: str,
        units: list[SourceUnit],
        *,
        engine_id: str,
        model_id: str,
        device: str,
        keep_terms: Iterable[str],
    ) -> Translation:
        self._require_project(project_id)
        if source_language == target_language:
            raise TranslationInvalidRequest("Source and target languages must differ.")
        engine = self.manager.get(engine_id)
        if not engine.supports_language_pair(source_language, target_language):
            raise TranslationUnsupportedLanguagePair()
        if engine_id == self.LOCAL_ENGINE_ID:
            model_id = model_id or self.resolve_model_id(source_language, target_language)
            self._translation_model(model_id)
        translation = Translation(
            project_id=project_id,
            source_type=source_type,
            source_id=source_id,
            source_language=source_language,
            target_language=target_language,
            engine_id=engine_id,
            model_id=model_id,
            status=TranslationStatus.DRAFT,
            source_fingerprint=self._fingerprint_units(units),
            settings={"device": device, "keep_terms": [str(item) for item in keep_terms if str(item).strip()]},
            metadata={"sourceSegmentCount": len(units)},
        )
        segments = [
            TranslationSegment(
                translation_id=translation.translation_id,
                source_segment_id=unit.source_segment_id,
                order=order,
                start_ms=unit.start_ms,
                end_ms=unit.end_ms,
                source_text=unit.text,
                metadata=dict(unit.metadata or {}),
            )
            for order, unit in enumerate(sorted(units, key=lambda item: item.order))
        ]
        self.repository.create(translation, segments)
        return translation

    def translate_document(
        self,
        project_id: str,
        translation_id: str,
        cancellation: CancellationToken | None = None,
        progress: ProgressCallback | None = None,
        *,
        protect_edits: bool = True,
        include_failed: bool = True,
    ) -> Translation:
        token = cancellation or CancellationToken()
        translation = self._owned(project_id, translation_id)
        if translation.engine_id == self.MANUAL_ENGINE_ID:
            translation.status = TranslationStatus.DRAFT
            self.repository.update_translation(translation)
            return translation
        engine = self.manager.get(translation.engine_id)
        model_id = translation.model_id or self.resolve_model_id(translation.source_language, translation.target_language)
        device = str(translation.settings.get("device") or "auto")
        resolved_device = self.load(model_id, device=device)
        keep_terms = tuple(str(item) for item in translation.settings.get("keep_terms", []) if str(item).strip())
        segments = self.repository.segments(translation_id)
        candidates = [
            item
            for item in segments
            if not item.locked
            and (not protect_edits or not item.edited)
            and (item.status_code in {TranslationSegmentStatus.PENDING.value, TranslationSegmentStatus.NEEDS_ATTENTION.value}
                 or include_failed and item.status_code == TranslationSegmentStatus.FAILED.value)
        ]
        total = len(candidates)
        translation.status = TranslationStatus.TRANSLATING
        translation.model_id = model_id
        translation.settings["resolved_device"] = resolved_device
        self.repository.update_translation(translation)
        self.model_service.acquire_model(model_id, loaded=True)
        self._active_jobs += 1
        completed = 0
        failures = 0
        try:
            for segment in candidates:
                if token.is_cancelled:
                    raise TranslationCancelled()
                segment.status = TranslationSegmentStatus.TRANSLATING
                self.repository.update_segment(project_id, segment)
                if progress:
                    progress(completed, total, f"Translating {completed + 1} / {total}")
                try:
                    machine, warnings, provider_version = self._translate_text(
                        translation,
                        segment,
                        engine,
                        token,
                        keep_terms,
                    )
                    if not machine.strip():
                        raise TranslationError("The translation provider returned empty text.")
                    segment.machine_translation = machine
                    segment.translated_text = machine
                    segment.edited = False
                    segment.reviewed = False
                    segment.status = (
                        TranslationSegmentStatus.NEEDS_ATTENTION if warnings else TranslationSegmentStatus.TRANSLATED
                    )
                    segment.metadata["qualityWarnings"] = list(warnings)
                    segment.metadata["providerVersion"] = provider_version
                except TranslationCancelled:
                    raise
                except Exception as exc:
                    failures += 1
                    segment.status = TranslationSegmentStatus.FAILED
                    segment.metadata["lastError"] = self._friendly_error(exc)
                    self.logger.exception("Translation segment failed: %s", segment.segment_id)
                finally:
                    self.repository.update_segment(project_id, segment)
                completed += 1
                if progress:
                    progress(completed, total, f"Translated {completed} / {total}")
            remaining = self.repository.segments(translation_id)
            incomplete = any(
                item.status_code in {
                    TranslationSegmentStatus.PENDING.value,
                    TranslationSegmentStatus.FAILED.value,
                    TranslationSegmentStatus.NEEDS_ATTENTION.value,
                }
                and not item.reviewed
                for item in remaining
            )
            translation.status = TranslationStatus.DRAFT if failures or incomplete else TranslationStatus.REVIEW
            translation.metadata["completedSegments"] = sum(1 for item in remaining if item.machine_translation)
            translation.metadata["failedSegments"] = failures
            translation.updated_at = utc_now_iso()
            self.repository.update_translation(translation)
            return translation
        except TranslationCancelled:
            translation.status = TranslationStatus.DRAFT
            translation.metadata["cancelledAfterSegments"] = completed
            self.repository.update_translation(translation)
            self.logger.info("Translation cancelled: %s after %s/%s", translation_id, completed, total)
            raise
        finally:
            self._active_jobs = max(0, self._active_jobs - 1)
            self.model_service.release_model(model_id, unload=False)

    def _translate_text(self, translation, segment, engine, token, keep_terms):
        protected = self.review.protect(segment.source_text, keep_terms)
        chunks = self.chunking.chunk(protected.text, translation.source_language)
        translated_parts: list[str] = []
        provider_version = ""
        for chunk in chunks:
            if token.is_cancelled:
                raise TranslationCancelled()
            request = TranslationRequest(
                project_id=translation.project_id,
                source_language=translation.source_language,
                target_language=translation.target_language,
                text=chunk,
                engine_id=translation.engine_id,
                model_id=translation.model_id,
                device=str(translation.settings.get("resolved_device") or translation.settings.get("device") or "auto"),
                segment_id=segment.segment_id,
                transcript_id=translation.source_id if translation.source_type_code == TranslationSourceType.TRANSCRIPT.value else "",
                script_section_id=segment.source_segment_id if translation.source_type_code == TranslationSourceType.SCRIPT.value else "",
                keep_terms=keep_terms,
                settings=dict(translation.settings.get("engine", {})) if isinstance(translation.settings.get("engine"), dict) else {},
            )
            result = engine.translate(request, token)
            translated_parts.append(result.text)
            provider_version = result.provider_version or provider_version
        raw = "".join(translated_parts)
        restored, missing = self.review.restore(raw, protected)
        warnings = self.review.quality_warnings(segment.source_text, restored, missing_protected=missing)
        return restored, warnings, provider_version

    def edit_segment(self, project_id: str, translation_id: str, segment_id: str, text: str) -> TranslationSegment:
        self._owned(project_id, translation_id)
        segment = self._owned_segment(project_id, translation_id, segment_id)
        segment.translated_text = text
        segment.edited = text != segment.machine_translation
        segment.reviewed = False
        if text.strip() and segment.status_code == TranslationSegmentStatus.FAILED.value:
            segment.status = TranslationSegmentStatus.TRANSLATED
        return self.repository.update_segment(project_id, segment)

    def reset_segment(self, project_id: str, translation_id: str, segment_id: str) -> TranslationSegment:
        segment = self._owned_segment(project_id, translation_id, segment_id)
        segment.translated_text = segment.machine_translation
        segment.edited = False
        segment.reviewed = False
        segment.status = (
            TranslationSegmentStatus.TRANSLATED if segment.machine_translation else TranslationSegmentStatus.PENDING
        )
        return self.repository.update_segment(project_id, segment)

    def mark_reviewed(self, project_id: str, translation_id: str, segment_id: str, reviewed: bool = True) -> TranslationSegment:
        segment = self._owned_segment(project_id, translation_id, segment_id)
        if reviewed and not segment.translated_text.strip():
            raise TranslationInvalidRequest("Enter or generate a translation before marking it reviewed.")
        segment.reviewed = bool(reviewed)
        return self.repository.update_segment(project_id, segment)

    def set_locked(self, project_id: str, translation_id: str, segment_id: str, locked: bool) -> TranslationSegment:
        segment = self._owned_segment(project_id, translation_id, segment_id)
        if locked and not segment.translated_text.strip():
            raise TranslationInvalidRequest("Translate this segment before locking it.")
        segment.locked = bool(locked)
        return self.repository.update_segment(project_id, segment)

    def retranslate_segment(
        self,
        project_id: str,
        translation_id: str,
        segment_id: str,
        *,
        replace_manual: bool = False,
        cancellation: CancellationToken | None = None,
    ) -> TranslationSegment:
        translation = self._owned(project_id, translation_id)
        segment = self._owned_segment(project_id, translation_id, segment_id)
        if segment.locked:
            raise TranslationInvalidRequest("Unlock this translation before retranslating it.")
        if segment.edited and not replace_manual:
            raise TranslationInvalidRequest("This segment contains manual edits. Choose Replace Translation to overwrite them.")
        if translation.engine_id == self.MANUAL_ENGINE_ID:
            raise TranslationInvalidRequest("Manual translations cannot be retranslated automatically.")
        model_id = translation.model_id or self.resolve_model_id(translation.source_language, translation.target_language)
        self.load(model_id, device=str(translation.settings.get("device") or "auto"))
        engine = self.manager.get(translation.engine_id)
        machine, warnings, provider_version = self._translate_text(
            translation,
            segment,
            engine,
            cancellation or CancellationToken(),
            tuple(translation.settings.get("keep_terms", [])),
        )
        segment.machine_translation = machine
        segment.translated_text = machine
        segment.edited = False
        segment.reviewed = False
        segment.status = TranslationSegmentStatus.NEEDS_ATTENTION if warnings else TranslationSegmentStatus.TRANSLATED
        segment.metadata["qualityWarnings"] = list(warnings)
        segment.metadata["providerVersion"] = provider_version
        return self.repository.update_segment(project_id, segment)

    def retry_failed(self, project_id: str, translation_id: str, cancellation: CancellationToken | None = None) -> Translation:
        return self.translate_document(project_id, translation_id, cancellation, include_failed=True)

    def resume(self, project_id: str, translation_id: str, cancellation: CancellationToken | None = None, progress=None) -> Translation:
        return self.translate_document(project_id, translation_id, cancellation, progress, protect_edits=True, include_failed=True)

    def review_progress(self, project_id: str, translation_id: str) -> tuple[int, int, float]:
        self._owned(project_id, translation_id)
        segments = [item for item in self.repository.segments(translation_id) if item.status_code != TranslationSegmentStatus.ORPHANED.value]
        total = len(segments)
        reviewed = sum(1 for item in segments if item.reviewed)
        return reviewed, total, (reviewed / total if total else 1.0)

    def approve(self, project_id: str, translation_id: str, *, force: bool = False) -> Translation:
        translation = self._owned(project_id, translation_id)
        reviewed, total, _ = self.review_progress(project_id, translation_id)
        if not force and reviewed < total:
            raise TranslationInvalidRequest(f"{total - reviewed} segments have not been reviewed.")
        translation.status = TranslationStatus.APPROVED
        return self.repository.update_translation(translation)

    def search(self, project_id: str, translation_id: str, query: str) -> list[TranslationSegment]:
        self._owned(project_id, translation_id)
        return self.repository.search_segments(translation_id, query)

    def get(self, project_id: str, translation_id: str) -> tuple[Translation, list[TranslationSegment]]:
        translation = self._owned(project_id, translation_id)
        self.refresh_outdated(project_id, translation_id)
        translation = self._owned(project_id, translation_id)
        return translation, self.repository.segments(translation_id)

    def list_for_project(self, project_id: str) -> list[Translation]:
        self._require_project(project_id)
        return self.repository.list_for_project(project_id)

    def source_options(self, project_id: str) -> list[dict[str, object]]:
        self._require_project(project_id)
        result: list[dict[str, object]] = []
        script = self.script_repository.get_primary_by_project(project_id)
        if script is not None:
            result.append({
                "type": TranslationSourceType.SCRIPT.value,
                "id": script.script_id,
                "name": script.title,
                "language": script.language,
                "status": str(script.status),
                "primary": True,
            })
        for transcript in self.transcript_repository.list_for_project(project_id):
            language = transcript.detected_language or (transcript.language_mode if transcript.language_mode != "auto" else "")
            result.append({
                "type": TranslationSourceType.TRANSCRIPT.value,
                "id": transcript.transcript_id,
                "name": f"Transcript {transcript.transcript_id[:8]}",
                "language": language,
                "status": transcript.status_code,
                "active": transcript.active,
                "mediaId": transcript.media_id,
            })
        return result

    def refresh_outdated(self, project_id: str, translation_id: str) -> bool:
        translation = self._owned(project_id, translation_id)
        try:
            units = self._current_units(translation)
        except TranslationInvalidRequest:
            return False
        current = self._fingerprint_units(units)
        if current and current != translation.source_fingerprint and translation.status_code != TranslationStatus.OUTDATED.value:
            translation.status = TranslationStatus.OUTDATED
            self.repository.update_translation(translation)
            return True
        return current != translation.source_fingerprint

    def sync_source(self, project_id: str, translation_id: str) -> Translation:
        translation = self._owned(project_id, translation_id)
        units = self._current_units(translation)
        existing = {item.source_segment_id: item for item in self.repository.segments(translation_id)}
        current_ids: set[str] = set()
        changed = False
        for order, unit in enumerate(sorted(units, key=lambda item: item.order)):
            current_ids.add(unit.source_segment_id)
            source_hash = translation_source_hash(unit.text, unit.start_ms, unit.end_ms)
            segment = existing.get(unit.source_segment_id)
            if segment is None:
                self.repository.create_segment(
                    project_id,
                    TranslationSegment(
                        translation_id=translation_id,
                        source_segment_id=unit.source_segment_id,
                        order=order,
                        start_ms=unit.start_ms,
                        end_ms=unit.end_ms,
                        source_text=unit.text,
                        metadata=dict(unit.metadata or {}),
                    ),
                )
                changed = True
                continue
            segment.order = order
            segment.start_ms = unit.start_ms
            segment.end_ms = unit.end_ms
            segment.metadata.pop("orphaned", None)
            if segment.source_hash != source_hash:
                segment.source_text = unit.text
                segment.source_hash = source_hash
                segment.reviewed = False
                segment.status = TranslationSegmentStatus.NEEDS_ATTENTION
                segment.metadata["sourceChanged"] = True
                changed = True
            elif segment.status_code == TranslationSegmentStatus.ORPHANED.value:
                segment.status = TranslationSegmentStatus.TRANSLATED if segment.machine_translation else TranslationSegmentStatus.PENDING
                changed = True
            self.repository.update_segment(project_id, segment)
        for source_id, segment in existing.items():
            if source_id not in current_ids:
                segment.status = TranslationSegmentStatus.ORPHANED
                segment.metadata["orphaned"] = True
                segment.reviewed = False
                self.repository.update_segment(project_id, segment)
                changed = True
        translation.source_fingerprint = self._fingerprint_units(units)
        translation.status = TranslationStatus.OUTDATED if changed else translation.status
        return self.repository.update_translation(translation)

    def get_reviewed_translation_segments(self, project_id: str, translation_id: str) -> list[dict[str, object]]:
        self._owned(project_id, translation_id)
        return [
            {
                "segment_id": item.segment_id,
                "source_segment_id": item.source_segment_id,
                "start_ms": item.start_ms,
                "end_ms": item.end_ms,
                "target_text": item.translated_text,
            }
            for item in self.repository.segments(translation_id)
            if item.reviewed and item.status_code != TranslationSegmentStatus.ORPHANED.value and item.translated_text.strip()
        ]

    def get_dubbing_segments(self, project_id: str, translation_id: str) -> list[dict[str, object]]:
        translation = self._owned(project_id, translation_id)
        return [
            {
                "segment_id": item.segment_id,
                "source_segment_id": item.source_segment_id,
                "start_ms": item.start_ms,
                "end_ms": item.end_ms,
                "source_text": item.source_text,
                "target_text": item.translated_text,
                "language": translation.target_language,
                "review_status": "reviewed" if item.reviewed else "unreviewed",
            }
            for item in self.repository.segments(translation_id)
            if item.status_code != TranslationSegmentStatus.ORPHANED.value and item.translated_text.strip()
        ]

    def export_txt(self, project_id: str, translation_id: str, destination: Path, *, bilingual: bool = False) -> Path:
        translation = self._owned(project_id, translation_id)
        from services.transcript_analysis_service import format_timestamp_ms
        lines: list[str] = []
        for item in self.repository.segments(translation_id):
            if item.status_code == TranslationSegmentStatus.ORPHANED.value:
                continue
            if item.start_ms is not None and item.end_ms is not None:
                lines.append(f"[{format_timestamp_ms(item.start_ms)} - {format_timestamp_ms(item.end_ms)}]")
            if bilingual:
                lines.extend([f"{translation.source_language.upper()}:", item.source_text, f"{translation.target_language.upper()}:", item.translated_text])
            else:
                lines.append(item.translated_text)
            lines.append("")
        destination = Path(destination)
        if destination.suffix.lower() != ".txt":
            destination = destination.with_suffix(".txt")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return destination

    def combined_translation_text(self, project_id: str, translation_id: str) -> str:
        self._owned(project_id, translation_id)
        return "\n\n".join(
            item.translated_text.strip()
            for item in self.repository.segments(translation_id)
            if item.status_code != TranslationSegmentStatus.ORPHANED.value and item.translated_text.strip()
        )

    def delete(self, project_id: str, translation_id: str) -> None:
        self._owned(project_id, translation_id)
        self.repository.delete(project_id, translation_id)

    def duplicate_project_translations(
        self,
        source_project_id: str,
        target_project_id: str,
        *,
        transcript_map: dict[str, str] | None = None,
        transcript_segment_map: dict[str, str] | None = None,
        script_map: dict[str, str] | None = None,
        script_section_map: dict[str, str] | None = None,
    ) -> int:
        count, _, _ = self.duplicate_project_translations_with_map(
            source_project_id, target_project_id, transcript_map=transcript_map,
            transcript_segment_map=transcript_segment_map, script_map=script_map,
            script_section_map=script_section_map,
        )
        return count

    def duplicate_project_translations_with_map(
        self,
        source_project_id: str,
        target_project_id: str,
        *,
        transcript_map: dict[str, str] | None = None,
        transcript_segment_map: dict[str, str] | None = None,
        script_map: dict[str, str] | None = None,
        script_section_map: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, str], dict[str, str]]:
        transcript_map = transcript_map or {}
        transcript_segment_map = transcript_segment_map or {}
        script_map = script_map or {}
        script_section_map = script_section_map or {}
        count = 0
        translation_id_map: dict[str, str] = {}
        translation_segment_id_map: dict[str, str] = {}
        for source in self.repository.list_for_project(source_project_id):
            if source.source_type_code == TranslationSourceType.TRANSCRIPT.value:
                target_source_id = transcript_map.get(source.source_id)
                segment_map = transcript_segment_map
            elif source.source_type_code == TranslationSourceType.SCRIPT.value:
                target_source_id = script_map.get(source.source_id)
                segment_map = script_section_map
            else:
                target_source_id = f"manual:{uuid4()}"
                segment_map = {}
            if not target_source_id:
                continue
            clone = Translation(
                project_id=target_project_id,
                source_type=source.source_type_code,
                source_id=target_source_id,
                source_language=source.source_language,
                target_language=source.target_language,
                engine_id=source.engine_id,
                model_id=source.model_id,
                status=source.status_code,
                source_fingerprint=source.source_fingerprint,
                settings=dict(source.settings),
                metadata=dict(source.metadata),
            )
            cloned_segments: list[TranslationSegment] = []
            for item in self.repository.segments(source.translation_id):
                cloned_segments.append(
                    TranslationSegment(
                        translation_id=clone.translation_id,
                        source_segment_id=segment_map.get(item.source_segment_id, item.source_segment_id if source.source_type_code == TranslationSourceType.MANUAL_TEXT.value else ""),
                        order=item.order,
                        start_ms=item.start_ms,
                        end_ms=item.end_ms,
                        source_text=item.source_text,
                        machine_translation=item.machine_translation,
                        translated_text=item.translated_text,
                        status=item.status_code,
                        edited=item.edited,
                        reviewed=item.reviewed,
                        locked=item.locked,
                        confidence=item.confidence,
                        notes=item.notes,
                        source_hash=item.source_hash,
                        metadata=dict(item.metadata),
                    )
                )
            self.repository.create(clone, cloned_segments)
            translation_id_map[source.translation_id] = clone.translation_id
            for original_segment, cloned_segment in zip(self.repository.segments(source.translation_id), cloned_segments):
                translation_segment_id_map[original_segment.segment_id] = cloned_segment.segment_id
            try:
                clone.source_fingerprint = self._fingerprint_units(self._current_units(clone))
                self.repository.update_translation(clone)
            except Exception:
                pass
            count += 1
        return count, translation_id_map, translation_segment_id_map

    def _current_units(self, translation: Translation) -> list[SourceUnit]:
        if translation.source_type_code == TranslationSourceType.TRANSCRIPT.value:
            transcript = self.transcript_repository.get(translation.source_id)
            if transcript is None or transcript.project_id != translation.project_id:
                raise TranslationInvalidRequest("The source transcript no longer exists.")
            return [
                SourceUnit(item.segment_id, item.order, item.text, item.start_ms, item.end_ms, {"sourceKind": "transcript_segment"})
                for item in self.transcript_repository.segments(translation.source_id)
            ]
        if translation.source_type_code == TranslationSourceType.SCRIPT.value:
            script = self.script_repository.get_by_id(translation.source_id)
            if script is None or script.project_id != translation.project_id:
                raise TranslationInvalidRequest("The source script no longer exists.")
            return [
                SourceUnit(item.section_id, item.order, item.content, None, None, {"sourceKind": "script_section", "sectionTitle": item.title})
                for item in self.script_repository.list_sections(translation.source_id)
                if item.enabled
            ]
        segments = self.repository.segments(translation.translation_id)
        return [SourceUnit(item.source_segment_id, item.order, item.source_text, item.start_ms, item.end_ms, dict(item.metadata)) for item in segments]

    def _translation_model(self, model_id: str):
        try:
            model = self.model_service.registry.get(model_id)
        except KeyError as exc:
            raise TranslationModelNotInstalled("Unknown translation model.") from exc
        if model.family != self.MODEL_FAMILY:
            raise TranslationInvalidRequest("The selected model is not a translation model.")
        return model

    def _owned(self, project_id: str, translation_id: str) -> Translation:
        translation = self.repository.get(translation_id)
        if translation is None or translation.project_id != project_id:
            raise TranslationInvalidRequest("This translation does not belong to the current project.")
        return translation

    def _owned_segment(self, project_id: str, translation_id: str, segment_id: str) -> TranslationSegment:
        self._owned(project_id, translation_id)
        segment = self.repository.segment(segment_id)
        if segment is None or segment.translation_id != translation_id:
            raise TranslationInvalidRequest("This translation segment does not belong to the current translation.")
        return segment

    def _require_project(self, project_id: str):
        project = self.project_repository.get_by_id(project_id)
        if project is None:
            raise TranslationInvalidRequest("This project could not be found.")
        return project

    @staticmethod
    def _fingerprint_units(units: Iterable[SourceUnit]) -> str:
        digest = hashlib.sha256()
        for unit in sorted(units, key=lambda item: item.order):
            digest.update(str(unit.source_segment_id).encode("utf-8")); digest.update(b"\0")
            digest.update(str(unit.order).encode("ascii")); digest.update(b"\0")
            digest.update(str(unit.start_ms if unit.start_ms is not None else "").encode("ascii")); digest.update(b"\0")
            digest.update(str(unit.end_ms if unit.end_ms is not None else "").encode("ascii")); digest.update(b"\0")
            digest.update(unit.text.encode("utf-8")); digest.update(b"\0")
        return digest.hexdigest()

    @staticmethod
    def _friendly_error(exc: Exception) -> str:
        if isinstance(exc, TranslationError):
            return str(exc) or exc.user_message
        return str(exc) or "Translation failed."
