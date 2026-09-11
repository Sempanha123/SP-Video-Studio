from __future__ import annotations

import contextlib
import sqlite3
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from domain.short_candidate import ShortCandidate
from domain.short_project import ShortProject
from domain.short_segment import ShortSegment
from domain.shorts_errors import ShortInvalidRange
from rendering.layer_compositor import build_layered_scene_command
from services.short_candidate_service import ShortCandidateService
from services.short_caption_service import CaptionGrouping, ShortCaptionService
from services.short_reframe_service import ShortReframeService
from services.short_validation_service import ShortsValidationService
from storage.migrations.m020_create_shorts import migrate
from storage.repositories.short_repository import ShortRepository


class DB:
    def __init__(self, path): self.path=Path(path)
    @contextlib.contextmanager
    def connect(self):
        c=sqlite3.connect(self.path); c.row_factory=sqlite3.Row; c.execute("PRAGMA foreign_keys=ON")
        try: yield c
        finally: c.close()


def make_db(tmp_path):
    db=DB(tmp_path/"phase23.sqlite")
    with db.connect() as c,c:
        c.execute("CREATE TABLE projects(id TEXT PRIMARY KEY)")
        c.execute("INSERT INTO projects(id) VALUES('p1'),('p2')")
        migrate(c)
    return db


class FakeMedia:
    def __init__(self, root: Path):
        self.path=root/"source.mp4"; self.path.write_bytes(b"media")
        self.asset=SimpleNamespace(id="m1",project_id="p1",type="video",duration_ms=300_000,width=1920,height=1080,
                                   project_path=str(self.path),name="source.mp4",original_path="/original/source.mp4",file_size=5)
    def get_by_id(self, value): return self.asset if value=="m1" else None
    def list_by_project(self, project_id): return [self.asset] if project_id=="p1" else []


class Word:
    def __init__(self, text, start, end): self.text=text; self.start_ms=start; self.end_ms=end; self.probability=.95


class Segment:
    def __init__(self, sid, order, start, end, text, words=()):
        self.id=sid; self.order=order; self.start_ms=start; self.end_ms=end; self.text=text; self.words=list(words)


class FakeTranscripts:
    def __init__(self):
        self.transcript=SimpleNamespace(id="t1",project_id="p1",media_id="m1",detected_language="th",language_mode="auto",updated_at="u1")
        self.items=[
            Segment("s1",0,0,900,"สวัสดี",[Word("สวัสดี",0,900)]),
            Segment("s2",1,1200,2200,"วันนี้",[Word("วันนี้",1200,2200)]),
            Segment("s3",2,2600,3900,"เทคโนโลยีใหม่",[Word("เทคโนโลยี",2600,3300),Word("ใหม่",3300,3900)]),
            Segment("s4",3,5200,6400,"Xin chào",[Word("Xin",5200,5650),Word(" chào",5650,6400)]),
        ]
    def get(self, value): return self.transcript if value=="t1" else None
    def segments(self, value): return list(self.items) if value=="t1" else []
    def list_for_project(self, value): return [self.transcript] if value=="p1" else []


class FakeScenes:
    def __init__(self):
        self.items=[
            SimpleNamespace(id="scene1",project_id="p1",order=0,duration_ms=5000,source_start_ms=1000,source_end_ms=6000,primary_media_id="m1",updated_at="u1",metadata={}),
            SimpleNamespace(id="scene2",project_id="p1",order=1,duration_ms=4000,source_start_ms=8000,source_end_ms=12000,primary_media_id="m1",updated_at="u2",metadata={}),
        ]
    def list_for_project(self, value): return list(self.items) if value=="p1" else []
    def list_enabled(self, value): return self.list_for_project(value)
    def get(self, scene_id): return next((x for x in self.items if x.id==scene_id),None)
    def update(self, scene): return scene


