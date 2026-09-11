from __future__ import annotations

import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.bootstrap import build_container
from domain.render_job import RenderJob, RenderJobStatus
from domain.render_output import RenderOutput
from domain.render_preset import BUILTIN_RENDER_PRESETS
from domain.render_settings import RenderSettings
from media.ffmpeg import FFmpegCapabilities, FFmpegRunner
from media.ffmpeg_escape import escape_filter_path, subtitles_filter
from media.filters import fit_filter
from rendering.encoder_registry import EncoderRegistry
from rendering.errors import RenderOutputInvalid
from rendering.output_validator import OutputValidator
from rendering.overlay_renderer import OverlayRenderer
from rendering.progress import RenderProgressMapper
from rendering.render_plan import RenderPlan, expected_sequence_duration_ms, project_time_map
from rendering.scene_renderer import SceneRenderer
from rendering.temp_manager import RenderTempManager
from rendering.transition_renderer import TransitionRenderer
from services.project_service import COPYABLE_DIRS, ProjectService
from services.render_validation_service import RenderValidationService
from storage.database import SQLiteDatabase
from storage.repositories.render_job_repository import RenderJobRepository
from storage.repositories.render_output_repository import RenderOutputRepository


class FakeRunner:
    def __init__(self, ready: dict[str, bool] | None = None):
        self.ready = ready or {}
        self.calls: list[list[str]] = []

    def validate_encoder(self, name: str) -> bool:
        return self.ready.get(name, False)

    def run(self, args, **kwargs):
        self.calls.append(list(args))


class FakeProbe:
    def __init__(self, result): self.result = result
    def probe(self, *_args, **_kwargs): return self.result


def caps(*encoders: str) -> FFmpegCapabilities:
    return FFmpegCapabilities("7.1.5", frozenset(encoders), frozenset({"subtitles", "ass", "xfade"}))


def test_phase15_database_migration_tables(tmp_path: Path):
    db = SQLiteDatabase(tmp_path / "app.db")
    db.initialize()
    assert db.current_version() == 14
    with db.connect() as con:
        tables = {row["name"] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"render_jobs", "render_outputs"} <= tables


def test_render_models_and_presets_roundtrip():
    settings = RenderSettings(1080, 1920, 30, "libx264", "balanced", "sub-1", keep_temp=True)
    assert RenderSettings.from_dict(settings.to_dict()).subtitle_track_id == "sub-1"
    assert {p.id for p in BUILTIN_RENDER_PRESETS} == {"vertical_full_hd", "landscape_full_hd", "square_full_hd"}
    job = RenderJob("p", "vertical_full_hd", status=RenderJobStatus.RENDERING, progress=.4)
    assert job.to_dict()["status"] == "rendering"
    output = RenderOutput("p", job.id, "x.mp4", 1080, 1920, 30, 5000, "h264", "aac", 123)
    assert output.to_dict()["resolution"] if "resolution" in output.to_dict() else output.width == 1080


def test_render_settings_validation():
    RenderSettings(1920, 1080, 30).validate()
    with pytest.raises(ValueError): RenderSettings(1919, 1080, 30).validate()
    with pytest.raises(ValueError): RenderSettings(1920, 1080, 29).validate()
    with pytest.raises(ValueError): RenderSettings(1920, 1080, 30, "bad").validate()


def test_render_job_and_output_repository_persistence(tmp_path: Path):
    db = SQLiteDatabase(tmp_path / "app.db"); db.initialize()
    from domain.project import Project
    from storage.repositories.project_repository import ProjectRepository
    ProjectRepository(db).create(Project(project_id="p", title="P", workflow="video", language="en", project_path=str(tmp_path / "P")))
    jobs = RenderJobRepository(db); outputs = RenderOutputRepository(db)
    job = RenderJob("p", status=RenderJobStatus.COMPLETED, expected_duration_ms=3000)
    jobs.create(job)
    out = RenderOutput("p", job.id, str(tmp_path / "P" / "renders" / "a.mp4"), 320, 180, 30, 3000, "h264", "aac", 55)
    outputs.create(out)
    assert jobs.get(job.id).status_code == "completed"
    assert outputs.get(out.id).render_job_id == job.id
    assert outputs.list_for_project("p", 10)[0].id == out.id


