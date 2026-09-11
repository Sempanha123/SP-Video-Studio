from __future__ import annotations

import contextlib
import sqlite3
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from domain.chroma_key import ChromaKeySettings
from domain.language import language_info, search_languages, supported_language_codes
from domain.project import Project
from domain.scene_layer import SceneLayer, VisualLayerRole
from domain.speaker_profile import SpeakerProfile
from domain.speech_block import SpeechBlock
from rendering.layer_compositor import build_layered_scene_command
from services.frame_time_service import FrameTimeService
from services.language_service import LanguageService, VOXCPM2_LANGUAGE_CODES
from services.visual_layer_service import VisualLayerService
from storage.migrations.m019_create_universal_video_studio import migrate
from storage.repositories.phase22_repository import Phase22Repository


class DB:
    def __init__(self,path): self.path=Path(path)
    @contextlib.contextmanager
    def connect(self):
        c=sqlite3.connect(self.path); c.row_factory=sqlite3.Row; c.execute("PRAGMA foreign_keys=ON")
        try: yield c
        finally:c.close()


def make_db(tmp_path):
    db=DB(tmp_path/"phase22.sqlite")
    with db.connect() as c,c:
        c.executescript("""
        CREATE TABLE projects(id TEXT PRIMARY KEY,title TEXT,workflow TEXT,language TEXT,aspect_ratio TEXT,fps INTEGER,created_at TEXT,updated_at TEXT,last_opened_at TEXT,thumbnail_path TEXT,status TEXT,project_path TEXT,version INTEGER);
        CREATE TABLE scripts(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,title TEXT,language TEXT,status TEXT,pace TEXT,version INTEGER,notes TEXT,metadata_json TEXT,created_at TEXT,updated_at TEXT,FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE);
        CREATE TABLE script_sections(id TEXT PRIMARY KEY,script_id TEXT NOT NULL,section_order INTEGER,section_type TEXT,title TEXT,content TEXT,notes TEXT,enabled INTEGER,metadata_json TEXT,created_at TEXT,updated_at TEXT,FOREIGN KEY(script_id) REFERENCES scripts(id) ON DELETE CASCADE);
        CREATE TABLE scenes(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,scene_order INTEGER,duration_ms INTEGER,FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE);
        CREATE TABLE media_assets(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,type TEXT,name TEXT,original_path TEXT,project_path TEXT,file_size INTEGER,FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE);
        INSERT INTO projects VALUES('p1','P','video','en','16:9',30,'n','n',NULL,NULL,'draft','/tmp/p',1);
        INSERT INTO projects VALUES('p2','P2','video','en','16:9',30,'n','n',NULL,NULL,'draft','/tmp/p2',1);
        INSERT INTO scripts VALUES('sc1','p1','S','th','draft','normal',1,NULL,'{}','n','n');
        INSERT INTO scripts VALUES('sc2','p2','S','th','draft','normal',1,NULL,'{}','n','n');
        INSERT INTO script_sections VALUES('sec1','sc1',0,'body','Intro','สวัสดี วันนี้เราจะมาพูดถึงเทคโนโลยีใหม่',NULL,1,'{}','n','n');
        INSERT INTO script_sections VALUES('sec2','sc2',0,'body','Intro','สวัสดี วันนี้เราจะมาพูดถึงเทคโนโลยีใหม่',NULL,1,'{}','n','n');
        INSERT INTO scenes VALUES('scene1','p1',0,5000); INSERT INTO scenes VALUES('scene2','p2',0,5000);
        INSERT INTO media_assets VALUES('a1','p1','audio','Music','/src/a.wav','/p/a.wav',100);
        INSERT INTO media_assets VALUES('a2','p2','audio','Music','/src/a.wav','/p2/a.wav',100);
        """)
        migrate(c)
    return db


