from __future__ import annotations

"""Phase 26 Batch Factory runtime extension layered on Phase 25.

Batch Factory only orchestrates the existing project/template/language/voice/TTS/
translation/subtitle/render/export services. It does not own a renderer, TTS engine,
or template engine.
"""

from pathlib import Path
from typing import Any

import app.phase25_runtime as p25
from domain.batch_stage import BatchStage
from domain.template import Template
from domain.template_placeholder import TemplatePlaceholderType
from services.batch_asset_service import BatchAssetService
from services.batch_execution_service import BatchExecutionService
from services.batch_import_service import BatchImportService
from services.batch_mapping_service import BatchMappingService
from services.batch_recovery_service import BatchRecoveryService
from services.batch_service import BatchService
from services.batch_validation_service import BatchValidationService
from services.batch_variant_service import BatchVariantService
from storage.database import SQLiteDatabase
from storage.repositories.batch_item_repository import BatchItemRepository
from storage.repositories.batch_repository import BatchRepository
from ui.controllers.batch_controller import BatchController
from workers.batch_scheduler import BatchScheduler
from workers.batch_worker import BatchWorker


def _resolve_optional(container, service_type):
    try:
        return container.resolve(service_type)
    except Exception:
        return None


def _platform_preset(value: str) -> str:
    key = str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")
    aliases = {
        "tiktok": "tiktok",
        "youtube_shorts": "youtube_shorts",
        "shorts": "youtube_shorts",
        "instagram_reels": "instagram_reels",
        "reels": "instagram_reels",
        "facebook_vertical": "facebook_vertical",
        "facebook_square": "facebook_square",
        "facebook_landscape": "facebook_landscape",
        "generic_vertical": "generic_vertical",
        "generic_square": "generic_square",
        "generic_landscape": "generic_landscape",
        "youtube": "youtube",
    }
    return aliases.get(key, key)