def test_encoder_discovery_and_auto_selection():
    runner = FakeRunner({"h264_nvenc": False, "h264_qsv": True})
    registry = EncoderRegistry(runner, caps("libx264", "h264_nvenc", "h264_qsv"))
    assert registry.resolve("auto") == "h264_qsv"
    assert registry.resolve("libx264") == "libx264"
    assert any(item.encoder_id == "h264_nvenc" and item.available for item in registry.list())


def test_explicit_hardware_unavailable_fallback_policy():
    runner = FakeRunner({"h264_nvenc": False})
    registry = EncoderRegistry(runner, caps("libx264", "h264_nvenc"))
    assert registry.resolve("h264_nvenc", allow_fallback=True) == "libx264"
    with pytest.raises(ValueError): registry.resolve("h264_nvenc", allow_fallback=False)
    with pytest.raises(ValueError): EncoderRegistry(runner, caps("libx264")).resolve("h264_amf")


def test_quality_args_are_encoder_specific():
    assert "-crf" in EncoderRegistry.quality_args("libx264", "balanced")
    assert "-cq" in EncoderRegistry.quality_args("h264_nvenc", "high")
    assert "-global_quality" in EncoderRegistry.quality_args("h264_qsv", "fast")


def test_fit_fill_stretch_filters():
    assert "pad=1920:1080" in fit_filter(1920, 1080, "fit")
    assert "crop=1920:1080" in fit_filter(1920, 1080, "fill")
    assert fit_filter(1920, 1080, "stretch").startswith("scale=1920:1080")


def test_windows_unicode_subtitle_path_escaping():
    escaped = escape_filter_path(r"C:\Video Files\ព័ត៌មាន ថ្មី\track [1].ass")
    assert "C\\:" in escaped and "ព័ត៌មាន" in escaped and r"\[1\]" in escaped
    expr = subtitles_filter(r"C:\Video Files\ខ្មែរ\track.ass")
    assert expr.startswith("subtitles=filename='") and "ខ្មែរ" in expr


def test_project_duration_and_scene_local_mapping():
    scenes = [
        {"sceneId": "a", "durationMs": 3000, "transitionOut": {"type": "crossfade", "durationMs": 500}},
        {"sceneId": "b", "durationMs": 4000, "transitionOut": {"type": "cut", "durationMs": 0}},
        {"sceneId": "c", "durationMs": 2000, "transitionOut": {"type": "cut", "durationMs": 0}},
    ]
    assert expected_sequence_duration_ms(scenes) == 8500
    mapping = project_time_map(scenes)
    assert mapping[0]["startMs"] == 0 and mapping[1]["startMs"] == 2500 and mapping[2]["startMs"] == 6500


def test_render_plan_snapshot_is_stable_copy_contract(tmp_path: Path):
    settings = RenderSettings(320, 180, 30, "libx264", "fast")
    scenes = [{"sceneId": "a", "durationMs": 1000}]
    plan = RenderPlan("p", str(tmp_path / "out.mp4"), settings, scenes, 1000, str(tmp_path / "tmp"))
    snapshot = plan.snapshot()
    assert snapshot["schemaVersion"] == 1 and snapshot["scenes"][0]["sceneId"] == "a"
    assert snapshot["settings"]["width"] == 320


def test_progress_parser_handles_na_and_machine_progress():
    info = FFmpegRunner._progress({"frame": "8", "out_time_ms": "N/A", "out_time": "00:00:01.500000", "speed": "1.2x", "progress": "continue"})
    assert info.out_time_ms == 1500 and info.frame == 8 and info.speed == pytest.approx(1.2)
    newer = FFmpegRunner._progress({"out_time_us": "2500000", "speed": "2x", "progress": "continue"})
    assert newer.out_time_ms == 2500


