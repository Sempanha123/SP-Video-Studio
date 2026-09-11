from __future__ import annotations

"""Phase 21 runtime extension.

Keeps app.bootstrap authoritative while registering the Translate & Dub singleton and
services without duplicating the existing application bootstrap/renderer architecture.
"""

from pathlib import Path

from app import bootstrap
from app.paths import AppPaths
from media.ffmpeg_locator import FFmpegLocator
from services.dubbing_alignment_service import DubbingAlignmentService
from services.dubbing_apply_service import DubbingApplyService
from services.dubbing_audio_service import DubbingAudioService
from services.dubbing_service import DubbingService
from services.dubbing_validation_service import DubbingValidationService
from services.settings_service import SettingsService
from services.render_service import RenderService
from services.subtitle_service import SubtitleService
from services.timeline_service import TimelineService
from services.tts_service import TTSService
from services.voice_service import VoiceService
from storage.database import SQLiteDatabase
from storage.repositories.dubbing_repository import DubbingRepository
from storage.repositories.generated_audio_repository import GeneratedAudioRepository
from storage.repositories.media_repository import MediaRepository
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.transcript_repository import TranscriptRepository
from storage.repositories.translation_repository import TranslationRepository
from ui.controllers.dubbing_controller import DubbingController
from workers.worker_pool import WorkerPool


def _extend_container(container):
    database=container.resolve(SQLiteDatabase)
    repository=DubbingRepository(database)
    alignment=DubbingAlignmentService()
    settings_service=container.resolve(SettingsService)
    locator=container.resolve(FFmpegLocator)

    def ffmpeg_path() -> str | None:
        settings=settings_service.current
        custom=settings.ffmpeg_path if settings.ffmpeg_mode == "custom" else None
        info,_=locator.discover(custom, custom)
        return info.path if info.available else None

    audio=DubbingAudioService(ffmpeg_path,alignment)
    service=DubbingService(
        repository,
        container.resolve(ProjectRepository),
        container.resolve(TranslationRepository),
        container.resolve(GeneratedAudioRepository),
        container.resolve(VoiceService),
        container.resolve(TTSService),
        alignment,
        audio,
        container.resolve("logger"),
        media_repository=container.resolve(MediaRepository),
    )
    apply_service=DubbingApplyService(repository,container.resolve(SubtitleService),container.resolve(TimelineService))
    validation=DubbingValidationService(alignment)
    # Existing RenderService remains authoritative. Inject only the generic audio/subtitle override
    # for projects that already have a ready Phase 21 final mix.
    render_service=container.resolve(RenderService)
    original_build_plan=render_service.build_plan
    def build_plan_with_dub(project_id,settings,*,preset_id="custom",job_id=""):
        output=repository.latest_output(project_id,"final_mix")
        if output is not None and output.status_code == "ready" and Path(output.file_path).is_file():
            apply_service.apply_render_settings(project_id,settings)
        return original_build_plan(project_id,settings,preset_id=preset_id,job_id=job_id)
    render_service.build_plan=build_plan_with_dub
    container.register_instance(DubbingRepository,repository)
    container.register_instance(DubbingAlignmentService,alignment)
    container.register_instance(DubbingAudioService,audio)
    container.register_instance(DubbingService,service)
    container.register_instance(DubbingApplyService,apply_service)
    container.register_instance(DubbingValidationService,validation)
    return service,apply_service,validation


def run() -> int:
    """Start the existing application with Phase 21 services/QML singleton registered."""
    try:
        from PySide6.QtQml import qmlRegisterSingletonType
    except ImportError:
        return bootstrap.run()

    container=bootstrap.build_container()
    service,apply_service,validation=_extend_container(container)
    transcript_repository=container.resolve(TranscriptRepository)
    media_repository=container.resolve(MediaRepository)
    worker_pool=container.resolve(WorkerPool)
    logger=container.resolve("logger")

    class RuntimeDubbingController(DubbingController):
        def __init__(self, parent=None):
            super().__init__(
                service,validation,worker_pool,apply_service,
                transcript_repository=transcript_repository,
                media_repository=media_repository,
                logger=logger,parent=parent,
            )

    qmlRegisterSingletonType(RuntimeDubbingController,"SPVideoStudio.Phase21",1,0,"Dubbing")
    original=bootstrap.build_container
    bootstrap.build_container=lambda: container
    try:
        return bootstrap.run()
    finally:
        bootstrap.build_container=original
