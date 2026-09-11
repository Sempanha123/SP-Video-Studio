from __future__ import annotations

import hashlib
import json
import logging
import shutil
from dataclasses import replace
from pathlib import Path
from typing import Callable
from uuid import uuid4

from domain.project import SUPPORTED_LANGUAGES, utc_now_iso
from domain.voice_config import VoiceConfig
from domain.voice_profile import VoiceProfile, VoiceType
from engines.voice_registry import VoiceRegistry
from storage.repositories.voice_repository import VoiceRepository


MAX_VOICE_DESCRIPTION = 800
DEFAULT_PREVIEW_TEXT = {
    "en": "Welcome to SP Video Studio. This is a preview of the selected voice.",
    "km": "សួស្តី! នេះគឺជាសំឡេងសាកល្បងសម្រាប់គម្រោងរបស់អ្នក។",
}
CATEGORY_FILTERS = {
    "news": {"news anchor"},
    "story": {"storyteller"},
    "documentary": {"documentary"},
    "professional": {"professional"},
}
WORKFLOW_CATEGORIES = {
    "news": {"News Anchor"},
    "story": {"Storyteller"},
    "translate": {"Professional"},
    "video": {"Professional", "Documentary", "Friendly"},
    "shorts": {"Energetic", "Friendly"},
    "batch": {"Professional"},
}


class VoiceServiceError(RuntimeError):
    pass


class VoiceInUseError(VoiceServiceError):
    def __init__(self, count: int) -> None:
        self.count = count
        super().__init__(f"This voice is currently used by {count} project or section assignment(s).")


