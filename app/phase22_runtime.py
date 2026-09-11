from __future__ import annotations

"""Phase 22 runtime extension layered on the existing authoritative bootstrap/renderer."""

from dataclasses import replace

from app import bootstrap
from app.phase21_runtime import _extend_container as extend_phase21
from engines.stt.faster_whisper_engine import FasterWhisperEngine
from engines.stt.errors import STTInvalidRequest
from engines.stt.manager import STTEngineManager
from engines.translation.manager import TranslationEngineManager
from engines.translation.manual_engine import ManualTranslationEngine
from engines.tts.manager import TTSEngineManager
from engines.tts.voxcpm2_engine import VoxCPM2Engine
from rendering.layer_compositor import build_layered_scene_command
from rendering.scene_renderer import SceneRenderer
from services.composition_service import CompositionService
from services.frame_time_service import FrameTimeService
from services.language_service import LanguageService, VOXCPM2_LANGUAGE_CODES
from services.multispeaker_tts_service import MultiSpeakerTTSService
from services.scene_service import SceneService
from services.speaker_service import SpeakerService
from services.speech_block_service import SpeechBlockService
from services.timeline_mapping_service import TimelineMappingService
from services.tts_service import TTSService
from services.universal_video_service import UniversalVideoService
from services.visual_layer_service import VisualLayerService
from services.voice_service import VoiceService
from services.word_timing_service import WordTimingService
from services.model_service import ModelService
from services.render_service import RenderService
from services.project_service import ProjectService
from storage.database import SQLiteDatabase
from storage.repositories.generated_audio_repository import GeneratedAudioRepository
from storage.repositories.media_repository import MediaRepository
from storage.repositories.phase22_repository import Phase22Repository
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.scene_repository import SceneRepository
from storage.repositories.subtitle_repository import SubtitleRepository
from storage.repositories.transcript_repository import TranscriptRepository
from ui.controllers.dubbing_controller import DubbingController
from ui.controllers.language_controller import LanguageController
from ui.controllers.video_studio_controller import VideoStudioController
from ui.controllers.word_timing_controller import WordTimingController
from services.dubbing_service import DubbingService
from services.dubbing_apply_service import DubbingApplyService
from services.dubbing_validation_service import DubbingValidationService
from workers.worker_pool import WorkerPool


def _patch_engine_language_capabilities(languages: LanguageService) -> None:
    if not getattr(VoxCPM2Engine, "_phase22_language_patch", False):
        original_caps=VoxCPM2Engine.get_capabilities
        def phase22_caps(self):
            caps=original_caps(self)
            return replace(caps,supported_languages=tuple(sorted(VOXCPM2_LANGUAGE_CODES)))
        VoxCPM2Engine.get_capabilities=phase22_caps
        VoxCPM2Engine._phase22_language_patch=True
    if not getattr(FasterWhisperEngine, "_phase22_language_patch", False):
        original_validate=FasterWhisperEngine.validate_request
        def phase22_validate(self, request):
            language=request.language
            if language in {"auto","en","km"}:
                return original_validate(self,request)
            if language not in languages.stt_languages():
                raise STTInvalidRequest(f"The selected faster-whisper installation does not support language: {language}")
            request.language="auto"
            try: original_validate(self,request)
            finally: request.language=language
        FasterWhisperEngine.validate_request=phase22_validate
        FasterWhisperEngine._phase22_language_patch=True


def _patch_manual_translation(languages: LanguageService) -> None:
    if getattr(ManualTranslationEngine,"_phase22_language_patch",False): return
    def pairs(self):
        codes=languages.app_languages(); return tuple((a,b) for a in codes for b in codes if a!=b)
    def supports(self,source,target): return source in languages.app_languages() and target in languages.app_languages() and source!=target
    ManualTranslationEngine.get_supported_language_pairs=pairs
    ManualTranslationEngine.supports_language_pair=supports
    ManualTranslationEngine._phase22_language_patch=True


def _patch_layer_renderer() -> None:
    if getattr(SceneRenderer,"_phase22_layer_patch",False): return
    original=SceneRenderer.build_command
    def phase22_build(self,spec,settings,destination,*,temp_dir):
        def fallback(inner_spec,inner_settings,inner_destination,*,temp_dir):
            return original(self,inner_spec,inner_settings,inner_destination,temp_dir=temp_dir)
        return build_layered_scene_command(self,fallback,spec,settings,destination,temp_dir=temp_dir)
    SceneRenderer.build_command=phase22_build
    SceneRenderer._phase22_layer_patch=True