def test_language_registry_core_and_unicode():
    codes=set(supported_language_codes())
    assert {"en","km","th","vi","zh","ja","ko","id","ms","es","fr","de"} <= codes
    assert language_info("km").native_name == "ខ្មែរ"
    assert language_info("th").native_name == "ไทย"
    assert language_info("vi").native_name == "Tiếng Việt"
    assert language_info("th").text_direction == "ltr"
    assert "Noto Sans Thai" in language_info("th").fallback_fonts
    assert search_languages("Tiếng")[0].code == "vi"
    assert "สวัสดี วันนี้เราจะมาพูดถึงเทคโนโลยีใหม่".encode().decode() == "สวัสดี วันนี้เราจะมาพูดถึงเทคโนโลยีใหม่"
    assert "Xin chào, hôm nay chúng ta sẽ nói về công nghệ mới.".encode().decode().startswith("Xin chào")


def test_legacy_and_new_project_languages_validate():
    for code in ("en","km","th","vi"):
        Project("P","video",language=code).validate()


def test_voxcpm_verified_catalog_has_phase22_languages():
    assert {"en","km","th","vi"} <= VOXCPM2_LANGUAGE_CODES


def test_language_capability_uses_engine_pairs(monkeypatch):
    class Engine:
        def get_supported_language_pairs(self): return (("en","th"),("th","en"))
    class Manager:
        def providers(self): return ("x",)
        def get(self,_): return Engine()
    service=LanguageService(translation_manager=Manager())
    monkeypatch.setattr(service,"stt_languages",lambda:{"en","km","th","vi"})
    assert service.supports_translation_pair("en","th")
    assert service.capability("th",translation_target="en").translation == "supported"


def test_chroma_and_layer_validation():
    key=ChromaKeySettings(enabled=True,key_color="#00FF00"); key.validate(); assert key.enabled and key.key_color=="#00FF00"
    layer=SceneLayer("s",0,"media",asset_id="m",x=.6,y=.05,width=.3,height=.4,metadata={"role":"presenter","zOrder":3,"chromaKey":key.to_dict(),"durationMs":1200})
    data=layer.to_dict(); assert data["role"]=="presenter" and data["zOrder"]==3 and data["chromaKey"]["enabled"]


def test_frame_snap_is_deterministic():
    frames=FrameTimeService(); assert frames.snap_ms(1017,30)==1033; assert frames.timecode(1033,30).endswith(":01")


def test_speaker_speech_legacy_and_restart(tmp_path):
    db=make_db(tmp_path); repo=Phase22Repository(db)
    reporter=repo.save_speaker(SpeakerProfile(project_id="p1",name="Reporter",role="reporter",language="th",voice_id="voice-th"))
    guest=repo.save_speaker(SpeakerProfile(project_id="p1",name="Guest",role="interview_guest",language="en",voice_id="voice-en"))
    legacy=repo.ensure_legacy_block("p1","sec1"); assert legacy[0].text.startswith("សวั") or legacy[0].text.startswith("สวั")
    legacy[0].speaker_id=reporter.id; repo.save_block("p1",legacy[0])
    repo.save_block("p1",SpeechBlock("sec1",1,"The new system...",language="en",speaker_id=guest.id))
    repo.save_block("p1",SpeechBlock("sec1",2,"Thank you.",language="th",speaker_id=reporter.id))
    assert [x.speaker_id for x in repo.blocks_for_section("sec1")] == [reporter.id,guest.id,reporter.id]
    reopened=Phase22Repository(DB(db.path)); assert len(reopened.speakers("p1"))==2 and len(reopened.blocks_for_section("sec1"))==3


def test_speaker_delete_foreign_key_does_not_dangle(tmp_path):
    repo=Phase22Repository(make_db(tmp_path)); s=repo.save_speaker(SpeakerProfile(project_id="p1",name="R",role="reporter",language="en")); b=repo.save_block("p1",SpeechBlock("sec1",0,"Hello",speaker_id=s.id))
    repo.delete_speaker("p1",s.id); assert repo.block("p1",b.id).speaker_id==""


def test_project_duplication_maps_phase22_ids(tmp_path):
    repo=Phase22Repository(make_db(tmp_path)); s=repo.save_speaker(SpeakerProfile(project_id="p1",name="R",role="reporter",language="vi")); b=repo.save_block("p1",SpeechBlock("sec1",0,"Xin chào",language="vi",speaker_id=s.id,scene_id="scene1"))
    from domain.manual_audio_clip import ManualAudioClip
    clip=repo.save_audio_clip(ManualAudioClip("p1","a1",100,1000,scene_id="scene1"))
    maps=repo.duplicate_project("p1","p2",media_map={"a1":"a2"},scene_map={"scene1":"scene2"})
    clone=repo.block("p2",maps["block"][b.id]); assert clone and clone.id!=b.id and clone.speaker_id!=s.id and clone.scene_id=="scene2"
    copied=repo.audio_clips("p2"); assert len(copied)==1 and copied[0].media_id=="a2" and copied[0].id!=clip.id