def _extend_phase26(container, templates, template_apply, asset_repository, languages):
    # Imported here so Phase 26 stays layered and startup only requires services
    # already present in the complete application runtime.
    from services.export_service import ExportService
    from services.language_service import LanguageService
    from services.narration_service import NarrationService
    from services.project_service import ProjectService
    from services.script_service import ScriptService
    from services.speaker_service import SpeakerService
    from services.speech_block_service import SpeechBlockService
    from services.subtitle_service import SubtitleService
    from services.translation_service import TranslationService
    from services.voice_service import VoiceService
    from services.multispeaker_tts_service import MultiSpeakerTTSService
    from storage.repositories.project_repository import ProjectRepository
    from workers.worker_pool import WorkerPool

    db = container.resolve(SQLiteDatabase)
    logger = container.resolve("logger")
    batch_repository = BatchRepository(db)
    item_repository = BatchItemRepository(db)
    importer = BatchImportService()
    mapping = BatchMappingService()
    variants = BatchVariantService()
    assets = BatchAssetService(asset_repository)

    voice_service = _resolve_optional(container, VoiceService)

    def voice_resolver(voice_id: str, language: str, role: str = "") -> dict[str, Any]:
        if voice_service is None:
            return {"available": False, "reason": "Voice service is unavailable."}
        try:
            voice = voice_service.get(str(voice_id))
            engine = str(getattr(voice, "engine_id", "voxcpm2") or "voxcpm2")
            return {
                "available": bool(languages.supports_tts(language, engine)),
                "voiceId": str(getattr(voice, "voice_id", voice_id)),
                "engine": engine,
                "role": role,
            }
        except Exception as exc:
            return {"available": False, "reason": str(exc)}

    validation = BatchValidationService(
        mapping,
        variants,
        language_service=languages,
        asset_service=assets,
        voice_resolver=voice_resolver,
    )
    project_service = container.resolve(ProjectService)
    service = BatchService(
        batch_repository,
        item_repository,
        importer,
        mapping,
        variants,
        validation,
        project_service=project_service,
        logger=logger,
    )
    recovery = BatchRecoveryService(batch_repository, item_repository, logger=logger)
    execution = BatchExecutionService(batch_repository, item_repository, logger=logger)

    script_service = _resolve_optional(container, ScriptService)
    translation_service = _resolve_optional(container, TranslationService)
    narration_service = _resolve_optional(container, NarrationService)
    multi_tts = _resolve_optional(container, MultiSpeakerTTSService)
    subtitle_service = _resolve_optional(container, SubtitleService)
    speaker_service = _resolve_optional(container, SpeakerService)
    speech_blocks = _resolve_optional(container, SpeechBlockService)
    export_service = _resolve_optional(container, ExportService)
    projects = container.resolve(ProjectRepository)

    media_placeholder_types = {
        TemplatePlaceholderType.MEDIA.value,
        TemplatePlaceholderType.VIDEO.value,
        TemplatePlaceholderType.IMAGE.value,
        TemplatePlaceholderType.AUDIO.value,
        TemplatePlaceholderType.LOGO.value,
    }

    def create_project(batch, item, *, cancellation=None, progress=None):
        if item.project_id:
            existing = projects.get_by_id(item.project_id)
            if existing is not None:
                return {"project_id": existing.project_id, "output_reference": existing.project_id}
        template = Template.from_dict(batch.template_snapshot, builtin=bool(batch.template_snapshot.get("builtin", False)))
        resolutions = dict(item.resolved_data)
        # Phase 25's TemplateApply patch expects explicit global-asset values in
        # the same Phase 24 resolution map. Keep placeholder syntax unchanged.
        for ph in template.placeholders:
            if ph.type_code in media_placeholder_types:
                value = resolutions.get(ph.id)
                if value and not (isinstance(value, str) and value.startswith("asset:")):
                    if asset_repository.get(str(value)) is not None:
                        resolutions[ph.id] = f"asset:{value}"
        language = str(resolutions.get("language") or item.metadata.get("variant", {}).get("language") or "en")
        aspect = str(resolutions.get("aspect_ratio") or item.metadata.get("variant", {}).get("aspect_ratio") or "")
        if not aspect:
            supported = list(getattr(template, "supported_aspect_ratios", ()) or ())
            aspect = supported[0] if supported else "9:16"
        label_bits = [str(item.row_index + 1).zfill(4), language]
        platform = str(item.metadata.get("variant", {}).get("platform") or resolutions.get("platform") or "")
        if platform:
            label_bits.append(platform)
        title = f"{batch.name} · {' · '.join(label_bits)}"
        if progress:
            progress(0.15, "Creating derived project")
        result = template_apply.create_project_from_template(
            template,
            title,
            language,
            aspect,
            resolutions=resolutions,
            allow_unresolved=False,
        )
        if progress:
            progress(1.0, "Project created")
        return {
            "project_id": result.project_id,
            "output_reference": result.project_id,
            "metadata": {
                "batchGeneratedProject": True,
                "templateApplyMapping": dict(result.mapping),
                "templateRecommendations": dict(result.recommendations),
            },
        }

    def prepare_script(batch, item, *, cancellation=None, progress=None):
        if script_service is None:
            raise RuntimeError("Existing ScriptService is unavailable.")
        script, sections = script_service.load_or_create(item.project_id)
        resolved = item.resolved_data
        source_language = str(resolved.get("source_language") or resolved.get("language") or script.language)
        script.language = source_language
        script_service.save_script(script)
        hook_text = str(resolved.get("headline") or resolved.get("hook") or "")
        body_text = str(resolved.get("script") or resolved.get("body") or resolved.get("text") or "")
        hook = next((s for s in sections if str(getattr(s, "type", "")) == "hook"), sections[0] if sections else None)
        body = next((s for s in sections if str(getattr(s, "type", "")) == "body"), sections[1] if len(sections) > 1 else (sections[0] if sections else None))
        if hook is not None and hook_text:
            hook.content = hook_text
            script_service.save_section(item.project_id, hook)
        if body is not None and body_text:
            body.content = body_text
            script_service.save_section(item.project_id, body)

        # Reuse Phase 22 SpeechBlocks for Reporter/Interview rows. The template
        # already owns speaker creation/roles; Batch only fills their data.
        created_blocks: list[str] = []
        if speaker_service is not None and speech_blocks is not None and body is not None:
            speakers = speaker_service.list(item.project_id)
            role_map = {str(getattr(s, "role", "")).casefold(): s for s in speakers}
            block_specs = [
                ("reporter_text", ("reporter", "interviewer", "presenter"), "reporter_voice"),
                ("guest_text", ("guest",), "guest_voice"),
                ("narrator_text", ("narrator",), "narrator_voice"),
                ("reporter_outro", ("reporter", "presenter"), "reporter_voice"),
            ]
            existing = speech_blocks.for_section(item.project_id, body.section_id, migrate_legacy=False)
            if any(str(resolved.get(key) or "").strip() for key, _, _ in block_specs):
                for old in list(existing):
                    try:
                        speech_blocks.delete(item.project_id, old.id)
                    except Exception:
                        pass
                for key, roles, voice_key in block_specs:
                    text = str(resolved.get(key) or "").strip()
                    if not text:
                        continue
                    speaker = next((role_map.get(role) for role in roles if role_map.get(role) is not None), None)
                    if speaker is None:
                        continue
                    voice_id = str(resolved.get(voice_key) or resolved.get("voice") or "")
                    if voice_id:
                        speaker_service.update(item.project_id, speaker.id, voice_id=voice_id, language=str(resolved.get("language") or source_language))
                    block = speech_blocks.add(
                        item.project_id,
                        body.section_id,
                        text,
                        speaker_id=speaker.id,
                        language=str(resolved.get("language") or source_language),
                    )
                    created_blocks.append(block.id)
        if progress:
            progress(1.0, "Script and speech data prepared")
        return {
            "resolved": {"script_id": script.script_id, "speech_block_ids": created_blocks},
            "output_reference": script.script_id,
        }

    def translate(batch, item, *, cancellation=None, progress=None):
        policy = str(batch.settings.get("translation_policy") or "reviewed_only")
        source = str(item.resolved_data.get("source_language") or "")
        target = str(item.resolved_data.get("language") or source)
        if source == target or policy == "skip_translation":
            return {}
        if policy == "reviewed_only":
            if script_service is None:
                raise RuntimeError("Existing ScriptService is unavailable.")
            reviewed_text = str(item.resolved_data.get("translated_script") or item.resolved_data.get("translated_body") or item.resolved_data.get("translated_text") or "").strip()
            reviewed_id = str(item.resolved_data.get("reviewed_translation_id") or "").strip()
            if not bool(item.resolved_data.get("translation_reviewed")) or (not reviewed_text and not reviewed_id):
                raise RuntimeError("Reviewed translation content/reference is required for this item.")
            script, sections = script_service.load_or_create(item.project_id)
            if reviewed_text:
                body = next((section for section in sections if str(getattr(section, "type", "")) == "body"), sections[0] if sections else None)
                if body is not None:
                    body.content = reviewed_text
                    script_service.save_section(item.project_id, body)
            script.language = target
            script_service.save_script(script)
            return {"resolved": ({"translation_id": reviewed_id} if reviewed_id else {}), "metadata": {"translationPolicy": "reviewed_only", "machineTranslationUsed": False}, "output_reference": reviewed_id}
        if policy != "allow_machine_translation":
            raise RuntimeError("Unknown Batch translation policy.")
        if translation_service is None or script_service is None:
            raise RuntimeError("Existing TranslationService is unavailable.")
        if not languages.supports_translation_pair(source, target):
            raise RuntimeError(f"Configured translation provider does not support {source} → {target}.")
        script, sections = script_service.load_or_create(item.project_id)
        job = translation_service.create_from_script(item.project_id, script.script_id, target)
        if progress:
            progress(0.1, "Translating with configured provider")
        translated = translation_service.translate_document(item.project_id, job.id, cancellation=cancellation)
        segment_repo = getattr(translation_service, "repository", None)
        if segment_repo is not None:
            translated_segments = segment_repo.segments(translated.id)
            by_source = {str(getattr(s, "source_segment_id", "")): s for s in translated_segments}
            for section in sections:
                seg = by_source.get(section.section_id)
                text = str(getattr(seg, "translated_text", "") or "") if seg is not None else ""
                if text:
                    section.content = text
                    script_service.save_section(item.project_id, section)
        script.language = target
        script_service.save_script(script)
        if progress:
            progress(1.0, "Translation complete")
        return {
            "resolved": {"translation_id": translated.id, "machine_translation_used": True},
            "metadata": {"machineTranslationUsed": True},
            "output_reference": translated.id,
        }

    def generate_tts(batch, item, *, cancellation=None, progress=None):
        if not item.project_id:
            raise RuntimeError("Batch project is unavailable for TTS.")
        if multi_tts is not None and speech_blocks is not None:
            blocks = speech_blocks.for_project(item.project_id)
            active = [b for b in blocks if str(getattr(b, "text", "")).strip()]
            if len(active) > 1 or item.resolved_data.get("speech_block_ids"):
                if progress:
                    progress(0.1, "Generating multi-speaker speech")
                outputs = multi_tts.generate_sequence(item.project_id, cancellation=cancellation)
                if progress:
                    progress(1.0, "Multi-speaker speech complete")
                return {
                    "resolved": {"generated_audio_ids": [x.id for x in outputs]},
                    "output_reference": outputs[-1].id if outputs else "",
                }
        if narration_service is None or voice_service is None:
            raise RuntimeError("Existing TTS/Narration service is unavailable.")
        voice_id = str(item.resolved_data.get("voice") or item.resolved_data.get("voice_id") or "")
        if not voice_id:
            raise RuntimeError("Voice Setup Required for this Batch item.")
        voice = voice_service.get(voice_id)
        language = str(item.resolved_data.get("language") or "en")
        engine = str(getattr(voice, "engine_id", "voxcpm2") or "voxcpm2")
        if not languages.supports_tts(language, engine):
            raise RuntimeError(f"Selected voice engine does not support {language}.")
        voice_service.assign_project(item.project_id, voice_id)
        config = voice_service.voice_config(voice_id)
        if progress:
            progress(0.1, "Generating narration")
        generated = narration_service.generate_full(
            item.project_id,
            config,
            cancellation=cancellation,
            progress=(lambda p: progress(min(0.95, max(0.1, float(getattr(p, "ratio", 0.5)))), str(getattr(p, "message", "Generating narration") or "Generating narration"))) if progress else None,
        )
        if progress:
            progress(1.0, "Narration complete")
        return {
            "resolved": {"generated_audio_id": generated.id},
            "output_reference": generated.id,
        }

    def generate_subtitles(batch, item, *, cancellation=None, progress=None):
        if subtitle_service is None:
            raise RuntimeError("Existing SubtitleService is unavailable.")
        preset = str(item.resolved_data.get("subtitle_preset") or batch.template_snapshot.get("metadata", {}).get("subtitlePresetId") or "clean")
        translation_id = str(item.resolved_data.get("translation_id") or "")
        transcript_id = str(item.resolved_data.get("transcript_id") or "")
        if translation_id:
            track = subtitle_service.create_from_translation(item.project_id, translation_id, preset_id=preset)
        elif transcript_id:
            track = subtitle_service.create_from_transcript(item.project_id, transcript_id, preset_id=preset)
        else:
            existing = subtitle_service.list_tracks(item.project_id)
            if existing:
                track = existing[0]
            else:
                # Arbitrary CSV text has no trustworthy timings. Do not fabricate
                # subtitle timings; template/translation/transcript must provide them.
                raise RuntimeError("Subtitle timing source is unavailable for this item.")
        if progress:
            progress(1.0, "Subtitles ready")
        return {"resolved": {"subtitle_track_id": track.id}, "output_reference": track.id}

    def render_export(batch, item, *, cancellation=None, progress=None):
        if export_service is None:
            raise RuntimeError("Existing ExportService is unavailable.")
        relative = str(item.resolved_data.get("output_relative") or f"{item.item_key}.mp4")
        root = Path(batch.output_directory).expanduser().resolve()
        target = (root / relative).resolve()
        if target != root and root not in target.parents:
            raise RuntimeError("Batch output path escaped the configured output directory.")
        target.parent.mkdir(parents=True, exist_ok=True)
        platform = str(item.metadata.get("variant", {}).get("platform") or item.resolved_data.get("platform") or "")
        preset_id = _platform_preset(platform)
        request = export_service.default_request(item.project_id, preset_id=preset_id)
        request.output_folder = str(target.parent)
        request.filename = target.name
        collision = str(batch.settings.get("collision_policy") or "keep_both")
        request.overwrite_policy = {"keep_both": "keep_both", "replace": "replace", "fail": "fail"}.get(collision, "keep_both")
        if progress:
            progress(0.05, "Rendering with the existing export pipeline")
        output = export_service.export(
            request,
            cancellation=cancellation,
            progress_callback=(lambda value, message="": progress(float(getattr(value, 'fraction', getattr(value, 'progress', value if isinstance(value,(int,float)) else 0.5))), str(getattr(value, 'message', message) or message))) if progress else None,
        )
        output_path = str(getattr(output, "file_path", "") or getattr(output, "path", "") or "")
        if not output_path or not Path(output_path).is_file():
            raise RuntimeError("Export completed without a validated output file.")
        if progress:
            progress(1.0, "Render complete")
        return {
            "output_path": output_path,
            "output_reference": str(getattr(output, "id", "") or output_path),
            "metadata": {"renderedBy": "Phase16 ExportService", "exportPresetId": preset_id},
        }

    def validate_export(batch, item, *, cancellation=None, progress=None):
        if not item.output_path:
            raise RuntimeError("Batch item has no rendered output.")
        path = Path(item.output_path)
        if not path.is_file() or path.stat().st_size <= 0:
            raise RuntimeError("Rendered output is missing or invalid.")
        if progress:
            progress(1.0, "Output validated")
        return {"output_reference": item.output_path}

    execution.register_handler(BatchStage.CREATE_PROJECT, create_project)
    execution.register_handler(BatchStage.PREPARE_SCRIPT, prepare_script)
    execution.register_handler(BatchStage.TRANSLATE, translate)
    execution.register_handler(BatchStage.GENERATE_TTS, generate_tts)
    execution.register_handler(BatchStage.GENERATE_SUBTITLES, generate_subtitles)
    # TemplateApplyService creates canonical scenes/layers; no Batch scene engine.
    execution.register_handler(BatchStage.PREPARE_SCENES, lambda batch, item, **_: {"output_reference": item.project_id})
    # Phase 16 ExportService owns the Phase 15 render. Render happens once here;
    # the explicit export stage only verifies the produced output/checkpoint.
    execution.register_handler(BatchStage.RENDER, render_export)
    execution.register_handler(BatchStage.EXPORT, validate_export)

    worker = BatchWorker(execution, item_repository, logger=logger)
    scheduler = BatchScheduler(
        service,
        batch_repository,
        item_repository,
        worker,
        container.resolve(WorkerPool),
        logger=logger,
    )

    for cls, obj in (
        (BatchRepository, batch_repository),
        (BatchItemRepository, item_repository),
        (BatchImportService, importer),
        (BatchMappingService, mapping),
        (BatchVariantService, variants),
        (BatchAssetService, assets),
        (BatchValidationService, validation),
        (BatchService, service),
        (BatchRecoveryService, recovery),
        (BatchExecutionService, execution),
        (BatchWorker, worker),
        (BatchScheduler, scheduler),
    ):
        container.register_instance(cls, obj)

    recovery.recover_startup()
    return batch_repository, item_repository, importer, service, execution, scheduler