def test_progress_stage_mapping():
    mapper = RenderProgressMapper(2)
    assert mapper.scene(0, 1).overall_progress == pytest.approx(.35)
    assert mapper.combine(1).overall_progress == pytest.approx(.85)
    assert mapper.final(1).overall_progress == pytest.approx(1.0)


def test_overlay_ass_is_valid_dialogue_and_unicode(tmp_path: Path):
    path = OverlayRenderer().write_ass([
        {"type": "headline", "visible": True, "order": 0, "text": "ព័ត៌មានថ្មីថ្ងៃនេះ", "x": .1, "y": .2, "opacity": .8, "style": {"color": "#FFFFFFFF"}}
    ], tmp_path / "overlay.ass", width=1080, height=1920, duration_ms=3000)
    text = path.read_text(encoding="utf-8")
    assert "Dialogue: 0,0:00:00.00,0:00:03.00,Default,,0,0,0,," in text
    assert "ព័ត៌មានថ្មីថ្ងៃនេះ" in text


def test_scene_renderer_builds_image_logo_ass_and_silence(tmp_path: Path):
    runner = FakeRunner(); renderer = SceneRenderer(runner)
    image = tmp_path / "image.png"; image.write_bytes(b"x")
    logo = tmp_path / "logo.png"; logo.write_bytes(b"x")
    spec = {"sceneId":"s","durationMs":2000,"visual":{"path":str(image),"mediaType":"image","fitMode":"fill","backgroundColor":"#000000"},"audio":{},"overlays":[{"type":"logo","visible":True,"assetPath":str(logo),"width":.1,"height":.1,"x":.8,"y":.1,"opacity":.5},{"type":"headline","visible":True,"text":"Hello","x":.1,"y":.1}],"transitionIn":{},"transitionOut":{}}
    cmd = renderer.build_command(spec, RenderSettings(320,180,30), tmp_path / "s.nut", temp_dir=tmp_path)
    joined = " ".join(cmd)
    assert "-loop 1" in joined and "overlay=" in joined and "subtitles=filename=" in joined
    assert "anullsrc" in joined and "-c:v ffv1" in joined and "-c:a pcm_s16le" in joined


def test_scene_renderer_audio_mix_and_video_trim(tmp_path: Path):
    runner = FakeRunner(); renderer = SceneRenderer(runner)
    video = tmp_path / "clip.mp4"; video.write_bytes(b"x")
    narration = tmp_path / "n.wav"; narration.write_bytes(b"x")
    spec = {"sceneId":"s","durationMs":2000,"visual":{"path":str(video),"mediaType":"video","fitMode":"fit","sourceStartMs":500,"hasAudio":True},"audio":{"sourceAudioEnabled":True,"sourceAudioVolume":.2,"narrationPath":str(narration),"narrationEnabled":True,"narrationVolume":1},"overlays":[],"transitionIn":{},"transitionOut":{}}
    cmd = renderer.build_command(spec, RenderSettings(320,180,30), tmp_path / "s.nut", temp_dir=tmp_path)
    joined = " ".join(cmd)
    assert "-ss 0.500000" in joined and "amix=inputs=2" in joined and "volume=0.2000" in joined


def test_transition_renderer_cut_crossfade_and_slide_commands(tmp_path: Path):
    runner = FakeRunner(); renderer = TransitionRenderer(runner)
    files = [tmp_path / "a.nut", tmp_path / "b.nut"]
    renderer.combine(files,[{"durationMs":1000,"transitionOut":{"type":"cut","durationMs":0}},{"durationMs":1000}],tmp_path/"cut.nut",expected_duration_ms=2000)
    assert "-f" in runner.calls[-1] and "concat" in runner.calls[-1]
    renderer.combine(files,[{"durationMs":1000,"transitionOut":{"type":"crossfade","durationMs":200}},{"durationMs":1000}],tmp_path/"xf.nut",expected_duration_ms=1800)
    assert "xfade=transition=fade" in " ".join(runner.calls[-1])
    renderer.combine(files,[{"durationMs":1000,"transitionOut":{"type":"slide","durationMs":200,"direction":"right"}},{"durationMs":1000}],tmp_path/"slide.nut",expected_duration_ms=1800)
    assert "xfade=transition=slideright" in " ".join(runner.calls[-1])


