from __future__ import annotations

import json
import sqlite3
import zipfile
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from domain.template import Template
from domain.template_asset import TemplateAsset
from domain.template_component import TemplateComponent
from domain.template_errors import TemplateApplyError, TemplateChecksumError, TemplatePackageUnsafe, TemplateReadOnly
from domain.template_placeholder import TemplatePlaceholder, resolve_placeholders
from services.language_service import LanguageService
from services.template_apply_service import TemplateApplyService
from services.template_package_service import TemplatePackageService
from services.template_preview_service import TemplatePreviewService
from services.template_service import TemplateService
from services.template_validation_service import TemplateValidationService
from storage.migrations.m021_create_templates import migrate as migrate_templates
from storage.repositories.template_repository import TemplateRepository

ROOT=Path(__file__).resolve().parents[1]
BUILTINS=ROOT/"resources"/"templates"/"builtin"


def languages(): return LanguageService()
def validation(): return TemplateValidationService(languages())

def sample_template(name="ព័ត៌មានទំនើប"):
    return Template(name=name,template_type="project",category="General Video",description="Tin tức hiện đại ข่าวสมัยใหม่",workflow="video",supported_aspect_ratios=("16:9","9:16"),supported_languages=("*",),components=[TemplateComponent("project_settings","project_settings",{"language":"{{project_language}}"})],placeholders=[TemplatePlaceholder("headline","Headline","text")])


def load_builtin(filename:str)->Template:
    return Template.from_dict(json.loads((BUILTINS/filename).read_text(encoding="utf-8")),builtin=True)


def test_builtin_registry_contains_required_phase24_templates():
    items=[Template.from_dict(json.loads(p.read_text(encoding="utf-8")),builtin=True) for p in BUILTINS.glob("*.json")]
    names={x.name for x in items}
    required={"Clean News","Modern News","Reporter News","Interview News","Documentary Story","5-Beat Story","Educational Story","Creator Short","News Short","Interview Short","Minimal Vertical Video","Minimal Landscape Video","Green Screen Presenter","Translate & Dub Basic"}
    assert required <= names
    assert len(items) >= 14
    for item in items: validation().validate(item)


def test_reporter_news_acceptance_template_is_generic_and_layered():
    item=load_builtin("reporter-news.json")
    data=item.to_dict(); encoded=json.dumps(data,ensure_ascii=False)
    assert item.workflow=="news" and {"16:9","9:16"} <= set(item.supported_aspect_ratios)
    assert "speaker_reporter" in encoded and "reporter_voice" in encoded and "background_video" in encoded and "reporter_video" in encoded
    assert '"enabled": true' in encoded and "chromaKey" in encoded
    assert "claimText" not in encoded and "http://" not in encoded and "https://" not in encoded


def test_interview_template_has_two_speakers_and_split_layout():
    item=load_builtin("interview-news.json"); encoded=json.dumps(item.to_dict())
    assert "speaker_interviewer" in encoded and "speaker_guest" in encoded
    assert "interviewer_voice" in encoded and "guest_voice" in encoded
    assert '"width": 0.5' in encoded


def test_story_short_and_dub_templates_do_not_invent_content():
    story=load_builtin("five-beat-story.json"); short=load_builtin("creator-short.json"); dub=load_builtin("translate-dub-basic.json")
    raw=json.dumps(story.to_dict(),ensure_ascii=False).lower()
    for beat in ("hook","setup","development","climax","resolution"): assert beat in raw
    assert short.workflow=="shorts" and short.supported_aspect_ratios==("9:16",)
    assert any(c.type_code=="short_style" and c.data.get("style")=="creator" for c in short.components)
    assert dub.workflow=="translate" and not any(p.type_code in {"video","media","audio"} for p in dub.placeholders)


def test_unicode_template_names_and_controlled_placeholder_resolution():
    item=sample_template(); copy=Template.from_dict(item.to_dict())
    assert copy.name=="ព័ត៌មានទំនើប" and "Tin tức" in copy.description and "ข่าว" in copy.description
    assert resolve_placeholders("{{headline}} · {{unknown}}",{"headline":"Xin chào"})=="Xin chào · "
    assert resolve_placeholders("{{project_language}}",{"project_language":"th"})=="th"


