from __future__ import annotations

import hashlib
import json
import logging
import shutil
import wave
from pathlib import Path
from typing import Callable
from uuid import uuid4

from domain.generated_audio import GeneratedAudio, GeneratedAudioStatus
from domain.narration import NarrationJobState, NarrationProgress, TTSChunk
from domain.project import Project
from domain.voice_config import VoiceConfig
from engines.tts.errors import TTSCancelled, TTSGenerationError, TTSInvalidRequest
from engines.tts.types import TTSRequest
from services.project_service import ProjectFilesMissingError
from services.script_service import ScriptService
from services.tts_chunking_service import TTSChunkingService
from services.tts_service import TTSService
from storage.repositories.generated_audio_repository import GeneratedAudioRepository
from storage.repositories.project_repository import ProjectRepository
from workers.cancellation import CancellationToken

ProgressCallback = Callable[[NarrationProgress], None]
SECTION_PAUSE_MS = 260
CHUNK_PAUSE_MS = 60


class NarrationService:
    def __init__(
        self,
        repository: GeneratedAudioRepository,
        project_repository: ProjectRepository,
        script_service: ScriptService,
        tts_service: TTSService,
        chunking: TTSChunkingService | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.repository = repository
        self.project_repository = project_repository
        self.script_service = script_service
        self.tts_service = tts_service
        self.chunking = chunking or TTSChunkingService()
        self.logger = logger or logging.getLogger("sp_video_studio.narration")

    def generate_full(
        self,
        project_id: str,
        voice_config: VoiceConfig,
        cancellation: CancellationToken | None = None,
        progress: ProgressCallback | None = None,
    ) -> GeneratedAudio:
        project = self._project(project_id)
        script, sections = self.script_service.load_or_create(project_id)
        chunks = self.chunking.chunk_sections(sections, script.language)
        if not chunks:
            raise TTSInvalidRequest("Add narration text to at least one enabled script section.")
        text_hash = narration_text_hash(script.language, sections)
        return self._generate(
            project=project,
            script_id=script.script_id,
            section_id=None,
            language=script.language,
            chunks=chunks,
            text_hash=text_hash,
            voice_config=voice_config,
            cancellation=cancellation,
            progress=progress,
            active=True,
        )

    def generate_section(
        self,
        project_id: str,
        section_id: str,
        voice_config: VoiceConfig,
        cancellation: CancellationToken | None = None,
        progress: ProgressCallback | None = None,
    ) -> GeneratedAudio:
        project = self._project(project_id)
        script, sections = self.script_service.load_or_create(project_id)
        section = next((item for item in sections if item.section_id == section_id), None)
        if section is None:
            raise TTSInvalidRequest("This script section could not be found.")
        if not section.content.strip():
            raise TTSInvalidRequest("This script section is empty.")
        chunks = self.chunking.chunk_text(section.content, script.language, section.section_id)
        text_hash = stable_text_hash(script.language, [(section.order, section.section_id, section.content)])
        return self._generate(
            project=project,
            script_id=script.script_id,
            section_id=section.section_id,
            language=script.language,
            chunks=chunks,
            text_hash=text_hash,
            voice_config=voice_config,
            cancellation=cancellation,
            progress=progress,
            active=False,
        )

    def generate_preview(
        self,
        project_id: str,
        text: str,
        language: str,
        voice_config: VoiceConfig,
        cancellation: CancellationToken | None = None,
    ) -> Path:
        project = self._project(project_id)
        preview_text = text.strip()
        if not preview_text:
            raise TTSInvalidRequest("Enter preview text first.")
        if len(preview_text) > 400:
            raise TTSInvalidRequest("Preview text must be 400 characters or fewer.")
        cache = Path(project.project_path) / "cache" / "tts" / "previews"
        cache.mkdir(parents=True, exist_ok=True)
        output = cache / f"preview-{uuid4().hex[:12]}.wav"
        request = TTSRequest(project_id, preview_text, language, output, voice_config=voice_config)
        self.tts_service.generate(request, cancellation)
        self._validate_wav(output)
        return output


    def prepare_reference_audio(self, project_id: str, source: str | Path) -> Path:
        project = self._project(project_id)
        validated = self.tts_service.validate_reference(source)
        reference_root = (Path(project.project_path) / "audio" / "references").resolve()
        reference_root.mkdir(parents=True, exist_ok=True)
        resolved = validated.resolve()
        if _is_within(resolved, reference_root):
            return resolved
        suffix = validated.suffix.lower() or ".wav"
        target = reference_root / f"reference-{uuid4().hex[:12]}{suffix}"
        shutil.copy2(validated, target)
        return target

    def list_generated(self, project_id: str) -> list[GeneratedAudio]:
        project = self._project(project_id)
        result = self.repository.list_for_project(project_id)
        root = Path(project.project_path).resolve()
        for item in result:
            path = Path(item.file_path)
            if not path.is_file() or not _is_within(path, root):
                item.status = GeneratedAudioStatus.FAILED
        return result

    def active(self, project_id: str) -> GeneratedAudio | None:
        return self.repository.active_for_project(project_id)

    def set_active_generated(self, project_id: str, generated_audio_id: str) -> GeneratedAudio:
        item = self.get_generated(project_id, generated_audio_id)
        if not Path(item.file_path).is_file():
            raise TTSInvalidRequest("Generated narration file could not be found.")
        self.repository.set_active(project_id, generated_audio_id)
        item.active = True
        return item

    def get_generated(self, project_id: str, generated_audio_id: str) -> GeneratedAudio:
        self._project(project_id)
        item = self.repository.get(generated_audio_id)
        if item is None or item.project_id != project_id:
            raise TTSInvalidRequest("Generated narration could not be found.")
        return item

    def narration_is_current(self, project_id: str, generated: GeneratedAudio | None = None) -> bool:
        item = generated or self.repository.active_for_project(project_id)
        if item is None:
            return False
        script, sections = self.script_service.load_or_create(project_id)
        return item.text_hash == narration_text_hash(script.language, sections)

    def delete_generated(self, project_id: str, generated_audio_id: str) -> None:
        project = self._project(project_id)
        item = self.repository.get(generated_audio_id)
        if item is None or item.project_id != project_id:
            raise TTSInvalidRequest("Generated narration could not be found.")
        project_root = Path(project.project_path).resolve()
        narration_root = (project_root / "audio" / "narration").resolve()
        target = Path(item.file_path).resolve()
        if target != narration_root and narration_root not in target.parents:
            raise TTSInvalidRequest("Refusing to delete audio outside the project narration folder.")
        self.repository.delete(project_id, generated_audio_id)
        target.unlink(missing_ok=True)

    def duplicate_project_audio(self, source_project_id: str, duplicate_project_id: str) -> dict[str, str]:
        source_project = self._project(source_project_id)
        duplicate_project = self._project(duplicate_project_id)
        source_script, source_sections = self.script_service.load_or_create(source_project_id)
        duplicate_script, duplicate_sections = self.script_service.load_or_create(duplicate_project_id)
        section_map = {
            source.section_id: duplicate.section_id
            for source, duplicate in zip(
                sorted(source_sections, key=lambda item: item.order),
                sorted(duplicate_sections, key=lambda item: item.order),
                strict=False,
            )
        }
        source_root = Path(source_project.project_path).resolve()
        duplicate_root = Path(duplicate_project.project_path).resolve()
        # ProjectService already copied project-owned folders for portability. Rebuild
        # narration files with fresh IDs so stale copied filenames do not become
        # untracked duplicate generations. Reference recordings remain copied.
        duplicate_narration = duplicate_root / "audio" / "narration"
        shutil.rmtree(duplicate_narration, ignore_errors=True)
        duplicate_narration.mkdir(parents=True, exist_ok=True)
        id_map: dict[str, str] = {}
        for item in self.repository.list_for_project(source_project_id):
            source_path = Path(item.file_path).resolve()
            if not source_path.is_file() or not _is_within(source_path, source_root):
                continue
            new_id = str(uuid4())
            target = duplicate_root / "audio" / "narration" / f"{new_id}.wav"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target)
            voice_config = dict(item.voice_config)
            for key in ("referenceAudioPath", "promptAudioPath"):
                raw = str(voice_config.get(key) or "")
                if not raw:
                    continue
                candidate = Path(raw).resolve()
                if _is_within(candidate, source_root):
                    relative = candidate.relative_to(source_root)
                    remapped = duplicate_root / relative
                    if remapped.exists():
                        voice_config[key] = str(remapped)
            copy = GeneratedAudio(
                generated_audio_id=new_id,
                project_id=duplicate_project_id,
                script_id=duplicate_script.script_id,
                section_id=section_map.get(item.section_id or ""),
                engine=item.engine,
                model_id=item.model_id,
                language=item.language,
                voice_mode=item.voice_mode,
                voice_config=voice_config,
                text_hash=item.text_hash,
                file_path=str(target),
                duration_ms=item.duration_ms,
                sample_rate=item.sample_rate,
                channels=item.channels,
                generation_settings=dict(item.generation_settings),
                status=item.status,
                active=item.active,
                metadata=dict(item.metadata),
            )
            self.repository.create(copy)
            id_map[item.id] = new_id
        return id_map

    def _generate(
        self,
        *,
        project: Project,
        script_id: str,
        section_id: str | None,
        language: str,
        chunks: list[TTSChunk],
        text_hash: str,
        voice_config: VoiceConfig,
        cancellation: CancellationToken | None,
        progress: ProgressCallback | None,
        active: bool,
    ) -> GeneratedAudio:
        token = cancellation or CancellationToken()
        generation_id = str(uuid4())
        project_root = Path(project.project_path)
        final_dir = project_root / "audio" / "narration"
        temp_dir = project_root / "cache" / "tts" / generation_id
        final_dir.mkdir(parents=True, exist_ok=True)
        temp_dir.mkdir(parents=True, exist_ok=True)
        final_path = final_dir / f"{generation_id}.wav"
        chunk_paths: list[Path] = []
        results = []
        try:
            self._emit(progress, NarrationJobState.PREPARING, 0, len(chunks), "Preparing narration")
            token.raise_if_cancelled()
            self._emit(progress, NarrationJobState.LOADING_MODEL, 0, len(chunks), "Loading VoxCPM2")
            self.tts_service.load(voice_config.device_code)
            for index, chunk in enumerate(chunks, start=1):
                token.raise_if_cancelled()
                self._emit(progress, NarrationJobState.GENERATING, index - 1, len(chunks), f"Generating {index}/{len(chunks)}")
                chunk_path = temp_dir / f"chunk-{index:04d}.wav"
                request = TTSRequest(
                    project_id=project.project_id,
                    text=chunk.text,
                    language=language,
                    output_path=chunk_path,
                    voice_config=voice_config,
                    script_id=script_id,
                    section_id=chunk.section_id,
                    metadata={"chunkOrder": chunk.order},
                )
                result = self.tts_service.generate(request, token)
                chunk_paths.append(chunk_path)
                results.append(result)
                self._emit(progress, NarrationJobState.GENERATING, index, len(chunks), f"Generated {index}/{len(chunks)}")
            token.raise_if_cancelled()
            self._emit(progress, NarrationJobState.COMBINING, len(chunks), len(chunks), "Combining narration")
            if len(chunk_paths) == 1:
                shutil.copy2(chunk_paths[0], final_path)
            else:
                self._concat_wav(chunk_paths, final_path, chunks)
            self._emit(progress, NarrationJobState.VALIDATING, len(chunks), len(chunks), "Validating audio")
            duration_ms, sample_rate, channels = self._validate_wav(final_path)
            first = results[0] if results else None
            item = GeneratedAudio(
                generated_audio_id=generation_id,
                project_id=project.project_id,
                script_id=script_id,
                section_id=section_id,
                engine="voxcpm2",
                model_id="voxcpm2",
                language=language,
                voice_mode=voice_config.mode_code,
                voice_config=voice_config.to_dict(),
                text_hash=text_hash,
                file_path=str(final_path),
                duration_ms=duration_ms,
                sample_rate=sample_rate,
                channels=channels,
                generation_settings={
                    "cfgValue": voice_config.cfg_value,
                    "inferenceTimesteps": voice_config.inference_timesteps,
                    "seed": voice_config.seed,
                    "device": voice_config.device_code,
                },
                status=GeneratedAudioStatus.COMPLETED,
                active=active,
                metadata={
                    "engineVersion": first.engine_version if first else "",
                    "modelVersion": first.model_version if first else "openbmb/VoxCPM2",
                    "sourceIdentifier": "openbmb/VoxCPM2",
                    "chunkCount": len(chunks),
                },
            )
            self.repository.create(item)
            self._emit(progress, NarrationJobState.COMPLETED, len(chunks), len(chunks), "Narration ready")
            return item
        except RuntimeError as exc:
            if token.is_cancelled or "cancelled" in str(exc).lower():
                final_path.unlink(missing_ok=True)
                raise TTSCancelled() from exc
            final_path.unlink(missing_ok=True)
            raise
        except Exception:
            final_path.unlink(missing_ok=True)
            raise
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @staticmethod
    def _concat_wav(paths: list[Path], output: Path, chunks: list[TTSChunk] | None = None) -> None:
        params = None
        previous_section: str | None = None
        output.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output), "wb") as writer:
            for index, path in enumerate(paths):
                with wave.open(str(path), "rb") as reader:
                    current = (reader.getnchannels(), reader.getsampwidth(), reader.getframerate())
                    if params is None:
                        params = current
                        writer.setnchannels(current[0]); writer.setsampwidth(current[1]); writer.setframerate(current[2])
                    elif current != params:
                        raise TTSGenerationError("Generated chunks use incompatible WAV formats.")
                    if index > 0 and params is not None:
                        section = chunks[index].section_id if chunks and index < len(chunks) else None
                        pause_ms = SECTION_PAUSE_MS if section and previous_section and section != previous_section else CHUNK_PAUSE_MS
                        silent_frames = int(params[2] * pause_ms / 1000.0)
                        writer.writeframes(b"\x00" * silent_frames * params[0] * params[1])
                    while True:
                        block = reader.readframes(8192)
                        if not block:
                            break
                        writer.writeframes(block)
                    if chunks and index < len(chunks):
                        previous_section = chunks[index].section_id

    @staticmethod
    def _validate_wav(path: Path) -> tuple[int, int, int]:
        if not path.is_file() or path.stat().st_size <= 44:
            raise TTSGenerationError("Generated WAV is missing or empty.")
        try:
            with wave.open(str(path), "rb") as reader:
                rate = int(reader.getframerate())
                channels = int(reader.getnchannels())
                frames = int(reader.getnframes())
        except (wave.Error, OSError) as exc:
            raise TTSGenerationError("Generated audio is not a valid WAV file.") from exc
        if rate <= 0 or channels <= 0 or frames <= 0:
            raise TTSGenerationError("Generated WAV metadata is invalid.")
        return int(round(frames / rate * 1000.0)), rate, channels

    def _project(self, project_id: str) -> Project:
        project = self.project_repository.get_by_id(project_id)
        if project is None:
            raise TTSInvalidRequest("The project could not be found.")
        if not Path(project.project_path).is_dir():
            raise ProjectFilesMissingError()
        return project

    @staticmethod
    def _emit(callback: ProgressCallback | None, state: NarrationJobState, current: int, total: int, message: str) -> None:
        if callback:
            callback(NarrationProgress(state, current, total, message))


def narration_text_hash(language: str, sections) -> str:
    values = [
        (section.order, section.section_id, section.content)
        for section in sorted((s for s in sections if s.enabled and s.content.strip()), key=lambda item: item.order)
    ]
    return stable_text_hash(language, values)


def stable_text_hash(language: str, sections: list[tuple[int, str, str]]) -> str:
    # Stable across project duplication: section IDs are storage identity, not narration content.
    payload = {
        "language": language,
        "sections": [{"order": int(order), "text": text} for order, _section_id, text in sections],
    }
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False