def service_set(tmp_path):
    repo=ShortRepository(make_db(tmp_path)); media=FakeMedia(tmp_path); transcripts=FakeTranscripts(); scenes=FakeScenes()
    return repo,media,transcripts,scenes,ShortCandidateService(repo,media,transcripts,scenes)


def test_short_metadata_unicode_and_platform_registry(tmp_path):
    repo,_,_,_,_=service_set(tmp_path)
    item=ShortProject("p1",language="th",platform="future_platform",metadata={"title":"สวัสดี · Xin chào · ខ្មែរ"})
    repo.save_project(item)
    reopened=ShortRepository(DB(repo.database.path)).get_project("p1")
    assert reopened.language=="th" and "Xin chào" in reopened.metadata["title"]


def test_manual_in_out_candidate_and_invalid_range(tmp_path):
    repo,_,_,_,service=service_set(tmp_path)
    item=service.create_manual("p1","m1",30_000,60_000,title="Manual")
    assert item.duration_ms==30_000 and repo.segments(item.id)[0].source_start_ms==30_000
    with pytest.raises(ShortInvalidRange): service.create_manual("p1","m1",10_000,10_000)


def test_multi_range_ripple_assembly(tmp_path):
    repo,_,_,_,service=service_set(tmp_path)
    item=service.create_multi_range("p1","m1",[{"startMs":30_000,"endMs":36_000},{"startMs":130_000,"endMs":150_000},{"startMs":240_000,"endMs":248_000}])
    segments=repo.segments(item.id)
    assert [x.duration_ms for x in segments]==[6000,20000,8000]
    assert item.metadata["assembledDurationMs"]==34_000 and item.metadata["rippleGapsRemoved"] is True


def test_transcript_selection_and_outdated_detection(tmp_path):
    repo,_,transcripts,_,service=service_set(tmp_path)
    item=service.create_from_transcript("p1","t1",["s1","s2","s3"])
    assert item.start_ms==0 and item.end_ms==3900 and item.language=="th"
    assert service.mark_outdated_if_changed(item.id) is False
    transcripts.items[1].text="วันนี้แก้ไข"
    assert service.mark_outdated_if_changed(item.id) is True
    assert repo.get_candidate(item.id).status_code=="outdated"


def test_deterministic_suggestions_do_not_store_fake_scores(tmp_path):
    _,_,_,_,service=service_set(tmp_path)
    suggestions=service.suggest_from_transcript("p1","t1",3000,limit=2)
    assert suggestions and all(x.metadata.get("suggested") for x in suggestions)
    assert all(x.score_metadata=={"selection":"suggested","basis":"transcript_boundaries"} for x in suggestions)
    bad=ShortCandidate("p1","video","m1","Bad",0,1000,score_metadata={"viral_score":95})
    with pytest.raises(ValueError): bad.validate()


def test_scene_selection_preserves_language_and_order(tmp_path):
    repo,_,_,_,service=service_set(tmp_path)
    item=service.create_from_scenes("p1",["scene2","scene1"],language="vi",source_type="story")
    assert item.language=="vi" and item.source_type_code=="story"
    assert [x.source_entity_id for x in repo.segments(item.id)]==["scene1","scene2"]


def test_silence_suggestions_are_non_destructive(tmp_path):
    _,_,_,_,service=service_set(tmp_path)
    rows=service.silence_suggestions("t1",threshold_ms=1000)
    assert rows==[{"startMs":3900,"endMs":5200,"durationMs":1300}]


def test_candidate_duplication_and_restart_persistence(tmp_path):
    repo,_,_,_,service=service_set(tmp_path)
    source=service.create_manual("p1","m1",0,5000,title="A")
    clone=repo.duplicate_candidate("p1",source.id)
    assert clone.id!=source.id and repo.segments(clone.id)[0].id!=repo.segments(source.id)[0].id
    reopened=ShortRepository(DB(repo.database.path)); assert reopened.get_candidate(clone.id).title=="A Copy"


