from __future__ import annotations

"""Cross-cutting Manual Speech & TTS Editor layered on the Phase 31 runtime.

SpeechBlock remains canonical. GeneratedAudio remains take storage. Existing
Timeline, subtitles, Phase 21/22 TTS and Phase 30 mixer remain authoritative.
"""

import app.phase31_runtime as p31
from services.manual_speech_editor_service import ManualSpeechEditorService
from services.autosave_service import AutosaveService
from services.multispeaker_tts_service import MultiSpeakerTTSService
from services.speech_block_service import SpeechBlockService
from services.subtitle_service import SubtitleService
from services.timeline_service import TimelineService
from services.voice_service import VoiceService
from storage.repositories.generated_audio_repository import GeneratedAudioRepository
from storage.repositories.transcript_repository import TranscriptRepository
from storage.repositories.translation_repository import TranslationRepository
from ui.controllers.manual_speech_controller import ManualSpeechController
from workers.worker_pool import WorkerPool


def _install_manual_speech(container):
    blocks=container.resolve(SpeechBlockService)
    multispeaker=container.resolve(MultiSpeakerTTSService)
    audio=container.resolve(GeneratedAudioRepository)
    voices=container.resolve(VoiceService)
    subtitles=container.resolve(SubtitleService)
    transcripts=container.resolve(TranscriptRepository)
    translations=container.resolve(TranslationRepository)
    service=ManualSpeechEditorService(blocks,multispeaker,audio,voices,subtitle_service=subtitles,
                                      transcript_repository=transcripts,translation_repository=translations,
                                      logger=container.resolve("logger"))
    try:container.register_instance(ManualSpeechEditorService,service)
    except Exception:pass
    return service


def run()->int:
    try:
        from PySide6.QtQml import qmlRegisterSingletonType
    except ImportError:
        return p31.run()

    original_install=p31._install
    registered={"done":False}
    def install(container):
        result=original_install(container)
        service=_install_manual_speech(container)
        if not registered["done"]:
            workers=container.resolve(WorkerPool);timeline=container.resolve(TimelineService);logger=container.resolve("logger")
            class RuntimeManualSpeechController(ManualSpeechController):
                def __init__(self,parent=None):
                    super().__init__(service,workers,command_stack=timeline.edits.stack,autosave=container.resolve(AutosaveService),logger=logger,parent=parent)
            qmlRegisterSingletonType(RuntimeManualSpeechController,"SPVideoStudio.ManualSpeech",1,0,"ManualSpeech")
            registered["done"]=True
        return result
    p31._install=install
    try:return p31.run()
    finally:p31._install=original_install
