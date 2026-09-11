from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.bootstrap import build_container
from domain.export_preset import ExportPreset
from domain.export_request import ExportRequest, ExportRequestError
from domain.project import Project
from domain.render_job import RenderJob
from domain.render_output import RenderOutput
from services.export_filename_service import ExportFilenameService, ExportOutputConflict
from services.export_preset_service import ExportPresetService
from services.export_service import ExportError, ExportService
from services.export_validation_service import ExportValidationService
from services.project_service import ProjectService
from services.scene_service import SceneService
from services.subtitle_service import SubtitleService
from storage.database import SQLiteDatabase
from storage.repositories.export_preset_repository import ExportPresetRepository
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.render_job_repository import RenderJobRepository
from storage.repositories.render_output_repository import RenderOutputRepository


def make_container(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    return build_container()


def make_project_with_scene(tmp_path: Path, monkeypatch, *, aspect="16:9"):
    container=make_container(tmp_path,monkeypatch)
    projects=container.resolve(ProjectService)
    project=projects.create_project("ព័ត៌មាន Export Test","video","km",aspect,30)
    scenes=container.resolve(SceneService)
    scene=scenes.add_scene(project.id,"Scene 1",1000)
    scenes.update_general(project.id,scene.id,background_color="#102030")
    return container, project


def test_phase16_schema_migration_and_tables(tmp_path: Path):
    db=SQLiteDatabase(tmp_path/"app.db"); db.initialize()
    assert db.current_version() == 17
    with db.connect() as c:
        names={r["name"] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"export_presets","project_export_profiles"} <= names


def test_upgrade_from_phase15_schema_applies_export_migration(tmp_path: Path):
    from storage.migrations import MIGRATIONS
    db=SQLiteDatabase(tmp_path/"upgrade.db")
    with db.connect() as c:
        c.execute("CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY,name TEXT NOT NULL,applied_at TEXT NOT NULL)")
        for m in MIGRATIONS:
            if m.version>12: continue
            m.apply(c); c.execute("INSERT INTO schema_migrations VALUES(?,?,?)",(m.version,m.name,"old"))
        c.commit()
    assert db.current_version()==12
    db.initialize(); assert db.current_version() == 17
    with db.connect() as c: assert c.execute("SELECT COUNT(*) FROM export_presets").fetchone()[0]==0


def test_builtin_export_registry_has_unique_expected_presets(tmp_path: Path):
    db=SQLiteDatabase(tmp_path/"db.sqlite"); db.initialize(); service=ExportPresetService(ExportPresetRepository(db))
    rows=service.list_all(); ids=[x.id for x in rows]
    assert len(ids)==len(set(ids))
    expected={"tiktok","youtube_shorts","instagram_reels","youtube","facebook_vertical","facebook_square","facebook_landscape","generic_vertical","generic_landscape","generic_square","custom"}
    assert expected <= set(ids)
    assert all(x.builtin for x in rows)


@pytest.mark.parametrize("preset_id,aspect,width,height",[
    ("tiktok","9:16",1080,1920),
    ("youtube_shorts","9:16",1080,1920),
    ("instagram_reels","9:16",1080,1920),
    ("youtube","16:9",1920,1080),
    ("facebook_square","1:1",1080,1080),
])
def test_platform_preset_values(tmp_path: Path,preset_id,aspect,width,height):
    db=SQLiteDatabase(tmp_path/f"{preset_id}.db"); db.initialize(); service=ExportPresetService(ExportPresetRepository(db)); p=service.get(preset_id)
    assert (p.aspect_ratio,p.width,p.height)==(aspect,width,height)
    assert p.container=="mp4" and p.video_codec=="h264" and p.audio_codec=="aac"


def test_export_preset_model_validation():
    p=ExportPreset("My Vertical","custom","",1080,1920,"9:16",60,quality_profile="high")
    p.validate(); assert p.to_dict()["fps"]==60
    with pytest.raises(ValueError): ExportPreset("Bad","custom","",1079,1920,"9:16",30).validate()


def test_custom_preset_create_duplicate_delete_and_restart(tmp_path: Path):
    db=SQLiteDatabase(tmp_path/"db.sqlite"); db.initialize(); repo=ExportPresetRepository(db); service=ExportPresetService(repo)
    request=ExportRequest("p","tiktok",1080,1920,60,"high","auto","none","",str(tmp_path),"x.mp4")
    saved=service.create_custom("My Vertical HQ","60 FPS",request); assert not saved.builtin
    clone=service.duplicate(saved.id,"My Vertical HQ Copy"); assert clone.id!=saved.id and clone.width==1080
    service2=ExportPresetService(ExportPresetRepository(SQLiteDatabase(db.path)))
    assert service2.get(saved.id).fps==60
    service2.delete(clone.id); assert all(x.id!=clone.id for x in service2.list_all())
    with pytest.raises(ValueError): service2.delete("tiktok")


def test_project_export_profile_persists(tmp_path: Path):
    db=SQLiteDatabase(tmp_path/"db.sqlite"); db.initialize(); projects=ProjectRepository(db); projects.create(Project(project_id="p",title="P",workflow="video",project_path=str(tmp_path/"P")))
    service=ExportPresetService(ExportPresetRepository(db)); req=ExportRequest("p","youtube",1920,1080,30,output_folder=str(tmp_path),filename="x.mp4")
    service.save_profile("p",req); profile=ExportPresetService(ExportPresetRepository(db)).profile("p")
    assert profile and profile.last_preset_id=="youtube" and profile.settings["filename"]=="x.mp4"


def test_export_request_validation():
    valid=ExportRequest("p","youtube",1920,1080,30,output_folder="/tmp",filename="x.mp4"); valid.validate()
    with pytest.raises(ExportRequestError): ExportRequest("p","youtube",1919,1080,30,output_folder="/tmp",filename="x.mp4").validate()
    with pytest.raises(ExportRequestError): ExportRequest("p","youtube",1920,1080,29,output_folder="/tmp",filename="x.mp4").validate()
    with pytest.raises(ExportRequestError): ExportRequest("p","youtube",1920,1080,30,subtitle_mode="burn",output_folder="/tmp",filename="x.mp4").validate()


def test_filename_sanitization_english_khmer_and_extension():
    service=ExportFilenameService()
    assert service.sanitize("My News Video") == "My News Video.mp4"
    assert service.sanitize("ព័ត៌មានថ្មី.mp4") == "ព័ត៌មានថ្មី.mp4"
    assert service.sanitize("video.mov") == "video.mp4"
    assert service.sanitize('bad:name?*.mp4') == "bad_name__.mp4"
    assert service.sanitize("CON.mp4").startswith("_CON")


def test_file_collision_keep_both_replace_cancel(tmp_path: Path):
    svc=ExportFilenameService(); (tmp_path/"video.mp4").write_bytes(b"old")
    assert svc.resolve(tmp_path,"video.mp4","keep_both").name=="video_2.mp4"
    assert svc.resolve(tmp_path,"video.mp4","replace").name=="video.mp4"
    with pytest.raises(ExportOutputConflict): svc.resolve(tmp_path,"video.mp4","cancel")


def test_managed_output_classification(tmp_path: Path):
    project=tmp_path/"Project"; managed=project/"renders"/"video.mp4"; external=tmp_path/"Elsewhere"/"video.mp4"
    assert ExportFilenameService.is_managed(project,managed)
    assert not ExportFilenameService.is_managed(project,external)


def test_output_folder_validation_and_estimated_size(tmp_path: Path):
    svc=ExportValidationService(ExportFilenameService()); folder=svc.validate_folder(tmp_path/"new",create=True); assert folder.is_dir()
    estimate=svc.estimate_size(60_000,1080,1920,"balanced",True,"high")
    assert estimate>1_000_000


def test_default_request_uses_project_aspect_and_khmer_filename(tmp_path: Path,monkeypatch):
    container,project=make_project_with_scene(tmp_path,monkeypatch,aspect="9:16"); service=container.resolve(ExportService); req=service.default_request(project.id)
    assert req.preset_id=="generic_vertical" and (req.width,req.height)==(1080,1920)
    assert "ព័ត៌មាន" in req.filename and req.filename.endswith(".mp4")


def test_apply_preset_changes_resolution_without_rendering(tmp_path: Path,monkeypatch):
    container,project=make_project_with_scene(tmp_path,monkeypatch); service=container.resolve(ExportService); req=service.default_request(project.id)
    service.apply_preset(req,"tiktok")
    assert (req.width,req.height,req.fps)==(1080,1920,30) and req.preset_id=="tiktok"


def test_export_build_plan_wraps_existing_renderer_and_snapshot(tmp_path: Path,monkeypatch):
    container,project=make_project_with_scene(tmp_path,monkeypatch); service=container.resolve(ExportService)
    req=service.default_request(project.id,"youtube"); req.width=320;req.height=180;req.output_folder=str(tmp_path/"out");req.filename="plan.mp4";req.encoder="libx264";req.fit_mode="fit"
    plan=service.build_plan(req)
    assert plan.project_id==project.id and plan.settings.width==320 and plan.settings.metadata["exportPresetId"]=="youtube"
    assert plan.metadata["exportRequest"]["fitMode"]=="fit" and plan.output_path.endswith("plan.mp4")


def test_aspect_warning_and_validation_summary(tmp_path: Path,monkeypatch):
    container,project=make_project_with_scene(tmp_path,monkeypatch,aspect="16:9"); service=container.resolve(ExportService)
    req=service.default_request(project.id,"tiktok"); req.width=1080;req.height=1920;req.output_folder=str(tmp_path/"out");req.filename="x.mp4";req.encoder="libx264"
    issues,summary=service.validate(req)
    assert "export_aspect_mismatch" in {i.code for i in issues}
    assert summary.expected_duration_ms==1000 and summary.estimated_size_bytes>0


def test_subtitle_track_selection_defaults_to_project_default(tmp_path: Path,monkeypatch):
    container,project=make_project_with_scene(tmp_path,monkeypatch); subtitles=container.resolve(SubtitleService); track=subtitles.create_manual(project.id,"km",name="Khmer"); subtitles.set_default(project.id,track.id)
    service=container.resolve(ExportService); req=service.default_request(project.id,"tiktok")
    assert req.subtitle_track_id==track.id and req.subtitle_mode=="burn"


def test_render_output_repository_recent_and_metadata_update(tmp_path: Path):
    db=SQLiteDatabase(tmp_path/"db.sqlite"); db.initialize(); projects=ProjectRepository(db); projects.create(Project(project_id="p",title="P",workflow="video",project_path=str(tmp_path/"P")))
    jobs=RenderJobRepository(db); outputs=RenderOutputRepository(db); job=RenderJob("p");jobs.create(job);out=RenderOutput("p",job.id,str(tmp_path/"x.mp4"),320,180,30,1000,"h264",metadata={"exportPresetId":"tiktok"});outputs.create(out)
    out.metadata["subtitleMode"]="none";outputs.update(out)
    assert outputs.get(out.id).metadata["subtitleMode"]=="none" and outputs.list_recent(1)[0].id==out.id


def test_export_again_restores_settings_from_history(tmp_path: Path,monkeypatch):
    container,project=make_project_with_scene(tmp_path,monkeypatch); outputs=container.resolve(RenderOutputRepository); jobs=container.resolve(RenderJobRepository); service=container.resolve(ExportService)
    req=service.default_request(project.id,"youtube"); req.output_folder=str(tmp_path/"out");req.filename="old.mp4"
    job=RenderJob(project.id);jobs.create(job);out=RenderOutput(project.id,job.id,str(tmp_path/"out"/"old.mp4"),1920,1080,30,1000,"h264",metadata={"exportRequest":req.to_dict(),"externalOutput":True});outputs.create(out)
    restored=service.request_from_output(project.id,out.id)
    assert restored.preset_id=="youtube" and restored.overwrite_policy=="keep_both" and restored.filename=="old.mp4"


def test_missing_export_file_history_is_still_readable(tmp_path: Path,monkeypatch):
    container,project=make_project_with_scene(tmp_path,monkeypatch); outputs=container.resolve(RenderOutputRepository); jobs=container.resolve(RenderJobRepository); service=container.resolve(ExportService)
    job=RenderJob(project.id);jobs.create(job);out=RenderOutput(project.id,job.id,str(tmp_path/"missing.mp4"),320,180,30,1000,"h264",metadata={"externalOutput":True});outputs.create(out)
    assert service.history(project.id)[0].id==out.id
    service.remove_history(project.id,out.id); assert service.history(project.id)==[]


def test_external_export_delete_requires_explicit_confirmation(tmp_path: Path,monkeypatch):
    container,project=make_project_with_scene(tmp_path,monkeypatch); outputs=container.resolve(RenderOutputRepository); jobs=container.resolve(RenderJobRepository); service=container.resolve(ExportService)
    path=tmp_path/"external.mp4";path.write_bytes(b"x");job=RenderJob(project.id);jobs.create(job);out=RenderOutput(project.id,job.id,str(path),320,180,30,1000,"h264",metadata={"externalOutput":True});outputs.create(out)
    with pytest.raises(ExportError): service.delete_export(project.id,out.id)
    assert path.exists()
    service.delete_export(project.id,out.id,allow_external=True); assert not path.exists() and outputs.get(out.id) is None


def test_managed_export_delete_uses_render_safety(tmp_path: Path,monkeypatch):
    container,project=make_project_with_scene(tmp_path,monkeypatch); outputs=container.resolve(RenderOutputRepository); jobs=container.resolve(RenderJobRepository); service=container.resolve(ExportService)
    path=Path(project.project_path)/"renders"/"managed.mp4";path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b"x");job=RenderJob(project.id);jobs.create(job);out=RenderOutput(project.id,job.id,str(path),320,180,30,1000,"h264",metadata={"externalOutput":False});outputs.create(out)
    service.delete_export(project.id,out.id); assert not path.exists() and outputs.get(out.id) is None


