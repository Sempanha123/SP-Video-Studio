from __future__ import annotations

"""Phase 30 professional audio mixer layered on Phase 29.

This runtime extends the existing Timeline/Render/Template/Batch architecture. It
never creates an AudioProject, a separate audio timeline, or a second renderer.
"""
from pathlib import Path

import app.phase29_runtime as p29
from app.paths import AppPaths
from domain.audio_errors import AudioMixFailed
from services.audio_analysis_service import AudioAnalysisService
from services.audio_ducking_service import AudioDuckingService
from services.audio_mixer_service import AudioMixerService
from services.audio_render_service import AudioRenderService
from services.audio_validation_service import AudioValidationService
from services.audio_waveform_service import AudioWaveformService
from storage.repositories.audio_mix_repository import AudioMixRepository
from ui.controllers.audio_mixer_controller import AudioMixerController


def _resolve_optional(container, cls):
    try:
        return container.resolve(cls)
    except Exception:
        return None


class _ProviderRunner:
    """Lazy adapter around the app's existing FFmpeg provider/FFmpegRunner."""
    def __init__(self, provider, ffmpeg_runner_cls):
        self.provider = provider
        self.runner_cls = ffmpeg_runner_cls

    def run(self, args, **kwargs):
        path = self.provider()
        if not path:
            raise AudioMixFailed("FFmpeg is required for project audio mixing.")
        return self.runner_cls(path).run(args, **kwargs)


def _template_audio_settings(item):
    metadata = dict(getattr(item, "metadata", {}) or {})
    for key in ("audioMixer", "audioMix", "mixer"):
        value = metadata.get(key)
        if isinstance(value, dict):
            return value
    for component in list(getattr(item, "components", []) or []):
        data = dict(getattr(component, "data", {}) or {})
        for key in ("audioMixer", "audioMix", "mixer"):
            value = data.get(key)
            if isinstance(value, dict):
                return value
    return None


def _install_command_bridge(mixer, timeline_service):
    edits = getattr(timeline_service, "edits", None)
    stack = getattr(edits, "stack", None)
    if stack is None:
        return None
    try:
        from commands.timeline.commands import TimelineCommand
    except Exception:
        return None

    replaying = {"value": False}

    def sink(name, before, after):
        if replaying["value"]:
            return
        def restore(payload):
            replaying["value"] = True
            try:
                mixer.restore_command_state(name, payload)
            finally:
                replaying["value"] = False
        label = {
            "track": "Audio Track Settings",
            "track_add": "Add Audio Track",
            "clip_mix": "Audio Clip Settings",
            "master_gain": "Master Gain",
            "ducking": "Audio Ducking",
            "preset": "Audio Mixer Preset",
        }.get(name, "Audio Mixer Edit")
        stack.push_executed(TimelineCommand(label, lambda: restore(after), lambda: restore(before)))
    mixer.command_sink = sink
    return sink