class VoiceService:
    def __init__(
        self,
        registry: VoiceRegistry,
        repository: VoiceRepository,
        voice_root: Path,
        reference_validator: Callable[[str | Path], Path] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.registry = registry
        self.repository = repository
        self.voice_root = Path(voice_root)
        self.reference_validator = reference_validator
        self.logger = logger or logging.getLogger("sp_video_studio.voices")
        self.designed_root = self.voice_root / "designed"
        self.reference_root = self.voice_root / "references"
        self.designed_root.mkdir(parents=True, exist_ok=True)
        self.reference_root.mkdir(parents=True, exist_ok=True)

    def list_all(self) -> list[VoiceProfile]:
        prefs = self.repository.all_preferences()
        voices = [replace(item) for item in self.registry.list_all()] + self.repository.list_profiles()
        for voice in voices:
            pref = prefs.get(voice.voice_id, {})
            voice.favorite = bool(pref.get("favorite", False))
            voice.last_used_at = pref.get("last_used_at") or None
            voice.usage_count = int(pref.get("usage_count", 0))
        return voices

    def get(self, voice_id: str) -> VoiceProfile:
        voice = self.registry.get(voice_id) or self.repository.get_profile(voice_id)
        if voice is None:
            raise VoiceServiceError("This voice could not be found.")
        value = replace(voice)
        pref = self.repository.preference(voice_id)
        value.favorite = bool(pref["favorite"])
        value.last_used_at = pref["last_used_at"] or None
        value.usage_count = int(pref["usage_count"])
        return value

    def browse(
        self,
        query: str = "",
        category_filter: str = "all",
        language: str = "all",
        engine: str = "all",
        sort_by: str = "recommended",
        project_language: str = "",
        project_workflow: str = "",
    ) -> list[VoiceProfile]:
        query = query.strip().casefold()
        category_filter = category_filter.strip().lower()
        result = []
        for voice in self.list_all():
            if language not in {"", "all"} and voice.language != language:
                continue
            if engine not in {"", "all"} and voice.engine_id != engine:
                continue
            if category_filter == "my" and voice.is_builtin:
                continue
            if category_filter == "favorites" and not voice.favorite:
                continue
            if category_filter in CATEGORY_FILTERS and voice.category.casefold() not in CATEGORY_FILTERS[category_filter]:
                continue
            haystack = " ".join([voice.name, voice.category, *voice.style_tags]).casefold()
            if query and query not in haystack:
                continue
            result.append(voice)

        def recommended_score(item: VoiceProfile) -> tuple[int, int, str]:
            language_match = 1 if project_language and item.language == project_language else 0
            category_match = 1 if item.category in WORKFLOW_CATEGORIES.get(project_workflow, set()) else 0
            return (language_match + category_match, item.usage_count, item.name.casefold())

        if sort_by == "name":
            result.sort(key=lambda item: item.name.casefold())
        elif sort_by == "recent":
            result.sort(key=lambda item: item.last_used_at or "", reverse=True)
        elif sort_by == "favorites":
            result.sort(key=lambda item: (item.favorite, item.usage_count, item.name.casefold()), reverse=True)
        else:
            result.sort(key=recommended_score, reverse=True)
        return result

    def toggle_favorite(self, voice_id: str) -> bool:
        voice = self.get(voice_id)
        value = not voice.favorite
        self.repository.set_favorite(voice_id, value)
        return value

    def mark_used(self, voice_id: str) -> None:
        self.get(voice_id)
        self.repository.mark_used(voice_id)

    def create_designed(
        self,
        name: str,
        language: str,
        category: str,
        voice_description: str,
        style_tags: list[str] | None = None,
        settings: dict | None = None,
    ) -> VoiceProfile:
        self._validate_common(name, language, category)
        description = voice_description.strip()
        if not description:
            raise VoiceServiceError("Voice description is required.")
        if len(description) > MAX_VOICE_DESCRIPTION:
            raise VoiceServiceError(f"Keep voice descriptions under {MAX_VOICE_DESCRIPTION} characters.")
        voice = VoiceProfile(
            name=name.strip(), voice_type=VoiceType.DESIGNED, language=language, category=category.strip(),
            voice_description=description, style_tags=self._tags(style_tags), settings=self._safe_settings(settings), validated=True,
        )
        self.repository.create_profile(voice)
        self.logger.info("Designed voice created: %s", voice.voice_id)
        return voice

    def create_reference(
        self,
        name: str,
        language: str,
        category: str,
        source_audio: str | Path,
        consent_confirmed: bool,
        style_tags: list[str] | None = None,
        notes: str = "",
    ) -> VoiceProfile:
        if not consent_confirmed:
            raise VoiceServiceError("Confirm that you have permission to use this voice recording.")
        self._validate_common(name, language, category)
        source = self._validate_reference(source_audio)
        voice = VoiceProfile(
            name=name.strip(), voice_type=VoiceType.REFERENCE, language=language, category=category.strip(),
            style_tags=self._tags(style_tags), notes=notes.strip(), validated=True,
        )
        folder = self.reference_root / voice.voice_id
        target = folder / f"reference{source.suffix.lower()}"
        try:
            folder.mkdir(parents=True, exist_ok=False)
            shutil.copy2(source, target)
            voice.reference_audio_path = str(target)
            voice.duration_ms = self._reference_duration_ms(target)
            self.repository.create_profile(voice)
        except Exception:
            shutil.rmtree(folder, ignore_errors=True)
            raise
        self.logger.info("Reference voice created: %s", voice.voice_id)
        return voice

    def edit_voice(
        self,
        voice_id: str,
        *,
        name: str | None = None,
        language: str | None = None,
        category: str | None = None,
        voice_description: str | None = None,
        style_tags: list[str] | None = None,
        notes: str | None = None,
    ) -> VoiceProfile:
        voice = self.get(voice_id)
        if voice.is_builtin:
            raise VoiceServiceError("Built-in voices cannot be edited.")
        if name is not None:
            voice.name = name.strip()
        if language is not None:
            voice.language = language
        if category is not None:
            voice.category = category.strip()
        if voice_description is not None:
            voice.voice_description = voice_description.strip()
        if style_tags is not None:
            voice.style_tags = self._tags(style_tags)
        if notes is not None:
            voice.notes = notes.strip()
        self._validate_common(voice.name, voice.language, voice.category)
        if voice.type_code == VoiceType.DESIGNED.value:
            if not voice.voice_description:
                raise VoiceServiceError("Voice description is required.")
            if len(voice.voice_description) > MAX_VOICE_DESCRIPTION:
                raise VoiceServiceError(f"Keep voice descriptions under {MAX_VOICE_DESCRIPTION} characters.")
        voice.updated_at = utc_now_iso()
        return self.repository.update_profile(voice)

    def replace_reference(self, voice_id: str, source_audio: str | Path, consent_confirmed: bool) -> VoiceProfile:
        if not consent_confirmed:
            raise VoiceServiceError("Confirm that you have permission to use this voice recording.")
        voice = self.get(voice_id)
        if voice.is_builtin or voice.type_code != VoiceType.REFERENCE.value:
            raise VoiceServiceError("Choose one of your reference voices.")
        source = self._validate_reference(source_audio)
        folder = self._reference_folder(voice_id)
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"reference{source.suffix.lower()}"
        temp = folder / f".replacement-{uuid4().hex}{source.suffix.lower()}"
        old_path = Path(voice.reference_audio_path) if voice.reference_audio_path else None
        try:
            shutil.copy2(source, temp)
            self._validate_reference(temp)
            temp.replace(target)
            voice.reference_audio_path = str(target)
            voice.duration_ms = self._reference_duration_ms(target)
            voice.validated = True
            voice.updated_at = utc_now_iso()
            self.repository.update_profile(voice)
            if old_path and old_path != target and self._is_within(old_path, folder):
                old_path.unlink(missing_ok=True)
            return voice
        except Exception:
            temp.unlink(missing_ok=True)
            raise

    def duplicate_voice(self, voice_id: str) -> VoiceProfile:
        source = self.get(voice_id)
        if source.is_builtin:
            # Built-ins may be duplicated into an editable designed profile.
            return self.create_designed(
                f"{source.name} Copy", source.language, source.category, source.voice_description,
                source.style_tags, source.settings,
            )
        clone = VoiceProfile(
            name=f"{source.name} Copy", voice_type=source.type_code, language=source.language,
            category=source.category, engine_id=source.engine_id, voice_description=source.voice_description,
            style_tags=list(source.style_tags), description=source.description, settings=dict(source.settings),
            notes=source.notes, validated=source.validated, duration_ms=source.duration_ms,
        )
        if source.type_code == VoiceType.REFERENCE.value:
            src = Path(source.reference_audio_path)
            folder = self.reference_root / clone.voice_id
            target = folder / src.name
            try:
                folder.mkdir(parents=True, exist_ok=False)
                shutil.copy2(src, target)
                clone.reference_audio_path = str(target)
                self.repository.create_profile(clone)
            except Exception:
                shutil.rmtree(folder, ignore_errors=True)
                raise
        else:
            self.repository.create_profile(clone)
        return clone

    def delete_voice(self, voice_id: str, clear_assignments: bool = False) -> None:
        voice = self.get(voice_id)
        if voice.is_builtin:
            raise VoiceServiceError("Built-in voices cannot be deleted.")
        count = self.repository.assignment_count(voice_id)
        if count and not clear_assignments:
            raise VoiceInUseError(count)
        if count:
            self.repository.clear_assignments(voice_id)
        self.repository.delete_profile(voice_id)
        if voice.type_code == VoiceType.REFERENCE.value:
            folder = self._reference_folder(voice_id)
            if folder.exists() and self._is_within(folder, self.reference_root) and folder.resolve() != self.reference_root.resolve():
                shutil.rmtree(folder)
        self.logger.info("Voice deleted: %s", voice_id)

    def assign_project(self, project_id: str, voice_id: str) -> VoiceProfile:
        voice = self.get(voice_id)
        self.repository.set_project_default_voice(project_id, voice.voice_id)
        self.mark_used(voice.voice_id)
        return voice

    def assign_section(self, project_id: str, section_id: str, voice_id: str | None) -> VoiceProfile | None:
        voice = self.get(voice_id) if voice_id else None
        self.repository.set_section_voice_override(project_id, section_id, voice.voice_id if voice else None)
        if voice:
            self.mark_used(voice.voice_id)
        return voice

    def project_voice(self, project_id: str) -> VoiceProfile | None:
        voice_id = self.repository.get_project_default_voice(project_id)
        return self.get(voice_id) if voice_id else None

    def section_voice(self, section_id: str) -> VoiceProfile | None:
        voice_id = self.repository.get_section_voice_override(section_id)
        return self.get(voice_id) if voice_id else None

    def resolve_voice(self, project_id: str, section_id: str | None = None) -> VoiceProfile | None:
        if section_id:
            override = self.section_voice(section_id)
            if override is not None:
                return override
        return self.project_voice(project_id)

    def voice_config(
        self,
        voice_id: str,
        *,
        device: str = "auto",
        pace: str = "",
        energy: str = "",
        tone: str = "",
    ) -> VoiceConfig:
        voice = self.get(voice_id)
        settings = dict(voice.settings)
        description = voice.voice_description.strip()
        modifiers = [value.strip().lower() for value in (pace, energy, tone) if value and value.strip().lower() not in {"natural", "medium", "neutral"}]
        if modifiers and voice.type_code != VoiceType.REFERENCE.value:
            description = f"{description.rstrip('.')} with {', '.join(modifiers)} delivery."
        mode = "reference" if voice.type_code == VoiceType.REFERENCE.value else "designed"
        return VoiceConfig(
            mode=mode,
            description=description,
            reference_audio_path=voice.reference_audio_path,
            consent_confirmed=voice.type_code == VoiceType.REFERENCE.value,
            cfg_value=float(settings.get("cfg_value", 2.0)),
            inference_timesteps=int(settings.get("inference_timesteps", 10)),
            seed=settings.get("seed"),
            normalize_text=bool(settings.get("normalize_text", False)),
            device=device or str(settings.get("device", "auto")),
            metadata={"voice_id": voice.voice_id, "voice_name": voice.name, "voice_type": voice.type_code},
        )

    def duplicate_project_assignments(self, source_project_id: str, duplicate_project_id: str) -> None:
        self.repository.duplicate_project_assignments(source_project_id, duplicate_project_id)

    def preview_text(self, language: str) -> str:
        return DEFAULT_PREVIEW_TEXT.get(language, DEFAULT_PREVIEW_TEXT["en"])

    def preview_cache_key(self, voice_id: str, text: str, settings: dict, model_version: str = "") -> str:
        payload = json.dumps(
            {"voiceId": voice_id, "text": text, "settings": settings, "modelVersion": model_version},
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def assignment_count(self, voice_id: str) -> int:
        return self.repository.assignment_count(voice_id)

    def _validate_reference(self, path: str | Path) -> Path:
        candidate = Path(path).expanduser()
        if self.reference_validator is not None:
            return Path(self.reference_validator(candidate))
        if not candidate.is_file() or candidate.stat().st_size <= 0:
            raise VoiceServiceError("This recording could not be used as a reference voice.")
        if candidate.suffix.lower() not in {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".opus", ".aac"}:
            raise VoiceServiceError("This recording format is not supported yet.")
        return candidate

    @staticmethod
    def _reference_duration_ms(path: Path) -> int:
        if path.suffix.lower() != ".wav":
            return 0
        try:
            import wave
            with wave.open(str(path), "rb") as reader:
                rate = reader.getframerate()
                return int(reader.getnframes() / rate * 1000) if rate else 0
        except Exception:
            return 0

    @staticmethod
    def _validate_common(name: str, language: str, category: str) -> None:
        if not name.strip():
            raise VoiceServiceError("Voice name is required.")
        if language not in SUPPORTED_LANGUAGES:
            raise VoiceServiceError("Choose English or Khmer.")
        if not category.strip():
            raise VoiceServiceError("Voice category is required.")

    @staticmethod
    def _tags(values: list[str] | None) -> list[str]:
        result: list[str] = []
        for value in values or []:
            tag = str(value).strip()
            if tag and tag.casefold() not in {item.casefold() for item in result}:
                result.append(tag[:32])
            if len(result) >= 8:
                break
        return result

    @staticmethod
    def _safe_settings(settings: dict | None) -> dict:
        value = dict(settings or {})
        allowed = {"pace", "energy", "tone", "cfg_value", "inference_timesteps", "seed", "normalize_text", "device"}
        return {key: value[key] for key in value if key in allowed}

    def _reference_folder(self, voice_id: str) -> Path:
        folder = self.reference_root / voice_id
        if not self._is_within(folder, self.reference_root) or folder.resolve() == self.reference_root.resolve():
            raise VoiceServiceError("Reference voice storage path is unsafe.")
        return folder

    @staticmethod
    def _is_within(path: Path, root: Path) -> bool:
        try:
            path.resolve().relative_to(root.resolve())
            return True
        except ValueError:
            return False