def test_no_audio_setting_reaches_render_plan(tmp_path: Path,monkeypatch):
    container,project=make_project_with_scene(tmp_path,monkeypatch); service=container.resolve(ExportService); req=service.default_request(project.id,"youtube");req.width=320;req.height=180;req.audio_enabled=False;req.output_folder=str(tmp_path/"out");req.filename="silent.mp4";req.encoder="libx264"
    plan=service.build_plan(req); assert plan.settings.include_audio is False


def test_qml_export_workspace_and_ctrl_e():
    page=Path("ui/qml/pages/ProjectWorkspacePage.qml").read_text(encoding="utf-8")
    assert 'text: "Export"' in page and 'ExportPage {' in page and 'Ctrl+E' in page and 'exportController' in page
    for name in ["ExportPage.qml","ExportDialog.qml","ExportPresetCard.qml","ExportSettingsPanel.qml","ExportSummary.qml","ExportProgress.qml","ExportComplete.qml","ExportHistory.qml"]:
        assert (Path("ui/qml/export")/name).is_file()


def test_export_ui_does_not_construct_ffmpeg_commands():
    text="\n".join(p.read_text(encoding="utf-8") for p in Path("ui/qml/export").glob("*.qml"))
    assert "ffmpeg" not in text.lower() and "filter_complex" not in text
    controller=Path("ui/controllers/export_controller.py").read_text(encoding="utf-8")
    assert "RenderService" not in controller and "subprocess" not in controller


def test_pre_export_flush_guard_present():
    text=Path("ui/controllers/export_controller.py").read_text(encoding="utf-8")
    assert "_pre_export_flush" in text and "Project changes could not be saved" in text


def test_builtin_registry_is_versioned_json():
    data=json.loads(Path("resources/export/presets.json").read_text(encoding="utf-8"))
    assert data["schema_version"]==1 and len(data["presets"])==11