def test_duplicate_source_remapping_removes_writable_source_ids(tmp_path):
    repo,_,_,_,service=service_set(tmp_path)
    c=service.create_from_scenes("p1",["scene1"],source_type="news")
    mapping=repo.duplicate_project("p1","p2")
    repo.remap_duplicate_sources("p1","p2",mapping,media_map={"m1":"m2"},scene_map={"scene1":"sceneX"})
    copied=repo.get_candidate(mapping[c.id])
    assert copied.source_id=="p2" and copied.source_entity_ids==["sceneX"]
    assert repo.segments(copied.id)[0].source_entity_id=="sceneX"


def test_reframe_presets_and_crop_persistence():
    scenes=FakeScenes(); service=ShortReframeService(scenes)
    data=service.apply_preset("p1","scene1","right",scale=1.3)
    assert data["offsetX"]==1.0 and data["scale"]==1.3
    custom=service.set("p1","scene1",scale=1.2,crop_left=.1,crop_right=.05,fit_mode="fill")
    assert custom["cropLeft"]==.1 and service.get("p1","scene1")["cropRight"]==.05


def test_language_aware_caption_grouping_thai_vietnamese():
    service=ShortCaptionService(SimpleNamespace(),SimpleNamespace(),SimpleNamespace())
    thai=[Word("สวัสดี",0,400),Word("วันนี้",400,800),Word("เทคโนโลยี",800,1400),Word("ใหม่",1400,1700)]
    groups=service.group_words(thai,"th",CaptionGrouping(max_words=2,max_chars=50,max_duration_ms=2000))
    assert groups[0]["text"]=="สวัสดีวันนี้" and len(groups)==2
    vi=[Word("Xin",0,300),Word(" chào,",300,600),Word(" hôm",600,900),Word(" nay",900,1200)]
    assert service.group_words(vi,"vi",CaptionGrouping(max_words=4,max_chars=50,max_duration_ms=2000))[0]["text"]=="Xin chào, hôm nay"


def test_caption_multi_range_timing_uses_real_words(tmp_path):
    repo,_,transcripts,_,candidate_service=service_set(tmp_path)
    candidate=candidate_service.create_from_transcript("p1","t1",["s1","s2","s3"])
    cap=ShortCaptionService(repo,transcripts,SimpleNamespace())
    rows=cap.build_candidate_cues(candidate.id,max_words=2)
    assert rows[0]["startMs"]==0 and rows[-1]["endMs"]<=candidate.duration_ms
    assert all(row["words"] for row in rows)


def test_validation_reports_target_warning_without_auto_cut(tmp_path):
    repo,media,_,scenes,service=service_set(tmp_path)
    candidate=service.create_manual("p1","m1",0,73_000,target_duration_ms=60_000)
    validation=ShortsValidationService(repo,media,scenes,None)
    issues=validation.validate_candidate(candidate.id,target_duration_ms=60_000)
    assert any(x.code=="over_target" for x in issues) and repo.get_candidate(candidate.id).end_ms==73_000


class Caps: filters=frozenset({"chromakey","colorkey"})
class Runner:
    def discover_capabilities(self): return Caps()
class Overlay:
    def write_ass(self,*args,**kwargs): return None
class Renderer:
    runner=Runner(); overlay_renderer=Overlay(); fonts_dir=None
class Settings:
    width=180; height=320; fps=30


def test_actual_ffmpeg_vertical_reframe_render(tmp_path):
    source=tmp_path/"landscape.mp4"; out=tmp_path/"short.nut"
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","lavfi","-i","testsrc2=s=640x360:r=30:d=1","-an","-c:v","libx264","-pix_fmt","yuv420p",str(source)],check=True)
    spec={"sceneId":"s","durationMs":1000,"visual":{"path":str(source),"mediaType":"video","fitMode":"fill","backgroundColor":"#000000","reframe":{"scale":1.1,"offsetX":1.0,"offsetY":0.0,"fitMode":"fill"}},"audio":{},"layers":[],"overlays":[],"transitionIn":{},"transitionOut":{}}
    args=build_layered_scene_command(Renderer(),lambda *a,**k: (_ for _ in ()).throw(AssertionError("must use compositor")),spec,Settings(),out,temp_dir=tmp_path)
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",*args],check=True)
    probe=subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","csv=s=x:p=0",str(out)],capture_output=True,text=True,check=True)
    assert probe.stdout.strip()=="180x320"