def _extend_phase22(container):
    db=container.resolve(SQLiteDatabase); repository=Phase22Repository(db)
    media=container.resolve(MediaRepository); scenes_repo=container.resolve(SceneRepository); scenes=container.resolve(SceneService)
    mapping=container.resolve(TimelineMappingService); mapping.phase22=repository
    languages=LanguageService(stt_manager=container.resolve(STTEngineManager),tts_manager=container.resolve(TTSEngineManager),translation_manager=container.resolve(TranslationEngineManager),model_service=container.resolve(ModelService))
    _patch_engine_language_capabilities(languages); _patch_manual_translation(languages); _patch_layer_renderer()
    visual=VisualLayerService(scenes_repo,media); speakers=SpeakerService(repository,container.resolve(ProjectRepository),container.resolve(VoiceService),languages)
    blocks=SpeechBlockService(repository,speakers,languages); frame=FrameTimeService(); words=WordTimingService(container.resolve(TranscriptRepository),frame,container.resolve(SubtitleRepository))
    multispeaker=MultiSpeakerTTSService(repository,speakers,container.resolve(VoiceService),container.resolve(TTSService),container.resolve(GeneratedAudioRepository),container.resolve(ProjectRepository))
    universal=UniversalVideoService(scenes,media,repository,visual,mapping); composition=CompositionService(scenes,media,repository)

    render=container.resolve(RenderService); previous_build=render.build_plan
    def phase22_plan(project_id,settings,*,preset_id="custom",job_id=""):
        plan=previous_build(project_id,settings,preset_id=preset_id,job_id=job_id)
        plan.scenes=[composition.enrich_spec(project_id,dict(spec)) for spec in plan.scenes]
        plan.metadata["phase22Composition"]=True
        return plan
    render.build_plan=phase22_plan

    # Existing ProjectService remains authoritative; append Phase22 project-owned records after its ID-safe duplication.
    project_service=container.resolve(ProjectService)
    if not getattr(project_service,"_phase22_duplicate_patch",False):
        original_duplicate=project_service.duplicate_project
        def duplicate_with_phase22(project_id):
            duplicate=original_duplicate(project_id)
            src_media=media.list_by_project(project_id); dst_media=media.list_by_project(duplicate.project_id)
            target_media={(x.name,x.original_path,x.type,int(x.file_size)):x.id for x in dst_media}
            media_map={x.id:target_media.get((x.name,x.original_path,x.type,int(x.file_size)),"") for x in src_media}
            src_scenes=scenes_repo.list_for_project(project_id); dst_scenes=scenes_repo.list_for_project(duplicate.project_id); by_order={x.order:x.id for x in dst_scenes}; scene_map={x.id:by_order.get(x.order,"") for x in src_scenes}
            repository.duplicate_project(project_id,duplicate.project_id,media_map=media_map,scene_map=scene_map); return duplicate
        project_service.duplicate_project=duplicate_with_phase22
        project_service._phase22_duplicate_patch=True
    for cls,obj in ((Phase22Repository,repository),(LanguageService,languages),(VisualLayerService,visual),(SpeakerService,speakers),(SpeechBlockService,blocks),(FrameTimeService,frame),(WordTimingService,words),(MultiSpeakerTTSService,multispeaker),(UniversalVideoService,universal),(CompositionService,composition)):
        container.register_instance(cls,obj)
    return repository,languages,visual,speakers,blocks,universal


def run() -> int:
    try:
        from PySide6.QtQml import qmlRegisterSingletonType
    except ImportError:
        return bootstrap.run()
    container=bootstrap.build_container()
    dub_service,dub_apply,dub_validation=extend_phase21(container)
    repository,languages,visual,speakers,blocks,universal=_extend_phase22(container)
    worker_pool=container.resolve(WorkerPool); logger=container.resolve("logger")
    transcript_repository=container.resolve(TranscriptRepository); media_repository=container.resolve(MediaRepository)

    class RuntimeDubbingController(DubbingController):
        def __init__(self,parent=None):
            super().__init__(dub_service,dub_validation,worker_pool,dub_apply,transcript_repository=transcript_repository,media_repository=media_repository,logger=logger,parent=parent)
    class RuntimeLanguageController(LanguageController):
        def __init__(self,parent=None): super().__init__(languages,parent)
    class RuntimeVideoStudioController(VideoStudioController):
        def __init__(self,parent=None):
            super().__init__(universal,visual,speakers,blocks,repository,media_repository,container.resolve(SceneService),languages,parent,logger)
    class RuntimeWordTimingController(WordTimingController):
        def __init__(self,parent=None): super().__init__(container.resolve(WordTimingService),parent,logger)

    qmlRegisterSingletonType(RuntimeDubbingController,"SPVideoStudio.Phase21",1,0,"Dubbing")
    qmlRegisterSingletonType(RuntimeLanguageController,"SPVideoStudio.Phase22",1,0,"LanguageCatalog")
    qmlRegisterSingletonType(RuntimeVideoStudioController,"SPVideoStudio.Phase22",1,0,"VideoStudio")
    qmlRegisterSingletonType(RuntimeWordTimingController,"SPVideoStudio.Phase22",1,0,"WordTiming")
    original=bootstrap.build_container; bootstrap.build_container=lambda:container
    try:return bootstrap.run()
    finally:bootstrap.build_container=original