def test_multilingual_compatibility_uses_language_registry():
    reporter=load_builtin("reporter-news.json")
    service=validation()
    for code in ("en","km","th","vi"):
        result=service.compatibility(reporter,language=code,aspect_ratio="9:16")
        assert result["state"] in {"compatible","compatible_with_warnings"}


def test_package_round_trip_and_keep_both_manifest(tmp_path:Path):
    item=sample_template("Tin tức hiện đại"); svc=TemplatePackageService(validation())
    package=svc.export(item,tmp_path/"tin-tuc.mmovtemplate")
    manifest,restored=svc.inspect(package); assert restored.name==item.name and manifest.template_id==item.id
    user=tmp_path/"templates"; imported,folder=svc.import_package(package,user,existing_ids={item.id},conflict="keep_both")
    assert imported.id!=item.id and folder.is_dir()
    local_manifest=json.loads((folder/"manifest.json").read_text(encoding="utf-8")); assert local_manifest["template_id"]==imported.id


def test_zip_traversal_is_rejected(tmp_path:Path):
    package=tmp_path/"bad.mmovtemplate"
    with zipfile.ZipFile(package,"w") as z:z.writestr("../../evil.txt","no")
    with pytest.raises(TemplatePackageUnsafe):TemplatePackageService(validation()).inspect(package)


def test_executable_package_is_rejected(tmp_path:Path):
    package=tmp_path/"bad.mmovtemplate"
    with zipfile.ZipFile(package,"w") as z:z.writestr("assets/script.ps1","Write-Host bad")
    with pytest.raises(TemplatePackageUnsafe):TemplatePackageService(validation()).inspect(package)


def test_checksum_tamper_is_rejected(tmp_path:Path):
    svc=TemplatePackageService(validation()); good=svc.export(sample_template(),tmp_path/"good.mmovtemplate"); bad=tmp_path/"bad.mmovtemplate"
    with zipfile.ZipFile(good,"r") as src, zipfile.ZipFile(bad,"w") as dst:
        for info in src.infolist():
            data=src.read(info.filename)
            if info.filename=="template.json": data=data.replace(b"General Video",b"Tampered     ",1)
            dst.writestr(info.filename,data)
    with pytest.raises(TemplateChecksumError):svc.inspect(bad)


class DB:
    def __init__(self,path): self.path=path
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.path); c.row_factory=sqlite3.Row; c.execute("PRAGMA foreign_keys=ON")
        try: yield c
        finally:c.close()


def test_user_template_restart_persistence_and_usage(tmp_path:Path):
    db=DB(tmp_path/"app.db")
    with db.connect() as c:c.__enter__ if False else None; migrate_templates(c); c.commit()
    root=tmp_path/"templates"; repo=TemplateRepository(db,root); item=sample_template("ข่าวสมัยใหม่")
    folder=root/item.id; folder.mkdir(parents=True); path=folder/"template.json"; path.write_text(json.dumps(item.to_dict(),ensure_ascii=False),encoding="utf-8"); manifest=folder/"manifest.json"; manifest.write_text(json.dumps(item.manifest().to_dict()),encoding="utf-8")
    repo.save(item,path,manifest); repo.record_usage(item.id,template_version=item.version)
    reopened=TemplateRepository(db,root); restored=reopened.get(item.id)
    assert restored and restored.name=="ข่าวสมัยใหม่" and reopened.usage(item.id)["useCount"]==1


def test_template_service_builtin_read_only_and_duplicate(tmp_path:Path):
    db=DB(tmp_path/"app.db")
    with db.connect() as c:migrate_templates(c); c.commit()
    repo=TemplateRepository(db,tmp_path/"users"); val=validation(); package=TemplatePackageService(val)
    service=TemplateService(repo,BUILTINS,tmp_path/"users",val,TemplatePreviewService(),package)
    builtin=service.get("builtin-reporter-news")
    with pytest.raises(TemplateReadOnly):service.delete(builtin.id)
    clone=service.duplicate(builtin.id)
    assert not clone.builtin and clone.id!=builtin.id and service.get(clone.id).name.endswith("Copy")