def _extend_phase30(container, cache, *, template_apply=None):
    p27 = p29.p27; p26 = p27.p26; p25 = p26.p25; p24 = p25.p24
    db = container.resolve(p24.SQLiteDatabase)
    logger = container.resolve("logger")
    repository = AudioMixRepository(db)
    timeline_service = container.resolve(p24.TimelineService)
    media_repository = container.resolve(p24.MediaRepository)
    scene_repository = container.resolve(p24.SceneRepository)
    dubbing_repository = container.resolve(p24.DubbingRepository)
    try:
        from storage.repositories.generated_audio_repository import GeneratedAudioRepository
        generated_audio_repository = container.resolve(GeneratedAudioRepository)
    except Exception:
        generated_audio_repository = None

    render_service = container.resolve(p24.RenderService)
    ffmpeg_provider = render_service.ffmpeg_provider
    lazy_runner = _ProviderRunner(ffmpeg_provider, p24.FFmpegRunner)
    ducking = AudioDuckingService()
    analysis = AudioAnalysisService(ffmpeg_provider, cache, logger)
    waveforms = AudioWaveformService(cache, ffmpeg_provider, logger)
    audio_render = AudioRenderService(lazy_runner, cache_service=cache, logger=logger)
    validation = AudioValidationService()
    mixer = AudioMixerService(
        repository,
        phase22_repository=_resolve_optional(container, p24.Phase22Repository),
        dubbing_repository=dubbing_repository,
        cache_service=cache,
        timeline_service=timeline_service,
        media_repository=media_repository,
        generated_audio_repository=generated_audio_repository,
        scene_repository=scene_repository,
        logger=logger,
    )
    _install_command_bridge(mixer, timeline_service)

    for cls, obj in (
        (AudioMixRepository, repository),
        (AudioDuckingService, ducking),
        (AudioAnalysisService, analysis),
        (AudioWaveformService, waveforms),
        (AudioRenderService, audio_render),
        (AudioValidationService, validation),
        (AudioMixerService, mixer),
    ):
        container.register_instance(cls, obj)

    # Final renders keep using the existing RenderService/FFmpegRenderer. The
    # only extension is an AudioMixSpec snapshot on the existing RenderPlan.
    previous_build_plan = render_service.build_plan
    if not getattr(previous_build_plan, "_phase30_audio_mix", False):
        def build_plan_with_audio_mix(project_id, settings, *, preset_id="custom", job_id=""):
            plan = previous_build_plan(project_id, settings, preset_id=preset_id, job_id=job_id)
            try:
                spec = mixer.build_project_mix_spec(project_id, int(plan.expected_duration_ms))
                if spec.get("clips"):
                    plan.audio_mix_spec = spec
                    plan.settings.metadata["audioMixSpec"] = spec
            except Exception:
                if logger:
                    logger.warning("Phase 30 mixer could not be attached; legacy audio path remains active", exc_info=True)
            return plan
        build_plan_with_audio_mix._phase30_audio_mix = True
        render_service.build_plan = build_plan_with_audio_mix

    # Project duplication copies mixer metadata; source audio files remain under
    # the existing project/media/take ownership rules.
    project_service = container.resolve(p24.ProjectService)
    previous_duplicate = project_service.duplicate_project
    if not getattr(previous_duplicate, "_phase30_audio_mix", False):
        def duplicate_with_audio_mix(project_id, *args, **kwargs):
            duplicate = previous_duplicate(project_id, *args, **kwargs)
            target_id = str(getattr(duplicate, "project_id", "") or getattr(duplicate, "id", "") or "")
            if target_id:
                try:
                    mixer.duplicate_project(str(project_id), target_id)
                except Exception:
                    if logger:
                        logger.warning("Mixer metadata duplication was skipped", exc_info=True)
            return duplicate
        duplicate_with_audio_mix._phase30_audio_mix = True
        project_service.duplicate_project = duplicate_with_audio_mix

    # Phase 24 Templates and therefore Phase 26 Batch can carry ID-free mixer
    # presets. They are applied after normal template components succeed.
    if template_apply is not None:
        previous_apply = template_apply.apply_to_project
        if not getattr(previous_apply, "_phase30_audio_mix", False):
            def apply_with_audio_mix(item, project_id, *args, **kwargs):
                result = previous_apply(item, project_id, *args, **kwargs)
                data = _template_audio_settings(item)
                if data:
                    mixer.apply_template_settings(project_id, data)
                    try:
                        result.recommendations["audioMixer"] = mixer.template_settings(project_id)
                    except Exception:
                        pass
                return result
            apply_with_audio_mix._phase30_audio_mix = True
            template_apply.apply_to_project = apply_with_audio_mix

    return repository, mixer, ducking, analysis, waveforms, audio_render, validation