def test_pre_render_validation_no_scenes_bad_aspect_and_missing_assets(tmp_path: Path):
    runner = FakeRunner(); registry = EncoderRegistry(runner, caps("libx264"))
    validator = RenderValidationService(disk_usage=lambda _p: SimpleNamespace(free=10**12))
    settings = RenderSettings(1080,1920,30,"libx264")
    issues = validator.validate(project_path=tmp_path, scenes=[], settings=settings, encoders=registry, output_path=tmp_path/"out.mp4", ffmpeg_filters={"ass"}, project_aspect_ratio="16:9")
    codes = {x.code for x in issues}
    assert "no_scenes" in codes and "aspect_mismatch" in codes
    scene={"sceneId":"s","durationMs":1000,"visual":{"path":str(tmp_path/'missing.mp4'),"mediaType":"video","durationMs":1000},"audio":{},"overlays":[]}
    codes={x.code for x in validator.validate(project_path=tmp_path,scenes=[scene],settings=RenderSettings(320,180,30,"libx264"),encoders=registry,output_path=tmp_path/'out.mp4',ffmpeg_filters={"ass"},project_aspect_ratio="16:9")}
    assert "missing_media" in codes


def test_pre_render_validation_disk_and_encoder_failures(tmp_path: Path):
    runner=FakeRunner(); registry=EncoderRegistry(runner,caps("libx264")); validator=RenderValidationService(disk_usage=lambda _p: SimpleNamespace(free=1))
    scene={"sceneId":"s","durationMs":1000,"visual":{"backgroundEnabled":True},"audio":{},"overlays":[]}
    issues=validator.validate(project_path=tmp_path,scenes=[scene],settings=RenderSettings(320,180,30,"libx264"),encoders=registry,output_path=tmp_path/'out.mp4',ffmpeg_filters={"ass"},project_aspect_ratio="16:9")
    assert "insufficient_disk" in {x.code for x in issues}
    registry2=EncoderRegistry(runner,caps("libx264"))
    issues=validator.validate(project_path=tmp_path,scenes=[scene],settings=RenderSettings(320,180,30,"h264_nvenc",allow_hardware_fallback=False),encoders=registry2,output_path=tmp_path/'out.mp4',ffmpeg_filters={"ass"})
    assert "encoder_unavailable" in {x.code for x in issues}


def test_output_validator_success_and_failures(tmp_path: Path):
    path=tmp_path/'out.mp4'; path.write_bytes(b'1234')
    result=SimpleNamespace(width=320,height=180,fps=30.0,duration_ms=2000,codec='h264',audio_codec='aac')
    validated=OutputValidator(FakeProbe(result)).validate(path,width=320,height=180,fps=30,expected_duration_ms=2000)
    assert validated.file_size==4 and validated.duration_delta_ms==0
    bad=SimpleNamespace(width=640,height=180,fps=30.0,duration_ms=2000,codec='h264',audio_codec='aac')
    with pytest.raises(RenderOutputInvalid): OutputValidator(FakeProbe(bad)).validate(path,width=320,height=180,fps=30,expected_duration_ms=2000)


def test_temp_cleanup_is_guarded(tmp_path: Path):
    project=tmp_path/'project'; manager=RenderTempManager(project,'job'); root=manager.prepare(); (root/'x').write_text('x')
    manager.cleanup(); assert not root.exists()