class FakeSceneRepo:
    def __init__(self): self.scene=SimpleNamespace(id="s",project_id="p",duration_ms=5000); self.items=[]
    def get(self,_): return self.scene
    def layers(self,_): return list(self.items)
    def replace_layers(self,project_id,scene_id,layers): self.items=list(layers)
class FakeMediaRepo:
    def __init__(self): self.items={"v":SimpleNamespace(id="v",project_id="p",type="video",duration_ms=4000),"i":SimpleNamespace(id="i",project_id="p",type="image",duration_ms=None)}
    def get_by_id(self,i): return self.items.get(i)


def test_visual_layers_pip_broll_delete_safety():
    scenes=FakeSceneRepo(); media=FakeMediaRepo(); service=VisualLayerService(scenes,media)
    broll=service.add_media_layer("p","s","v",role="broll"); assert broll.to_dict()["useAudio"] is False
    presenter=service.add_media_layer("p","s","v",role="presenter",pip_preset="bottom_right"); assert presenter.x>.5
    service.apply_chroma_preset("p","s",presenter.id,"green"); assert service.list_layers("p","s")[-1].chroma_key.enabled
    service.delete_layer("p","s",presenter.id); assert media.get_by_id("v") is not None and len(scenes.items)==1


def _make_video(path:Path,color:str,box:str|None=None):
    vf=[]
    if box: vf=["-vf",f"drawbox=x=50:y=20:w=60:h=80:color={box}:t=fill"]
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","lavfi","-i",f"color=c={color}:s=160x120:r=30:d=1",*vf,"-an","-c:v","libx264","-pix_fmt","yuv420p",str(path)],check=True)


class Caps: filters=frozenset({"chromakey","colorkey"})
class Runner:
    def discover_capabilities(self): return Caps()
class Overlay:
    def write_ass(self,*args,**kwargs): return None
class Renderer:
    runner=Runner(); overlay_renderer=Overlay(); fonts_dir=None
class Settings:
    width=320; height=180; fps=30


def _render(tmp_path,layers):
    out=tmp_path/"out.nut"; spec={"sceneId":"s","durationMs":1000,"visual":{"path":"","mediaType":"","fitMode":"fill","backgroundColor":"#101010"},"audio":{},"overlays":[],"layers":layers,"transitionIn":{},"transitionOut":{}}
    def fallback(*args,**kwargs): raise AssertionError("layered compositor should be used")
    args=build_layered_scene_command(Renderer(),fallback,spec,Settings(),out,temp_dir=tmp_path)
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",*args],check=True)
    assert out.is_file() and out.stat().st_size>0
    return out


def test_green_screen_ffmpeg_render(tmp_path):
    presenter=tmp_path/"presenter.mp4"; _make_video(presenter,"green","red")
    out=_render(tmp_path,[{"id":"p","assetPath":str(presenter),"mediaType":"video","visible":True,"zOrder":3,"startMs":0,"durationMs":1000,"sourceInMs":0,"x":.55,"y":.1,"width":.4,"height":.8,"opacity":1,"fitMode":"contain","chromaKey":{"enabled":True,"keyColor":"#00FF00","similarity":.25,"blend":.08}}])
    probe=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(out)],capture_output=True,text=True,check=True)
    assert float(probe.stdout.strip())>=.9


def test_pip_and_three_layer_ffmpeg_render(tmp_path):
    blue=tmp_path/"blue.mp4"; red=tmp_path/"red.mp4"; _make_video(blue,"blue"); _make_video(red,"red")
    layers=[
        {"id":"b","assetPath":str(blue),"mediaType":"video","visible":True,"zOrder":2,"startMs":0,"durationMs":1000,"x":0,"y":0,"width":1,"height":1,"opacity":1,"fitMode":"fill","chromaKey":{}},
        {"id":"p","assetPath":str(red),"mediaType":"video","visible":True,"zOrder":3,"startMs":100,"durationMs":700,"x":.68,"y":.58,"width":.28,"height":.34,"opacity":.9,"fitMode":"contain","chromaKey":{}},
    ]
    out=_render(tmp_path,layers); assert out.exists()