def run() -> int:
    p24 = p25.p24
    try:
        from PySide6.QtQml import qmlRegisterSingletonType
    except ImportError:
        return p24.bootstrap.run()

    container = p24.bootstrap.build_container()
    dub_service, dub_apply, dub_validation = p24.extend_phase21(container)
    phase22_repository, languages, visual, speakers, blocks, universal = p24._extend_phase22(container)
    short_repository, candidates, reframe, captions, shorts = p24._extend_phase23(container)
    template_repository, templates, template_apply = p24._extend_phase24(
        container, phase22_repository, languages, visual, speakers, short_repository
    )
    asset_repository, assets, asset_usage, asset_project = p25._extend_phase25(container)
    batch_repository, item_repository, imports, batch_service, execution, scheduler = _extend_phase26(
        container, templates, template_apply, asset_repository, languages
    )

    worker_pool = container.resolve(p24.WorkerPool)
    logger = container.resolve("logger")
    transcript_repository = container.resolve(p24.TranscriptRepository)
    media_repository = container.resolve(p24.MediaRepository)
    scene_repository = container.resolve(p24.SceneRepository)
    project_repository = container.resolve(p24.ProjectRepository)

    class RuntimeDubbingController(p24.DubbingController):
        def __init__(self, parent=None):
            super().__init__(dub_service, dub_validation, worker_pool, dub_apply, transcript_repository=transcript_repository, media_repository=media_repository, logger=logger, parent=parent)

    class RuntimeLanguageController(p24.LanguageController):
        def __init__(self, parent=None):
            super().__init__(languages, parent)

    class RuntimeVideoStudioController(p24.VideoStudioController):
        def __init__(self, parent=None):
            super().__init__(universal, visual, speakers, blocks, phase22_repository, media_repository, container.resolve(p24.SceneService), languages, parent, logger)

    class RuntimeWordTimingController(p24.WordTimingController):
        def __init__(self, parent=None):
            super().__init__(container.resolve(p24.WordTimingService), parent, logger)

    class RuntimeShortsController(p24.ShortsController):
        def __init__(self, parent=None):
            super().__init__(shorts, candidates, captions, reframe, short_repository, media_repository, transcript_repository, scene_repository, project_repository, languages, logger, parent)

    class RuntimeTemplateController(p24.TemplateController):
        def __init__(self, parent=None):
            super().__init__(templates, template_apply, logger, parent)

    class RuntimeAssetController(p25.AssetLibraryController):
        def __init__(self, parent=None):
            super().__init__(assets, asset_repository, asset_usage, asset_project, importer=container.resolve(p25.AssetImportService), relink=container.resolve(p25.AssetRelinkService), logger=logger, parent=parent)

    class RuntimeBatchController(BatchController):
        def __init__(self, parent=None):
            super().__init__(batch_service, imports, batch_repository, item_repository, templates, scheduler, logger=logger, parent=parent)

    qmlRegisterSingletonType(RuntimeDubbingController, "SPVideoStudio.Phase21", 1, 0, "Dubbing")
    qmlRegisterSingletonType(RuntimeLanguageController, "SPVideoStudio.Phase22", 1, 0, "LanguageCatalog")
    qmlRegisterSingletonType(RuntimeVideoStudioController, "SPVideoStudio.Phase22", 1, 0, "VideoStudio")
    qmlRegisterSingletonType(RuntimeWordTimingController, "SPVideoStudio.Phase22", 1, 0, "WordTiming")
    qmlRegisterSingletonType(RuntimeShortsController, "SPVideoStudio.Phase23", 1, 0, "Shorts")
    qmlRegisterSingletonType(RuntimeTemplateController, "SPVideoStudio.Phase24", 1, 0, "Templates")
    qmlRegisterSingletonType(RuntimeAssetController, "SPVideoStudio.Phase25", 1, 0, "AssetLibrary")
    qmlRegisterSingletonType(RuntimeBatchController, "SPVideoStudio.Phase26", 1, 0, "BatchFactoryController")

    original = p24.bootstrap.build_container
    p24.bootstrap.build_container = lambda: container
    try:
        return p24.bootstrap.run()
    finally:
        p24.bootstrap.build_container = original
