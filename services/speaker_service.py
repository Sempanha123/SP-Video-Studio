from __future__ import annotations

from domain.phase22_errors import SpeakerNotFound, VoiceLanguageMismatch
from domain.speaker_profile import SpeakerProfile
from domain.speech_block import SpeechBlock
from services.language_service import LanguageService
from storage.repositories.phase22_repository import Phase22Repository


class SpeakerService:
    def __init__(self, repository: Phase22Repository, project_repository, voice_service, languages: LanguageService) -> None:
        self.repository = repository
        self.projects = project_repository
        self.voices = voice_service
        self.languages = languages

    def list(self, project_id: str) -> list[SpeakerProfile]:
        self._project(project_id)
        return self.repository.speakers(project_id)

    def create(self, project_id: str, name: str, role: str = "speaker", *, language: str = "en", voice_id: str = "", description: str = "") -> SpeakerProfile:
        self._project(project_id)
        self.languages.get(language)
        if voice_id:
            self.voices.get(voice_id)
        item = SpeakerProfile(project_id=project_id, name=name.strip(), role=role, language=language, voice_id=voice_id, description=description.strip())
        return self.repository.save_speaker(item)

    def update(self, project_id: str, speaker_id: str, **updates) -> SpeakerProfile:
        item = self.repository.speaker(project_id, speaker_id)
        if item is None:
            raise SpeakerNotFound()
        aliases = {"voiceId": "voice_id", "avatarUrl": "avatar"}
        allowed = {"name", "role", "voice_id", "language", "description", "avatar", "metadata"}
        for key, value in updates.items():
            attr = aliases.get(key, key)
            if attr not in allowed:
                continue
            if attr == "language":
                self.languages.get(str(value))
            if attr == "voice_id" and value:
                self.voices.get(str(value))
            setattr(item, attr, value)
        return self.repository.save_speaker(item)

    def delete(self, project_id: str, speaker_id: str, *, replacement_speaker_id: str = "") -> None:
        item = self.repository.speaker(project_id, speaker_id)
        if item is None:
            raise SpeakerNotFound()
        usage = self.repository.speaker_usage_count(project_id, speaker_id)
        if usage and not replacement_speaker_id:
            raise SpeakerNotFound(f"This speaker is used by {usage} speech block(s). Choose a replacement first.")
        if replacement_speaker_id:
            replacement = self.repository.speaker(project_id, replacement_speaker_id)
            if replacement is None or replacement.id == speaker_id:
                raise SpeakerNotFound("Choose a valid replacement speaker.")
            with self.repository.database.connect() as c, c:
                c.execute("UPDATE speech_blocks SET speaker_id=? WHERE speaker_id=?", (replacement.id, speaker_id))
        self.repository.delete_speaker(project_id, speaker_id)

    def resolve_voice(self, project_id: str, block: SpeechBlock):
        voice = None
        source = ""
        if block.voice_override_id:
            voice = self.voices.get(block.voice_override_id)
            source = "block_override"
        elif block.speaker_id:
            speaker = self.repository.speaker(project_id, block.speaker_id)
            if speaker is None:
                raise SpeakerNotFound()
            if speaker.voice_id:
                voice = self.voices.get(speaker.voice_id)
                source = "speaker"
        if voice is None:
            voice = self.voices.project_voice(project_id)
            source = "project_default" if voice is not None else ""
        if voice is None:
            raise VoiceLanguageMismatch("Choose a voice for this speech block.")
        engine_id = str(getattr(voice, "engine_id", "voxcpm2") or "voxcpm2")
        if not self.languages.supports_tts(block.language, engine_id):
            label = self.languages.get(block.language).display_name
            raise VoiceLanguageMismatch(f"The selected voice engine does not support {label}.")
        return voice, source

    def _project(self, project_id: str):
        item = self.projects.get_by_id(project_id)
        if item is None:
            raise KeyError("Project not found.")
        return item