def run() -> int:
    p27 = p29.p27; p26 = p27.p26; p25 = p26.p25; p24 = p25.p24
    try:
        from PySide6.QtQml import qmlRegisterSingletonType
    except ImportError:
        return p24.bootstrap.run()

    container = p24.bootstrap.build_container()
    dub_service, dub_apply, dub_validation = p24.extend_phase21(container)
    phase22_repository, languages, visual, speakers, blocks, universal = p24._extend_phase22(container)
    short_repository, candidates, reframe, captions, shorts = p24._extend_phase23(container)
    template_repository, templates, template_apply = p24._extend_phase24(container, phase22_repository, languages, visual, speakers, short_repository)
    asset_repository, assets, asset_usage, asset_project = p25._extend_phase25(container)
    batch_repository, item_repository, imports, batch_service, execution, scheduler = p26._extend_phase26(container, templates, template_apply, asset_repository, languages)
    autosave, recovery, snapshots, shutdown = p27._extend_phase27(container)
    cache, usage, cleanup, migration, disk, stale = p29._extend_phase29(container, asset_repository=asset_repository, scheduler=scheduler, recovery=recovery)
    audio_repository, mixer, ducking, analysis, waveforms, audio_render, audio_validation = _extend_phase30(container, cache, template_apply=template_apply)

    worker_pool = container.resolve(p24.WorkerPool); logger = container.resolve("logger")
    transcript_repository = container.resolve(p24.TranscriptRepository); media_repository = container.resolve(p24.MediaRepository)
    scene_repository = container.resolve(p24.SceneRepository); project_repository = container.resolve(p24.ProjectRepository)

    class RuntimeDubbingController(p24.DubbingController):
        def __init__(self, parent=None):
            super().__init__(dub_service, dub_validation, worker_pool, dub_apply, transcript_repository=transcript_repository, media_repository=media_repository, logger=logger, parent=parent)
    class RuntimeLanguageController(p24.LanguageController):
        def __init__(self, parent=None): super().__init__(languages, parent)
    class RuntimeVideoStudioController(p24.VideoStudioController):
        def __init__(self, parent=None): super().__init__(universal, visual, speakers, blocks, phase22_repository, media_repository, container.resolve(p24.SceneService), languages, parent, logger)
    class RuntimeWordTimingController(p24.WordTimingController):
        def __init__(self, parent=None): super().__init__(container.resolve(p24.WordTimingService), parent, logger)
    class RuntimeShortsController(p24.ShortsController):
        def __init__(self, parent=None): super().__init__(shorts, candidates, captions, reframe, short_repository, media_repository, transcript_repository, scene_repository, project_repository, languages, logger, parent)
    class RuntimeTemplateController(p24.TemplateController):
        def __init__(self, parent=None): super().__init__(templates, template_apply, logger, parent)
    class RuntimeAssetController(p25.AssetLibraryController):
        def __init__(self, parent=None): super().__init__(assets, asset_repository, asset_usage, asset_project, importer=container.resolve(p25.AssetImportService), relink=container.resolve(p25.AssetRelinkService), logger=logger, parent=parent)
    class RuntimeBatchController(p26.BatchController):
        def __init__(self, parent=None): super().__init__(batch_service, imports, batch_repository, item_repository, templates, scheduler, logger=logger, parent=parent)
    class RuntimeRecoveryController(p27.RecoveryController):
        def __init__(self, parent=None): super().__init__(autosave, recovery, snapshots, shutdown, logger, parent)
    class RuntimeStorageController(p29.StorageController):
        def __init__(self, parent=None): super().__init__(usage, cleanup, cache, migration, disk, stale, worker_pool=worker_pool, logger=logger, parent=parent)
    class RuntimeAudioMixerController(AudioMixerController):
        def __init__(self, parent=None): super().__init__(mixer, waveforms, analysis, audio_render, audio_validation, worker_pool=worker_pool, logger=logger, parent=parent)

    registrations = (
        (RuntimeDubbingController, "SPVideoStudio.Phase21", "Dubbing"),
        (RuntimeLanguageController, "SPVideoStudio.Phase22", "LanguageCatalog"),
        (RuntimeVideoStudioController, "SPVideoStudio.Phase22", "VideoStudio"),
        (RuntimeWordTimingController, "SPVideoStudio.Phase22", "WordTiming"),
        (RuntimeShortsController, "SPVideoStudio.Phase23", "Shorts"),
        (RuntimeTemplateController, "SPVideoStudio.Phase24", "Templates"),
        (RuntimeAssetController, "SPVideoStudio.Phase25", "AssetLibrary"),
        (RuntimeBatchController, "SPVideoStudio.Phase26", "BatchFactoryController"),
        (RuntimeRecoveryController, "SPVideoStudio.Phase27", "Recovery"),
        (RuntimeStorageController, "SPVideoStudio.Phase29", "Storage"),
        (RuntimeAudioMixerController, "SPVideoStudio.Phase30", "AudioMixer"),
    )
    for cls, module, name in registrations:
        qmlRegisterSingletonType(cls, module, 1, 0, name)

    originals = p27._install_controller_bridges(p24.bootstrap, autosave)
    engine_patch = p27._install_recovery_overlay_engine(logger)
    original_build = p24.bootstrap.build_container; p24.bootstrap.build_container = lambda: container
    try:
        return p24.bootstrap.run()
    finally:
        p24.bootstrap.build_container = original_build
        for name, cls in originals.items():
            setattr(p24.bootstrap, name, cls)
        if engine_patch:
            engine_patch[0].QQmlApplicationEngine = engine_patch[1]