class FakeProjectRepo:
    def __init__(self,project): self.project=project
    def get_by_id(self,pid): return self.project if pid==self.project.project_id else None
class FakeProjectService:
    def __init__(self,project): self.project=project; self.deleted=[]
    def create_project(self,*args): return self.project
    def delete_project(self,pid): self.deleted.append(pid)
class FakeScenes:
    def __init__(self): self.created=[]; self.deleted=[]; self.overlays=[]
    def add_scene(self,pid,name,duration):
        s=SimpleNamespace(id=f"scene-{len(self.created)+1}",project_id=pid,name=name,duration_ms=duration,background_color="#000",transition_out=SimpleNamespace(to_dict=lambda:{})); self.created.append(s); return s
    def delete_scene(self,pid,sid): self.deleted.append(sid)
    def update_general(self,*args,**kwargs): pass
    def assign_media(self,*args,**kwargs): pass
    def set_transition(self,*args,**kwargs): pass
    def add_lower_third(self,pid,sid,text,secondary): return SimpleNamespace(id=f"o-{len(self.overlays)+1}")
    def add_text_overlay(self,pid,sid,text,kind): return SimpleNamespace(id=f"o-{len(self.overlays)+1}")
    def update_overlay(self,*args,**kwargs): pass
class FakeSceneRepo:
    def list_for_project(self,pid): return []
class FakeVisual:
    def add_media_layer(self,*args,**kwargs): return SimpleNamespace(id="layer-1")
    def update_layer(self,*args,**kwargs): return args[2]
    def set_chroma_key(self,*args,**kwargs): return args[2]
class FakeSpeakers:
    def __init__(self): self.created=[]; self.deleted=[]
    def create(self,pid,name,role,**kwargs): x=SimpleNamespace(id=f"speaker-{len(self.created)+1}",name=name,role=role,language=kwargs.get("language")); self.created.append(x); return x
    def delete(self,pid,sid): self.deleted.append(sid)
class FakeSubtitles:
    def list_tracks(self,pid): return []
class FakeTemplateRepo:
    def __init__(self): self.used=[]
    def record_usage(self,*args,**kwargs): self.used.append((args,kwargs))
class FakeMedia:
    def __init__(self): self.imported=[]; self.removed=[]
    def import_file(self,pid,path): x=SimpleNamespace(id=f"media-{len(self.imported)+1}"); self.imported.append((pid,Path(path))); return x
    def remove_media(self,pid,mid): self.removed.append(mid)


def make_apply(project,media=None):
    scenes=FakeScenes(); speakers=FakeSpeakers(); repo=FakeTemplateRepo()
    svc=TemplateApplyService(FakeProjectService(project),FakeProjectRepo(project),scenes,FakeSceneRepo(),FakeVisual(),speakers,FakeSubtitles(),validation(),repo,media_service=media)
    return svc,scenes,speakers,repo


def test_partial_apply_does_not_create_unselected_scenes_or_speakers():
    project=SimpleNamespace(project_id="p1",language="en",aspect_ratio="16:9",workflow="video")
    svc,scenes,speakers,repo=make_apply(project)
    item=Template(name="Partial",template_type="project",category="General Video",description="",workflow="video",components=[TemplateComponent("sp","speaker_structure",{"speakers":[{"localId":"speaker_a","name":"A","role":"speaker"}]}),TemplateComponent("sc","scene_structure",{"scenes":[{"localId":"scene_a","name":"A"}]}),TemplateComponent("ex","export_recommendation",{"presetId":"youtube"})])
    result=svc.apply_to_project(item,"p1",selected_components=["export_recommendation"])
    assert not scenes.created and not speakers.created and result.recommendations["exportPresetId"]=="youtube"


