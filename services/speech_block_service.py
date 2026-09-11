from __future__ import annotations

from domain.phase22_errors import SpeechBlockInvalid
from domain.speech_block import SpeechBlock
from storage.repositories.phase22_repository import Phase22Repository


class SpeechBlockService:
    def __init__(self, repository: Phase22Repository, speakers, languages) -> None:
        self.repository = repository
        self.speakers = speakers
        self.languages = languages

    def for_section(self, project_id: str, section_id: str, *, migrate_legacy: bool = True) -> list[SpeechBlock]:
        return self.repository.ensure_legacy_block(project_id, section_id) if migrate_legacy else self.repository.blocks_for_section(section_id)

    def for_project(self, project_id: str) -> list[SpeechBlock]:
        return self.repository.blocks_for_project(project_id)

    def add(self, project_id: str, section_id: str, text: str = "", *, speaker_id: str = "", language: str = "en", source_type: str = "tts") -> SpeechBlock:
        self.languages.get(language)
        if speaker_id and self.repository.speaker(project_id, speaker_id) is None:
            raise SpeechBlockInvalid("Speaker not found.")
        items = self.repository.blocks_for_section(section_id)
        item = SpeechBlock(script_section_id=section_id, order=len(items), text=text, speaker_id=speaker_id, language=language, speech_source_type=source_type)
        return self.repository.save_block(project_id, item)

    def update(self, project_id: str, block_id: str, **updates) -> SpeechBlock:
        item = self.repository.block(project_id, block_id)
        if item is None:
            raise SpeechBlockInvalid("Speech block not found.")
        aliases = {
            "speakerId": "speaker_id", "voiceOverrideId": "voice_override_id", "sourceType": "speech_source_type",
            "pauseBeforeMs": "pause_before_ms", "pauseAfterMs": "pause_after_ms", "sceneId": "scene_id",
            "startOffsetMs": "start_offset_ms", "audioId": "audio_id",
        }
        allowed = {"speaker_id", "text", "language", "voice_override_id", "speech_source_type", "pause_before_ms", "pause_after_ms", "scene_id", "start_offset_ms", "audio_id", "metadata"}
        for key, value in updates.items():
            attr = aliases.get(key, key)
            if attr not in allowed:
                continue
            if attr == "language":
                self.languages.get(str(value))
            if attr == "speaker_id" and value and self.repository.speaker(project_id, str(value)) is None:
                raise SpeechBlockInvalid("Speaker not found.")
            setattr(item, attr, value)
        return self.repository.save_block(project_id, item)

    def move(self, project_id: str, block_id: str, new_index: int) -> list[SpeechBlock]:
        item = self.repository.block(project_id, block_id)
        if item is None:
            raise SpeechBlockInvalid("Speech block not found.")
        items = self.repository.blocks_for_section(item.script_section_id)
        old = next((i for i, value in enumerate(items) if value.id == block_id), -1)
        if old < 0:
            raise SpeechBlockInvalid("Speech block not found.")
        moving = items.pop(old); items.insert(max(0, min(int(new_index), len(items))), moving)
        with self.repository.database.connect() as c, c:
            for order, block in enumerate(items):
                c.execute("UPDATE speech_blocks SET block_order=? WHERE id=?", (order, block.id))
        return self.repository.blocks_for_section(item.script_section_id)

    def delete(self, project_id: str, block_id: str) -> None:
        item = self.repository.block(project_id, block_id)
        if item is None:
            raise SpeechBlockInvalid("Speech block not found.")
        section_id = item.script_section_id
        self.repository.delete_block(project_id, block_id)
        self.repository.normalize_block_order(project_id, section_id)

    def voice_resolution(self, project_id: str, block_id: str) -> dict[str, str]:
        item = self.repository.block(project_id, block_id)
        if item is None:
            raise SpeechBlockInvalid("Speech block not found.")
        voice, source = self.speakers.resolve_voice(project_id, item)
        return {"speakerId": item.speaker_id, "voiceId": voice.voice_id, "source": source, "language": item.language}