def test_word_timing_edit_merge_split_and_frame_snap(tmp_path):
    from services.word_timing_service import WordTimingService
    db=DB(tmp_path/"words.sqlite")
    with db.connect() as c,c:
        c.executescript("""
        CREATE TABLE transcripts(id TEXT PRIMARY KEY,project_id TEXT);
        CREATE TABLE transcript_segments(id TEXT PRIMARY KEY,transcript_id TEXT,text TEXT,edited INTEGER,updated_at TEXT);
        CREATE TABLE transcript_words(id TEXT PRIMARY KEY,segment_id TEXT,word_order INTEGER,start_ms INTEGER,end_ms INTEGER,text TEXT,probability REAL,metadata_json TEXT);
        INSERT INTO transcripts VALUES('t','p'); INSERT INTO transcript_segments VALUES('s','t','Open AI works.',0,'n');
        INSERT INTO transcript_words VALUES('w1','s',0,0,400,'Open',.9,'{}');
        INSERT INTO transcript_words VALUES('w2','s',1,400,800,'AI',.9,'{}');
        INSERT INTO transcript_words VALUES('w3','s',2,800,1200,'works',.9,'{}');
        INSERT INTO transcript_words VALUES('w4','s',3,1200,1300,'.',.9,'{}');
        """)
    repo=SimpleNamespace(database=db); service=WordTimingService(repo)
    service.update_word('p','w1',text='OpenAI',end_ms=433,fps=30,snap_to_frame=True)
    assert service.words('p','s')[0].end_ms==433
    merged=service.merge('p','w1','w2'); assert 'OpenAI' in merged.text
    first,second=service.split('p','w3','work','s',split_ms=1000); assert first.end_ms==1000 and second.start_ms==1000
    with db.connect() as c: text=c.execute("SELECT text FROM transcript_segments WHERE id='s'").fetchone()[0]
    assert text.endswith('.') and 'work s' in text


def test_voice_resolution_priority_and_language_validation(tmp_path):
    from services.speaker_service import SpeakerService
    from domain.phase22_errors import VoiceLanguageMismatch
    repo=Phase22Repository(make_db(tmp_path))
    speaker=repo.save_speaker(SpeakerProfile(project_id='p1',name='Reporter',role='reporter',language='th',voice_id='speaker-voice'))
    class Voice:
        def __init__(self,i,engine='voxcpm2'): self.voice_id=i; self.engine_id=engine; self.name=i; self.language='en'
    class Voices:
        def get(self,i): return Voice(i,'unsupported' if i=='bad' else 'voxcpm2')
        def project_voice(self,p): return Voice('project-default')
    projects=SimpleNamespace(get_by_id=lambda p:object())
    service=SpeakerService(repo,projects,Voices(),LanguageService())
    block=SpeechBlock('sec1',0,'สวัสดี',language='th',speaker_id=speaker.id)
    voice,source=service.resolve_voice('p1',block); assert voice.voice_id=='speaker-voice' and source=='speaker'
    block.voice_override_id='override'; voice,source=service.resolve_voice('p1',block); assert voice.voice_id=='override' and source=='block_override'
    block.voice_override_id='bad'
    with pytest.raises(VoiceLanguageMismatch): service.resolve_voice('p1',block)


def test_speech_block_ordering_and_unicode_persistence(tmp_path):
    repo=Phase22Repository(make_db(tmp_path))
    a=repo.save_block('p1',SpeechBlock('sec1',0,'สวัสดี',language='th'))
    b=repo.save_block('p1',SpeechBlock('sec1',1,'Xin chào, hôm nay chúng ta sẽ nói về công nghệ mới.',language='vi'))
    assert [x.id for x in repo.blocks_for_section('sec1')]==[a.id,b.id]
    assert repo.blocks_for_section('sec1')[1].text.startswith('Xin chào')