def test_phase23_ui_is_existing_timeline_extension():
    root=Path(__file__).resolve().parents[1]
    timeline=(root/"ui/qml/timeline/TimelineEditor.qml").read_text(encoding="utf-8")
    studio=(root/"ui/qml/shorts/ShortsStudio.qml").read_text(encoding="utf-8")
    assert "ShortsStudio" in timeline and "UniversalVideoPanel" in timeline
    assert "viral score" not in studio.lower()
    assert not (root/"rendering/short_renderer.py").exists()


def test_actual_dub_range_audio_assembly(tmp_path):
    from services.short_audio_service import ShortAudioService
    source=tmp_path/"dub.wav"; out=tmp_path/"short-dub.wav"
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","lavfi","-i","sine=frequency=440:sample_rate=48000:duration=4","-c:a","pcm_s16le",str(source)],check=True)
    segments=[ShortSegment("c",0,0,1000,"m"),ShortSegment("c",1,2500,3500,"m")]
    ShortAudioService(lambda:"ffmpeg").assemble(source,segments,out)
    probe=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(out)],capture_output=True,text=True,check=True)
    assert 1.95 <= float(probe.stdout.strip()) <= 2.05


def test_subtitle_range_trim_preserves_real_word_timing():
    from services.short_subtitle_range_service import ShortSubtitleRangeService
    cue=SimpleNamespace(cue_id="q",id="q",order=0,start_ms=1000,end_ms=3000,text="Hello",metadata={},words=[SimpleNamespace(word_id="w",start_ms=1200,end_ms=1600,text="Hello")])
    track=SimpleNamespace(id="track")
    class Repo:
        def replace_cues(self,project_id,track_id,cues): self.cues=cues
    class Subs:
        def __init__(self): self.repository=Repo()
        def list_tracks(self,p): return [track]
        def get(self,p,t): return track,None,[cue]
    subs=Subs(); service=ShortSubtitleRangeService(subs)
    count=service.trim_project_tracks("p",[ShortSegment("c",0,1000,2000,"m")])
    assert count==1 and subs.repository.cues[0].start_ms==0 and subs.repository.cues[0].end_ms==1000
    assert subs.repository.cues[0].words[0].start_ms==200 and subs.repository.cues[0].words[0].end_ms==600


def test_silence_removal_uses_command_backed_timeline_edits():
    from services.shorts_service import ShortsService
    scene=SimpleNamespace(id="s",duration_ms=5000)
    class Edits:
        def __init__(self): self.splits=[]; self.deleted=[]; self.scenes=SimpleNamespace(get=lambda p,s:(scene,[],[]))
        def split_scene(self,p,s,local): self.splits.append((s,local)); return "new"
        def delete_scene(self,p,s): self.deleted.append(s)
    edits=Edits()
    timeline=SimpleNamespace(
        project_to_scene_time=lambda p,pos:("s",pos),
        edits=edits,
        mapping=SimpleNamespace(scene_ranges=lambda p:[{"sceneId":"middle","startMs":1000,"endMs":2000}]),
    )
    projects=SimpleNamespace(get_by_id=lambda p:SimpleNamespace(workflow="shorts"))
    service=ShortsService(SimpleNamespace(),projects,SimpleNamespace(),SimpleNamespace(),SimpleNamespace(),SimpleNamespace(),timeline_service=timeline)
    assert service.apply_silence_removal("p",1000,2000)==1000
    assert edits.splits==[("s",2000),("s",1000)] and edits.deleted==["middle"]