def test_project_duplication_excludes_render_artifacts(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HOME",str(tmp_path/'home')); monkeypatch.setenv("XDG_DATA_HOME",str(tmp_path/'xdg'))
    c=build_container(); service=c.resolve(ProjectService); project=service.create_project("Original","video","en","16:9",30)
    old=Path(project.project_path)/'renders'/'old.mp4'; old.parent.mkdir(parents=True,exist_ok=True); old.write_bytes(b'old')
    duplicate=service.duplicate_project(project.id)
    assert 'renders' not in COPYABLE_DIRS and not (Path(duplicate.project_path)/'renders'/'old.mp4').exists()
    assert (Path(duplicate.project_path)/'renders').is_dir()


def test_render_tables_cascade_on_project_delete(tmp_path: Path):
    db=SQLiteDatabase(tmp_path/'app.db'); db.initialize()
    from domain.project import Project
    from storage.repositories.project_repository import ProjectRepository
    projects=ProjectRepository(db); projects.create(Project(project_id='p',title='P',workflow='video',language='en',project_path=str(tmp_path/'P')))
    jobs=RenderJobRepository(db); outputs=RenderOutputRepository(db); job=RenderJob('p'); jobs.create(job); out=RenderOutput('p',job.id,'x.mp4',320,180,30,1000,'h264'); outputs.create(out)
    projects.delete('p'); assert jobs.get(job.id) is None and outputs.get(out.id) is None


def test_render_qml_workspace_wiring():
    page=Path('ui/qml/pages/ProjectWorkspacePage.qml').read_text(encoding='utf-8')
    assert 'text: "Export"' in page and 'ExportPage {' in page and 'exportController' in page
    for name in ['RenderDialog.qml','RenderSettings.qml','RenderProgress.qml','RenderResult.qml']:
        assert (Path('ui/qml/render')/name).is_file()


def test_upgrade_from_phase14_schema_applies_render_migration(tmp_path: Path):
    from storage.migrations import MIGRATIONS
    db=SQLiteDatabase(tmp_path/'upgrade.db'); db.path.parent.mkdir(parents=True,exist_ok=True)
    with db.connect() as con:
        con.execute("CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)")
        for migration in MIGRATIONS:
            if migration.version>11: continue
            migration.apply(con); con.execute("INSERT INTO schema_migrations(version,name,applied_at) VALUES(?,?,?)",(migration.version,migration.name,'old'))
        con.commit()
    assert db.current_version()==11
    db.initialize(); assert db.current_version()==14
    with db.connect() as con:
        assert con.execute("SELECT COUNT(*) FROM render_jobs").fetchone()[0]==0


@pytest.mark.parametrize("encoder", ["libx264","h264_nvenc","h264_qsv","h264_amf"])
def test_encoder_registry_reports_known_h264_encoders(encoder):
    registry=EncoderRegistry(FakeRunner(),caps("libx264","h264_nvenc","h264_qsv","h264_amf"))
    ids={item.encoder_id for item in registry.list()}
    assert encoder in ids


def test_pre_render_validation_missing_narration_and_libass(tmp_path: Path):
    registry=EncoderRegistry(FakeRunner(),caps("libx264")); validator=RenderValidationService(disk_usage=lambda _p: SimpleNamespace(free=10**12))
    scene={"sceneId":"s","durationMs":2000,"visual":{"backgroundEnabled":True},"audio":{"narrationAudioId":"a","narrationEnabled":True,"narrationPath":str(tmp_path/'missing.wav')},"overlays":[{"type":"headline","visible":True,"text":"Hi"}]}
    issues=validator.validate(project_path=tmp_path,scenes=[scene],settings=RenderSettings(320,180,30,"libx264"),encoders=registry,output_path=tmp_path/'out.mp4',ffmpeg_filters=set())
    codes={x.code for x in issues}; assert 'missing_narration' in codes and 'libass_missing' in codes


def test_render_service_missing_ffmpeg_is_typed():
    from rendering.errors import RenderFFmpegMissing
    from services.render_service import RenderService
    service=RenderService(None,None,None,None,None,lambda:None,lambda:None,None)
    with pytest.raises(RenderFFmpegMissing): service.encoder_options()