def test_apply_rollback_removes_created_scenes_and_speakers():
    project=SimpleNamespace(project_id="p1",language="en",aspect_ratio="16:9",workflow="video")
    svc,scenes,speakers,_=make_apply(project)
    item=Template(name="Rollback",template_type="project",category="General Video",description="",workflow="video",components=[TemplateComponent("sp","speaker_structure",{"speakers":[{"localId":"speaker_a","name":"A","role":"speaker"}]}),TemplateComponent("sc","scene_structure",{"scenes":[{"localId":"scene_a","name":"A"}]})])
    svc.failure_injector=lambda component,result: (_ for _ in ()).throw(RuntimeError("forced")) if component=="scene_structure" else None
    with pytest.raises(TemplateApplyError):svc.apply_to_project(item,"p1")
    assert scenes.deleted==["scene-1"] and speakers.deleted==["speaker-1"]


def test_multilingual_speaker_application_preserves_requested_language():
    item=load_builtin("reporter-news.json")
    for code in ("en","km","th","vi"):
        project=SimpleNamespace(project_id=f"p-{code}",language=code,aspect_ratio="9:16",workflow="news")
        svc,_,speakers,_=make_apply(project)
        svc.apply_to_project(item,project.project_id,resolutions={"headline":"","reporter_name":""},selected_components=["speaker_structure"])
        assert speakers.created[0].language==code


def test_packaged_asset_resolution_copies_into_project_media(tmp_path:Path):
    media=FakeMedia(); project=SimpleNamespace(project_id="p1",language="en",aspect_ratio="16:9",workflow="video"); svc,_,_,_=make_apply(project,media)
    folder=tmp_path/"t"; (folder/"assets").mkdir(parents=True); (folder/"assets"/"logo.png").write_bytes(b"png")
    item=sample_template(); item.manifest_path=str(folder/"manifest.json"); item.assets=[TemplateAsset("logo.png","",3,"image")]
    result=svc.apply_to_project(item,"p1",resolutions={"headline":"asset:logo.png"},selected_components=["project_settings"])
    assert result.imported_media_ids==["media-1"] and media.imported[0][1].name=="logo.png"


def test_ui_and_runtime_use_one_template_framework():
    expected=[ROOT/"ui/qml/pages/TemplatesPage.qml",ROOT/"ui/qml/templates/TemplateApplyDialog.qml",ROOT/"ui/qml/templates/SaveTemplateDialog.qml",ROOT/"app/phase24_runtime.py"]
    for path in expected: assert path.is_file()
    text=(ROOT/"app/phase24_runtime.py").read_text(encoding="utf-8")
    assert "SPVideoStudio.Phase24" in text and "TemplateController" in text
    combined="\n".join(p.read_text(encoding="utf-8") for p in (ROOT/"services").glob("template*.py"))
    assert "ShortVideoRenderer" not in combined and "ShortTimeline" not in combined and "eval(" not in combined

class FakeStoryOutline:
    def __init__(self): self.created=[]
    def latest(self,pid): return None,[]
    def create_from_plan(self,pid,template_id=None): self.created.append((pid,template_id)); return SimpleNamespace(id="outline-1"),[1,2,3,4,5]
    def apply_template(self,*args): raise AssertionError("not expected for new story")
class FakeNewsVisual:
    def __init__(self): self.applied=[]
    def apply_theme(self,pid,preset): self.applied.append((pid,preset))


def test_story_template_routes_to_existing_story_outline_service():
    project=SimpleNamespace(project_id="story-1",language="km",aspect_ratio="16:9",workflow="story")
    story=FakeStoryOutline(); svc,_,_,_=make_apply(project); svc.story_outline=story
    item=load_builtin("five-beat-story.json")
    result=svc.apply_to_project(item,"story-1",selected_components=["story_structure"])
    assert story.created==[("story-1","5_beat_story")] and result.recommendations["storyBeatCount"]==5


def test_news_template_routes_to_existing_news_visual_service():
    project=SimpleNamespace(project_id="news-1",language="vi",aspect_ratio="9:16",workflow="news")
    news=FakeNewsVisual(); svc,_,_,_=make_apply(project); svc.news_visual=news
    item=load_builtin("clean-news.json")
    svc.apply_to_project(item,"news-1",selected_components=["news_visual_theme"])
    assert news.applied==[("news-1","clean_news")]
