from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

import pytest

from domain.render_settings import RenderSettings
from domain.subtitle import SubtitleTrack
from domain.subtitle_cue import SubtitleCue
from domain.subtitle_style import SubtitleStyle
from media.ffmpeg import FFmpegRunner
from media.probe import FFprobeService
from rendering.encoder_registry import EncoderRegistry
from rendering.errors import RenderCancelled
from rendering.output_validator import OutputValidator
from rendering.render_plan import RenderPlan, expected_sequence_duration_ms
from rendering.renderer import FFmpegRenderer
from rendering.subtitle_renderer import SubtitleRenderer
from workers.cancellation import CancellationToken

pytestmark = pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="FFmpeg/FFprobe not available")


class StaticSubtitleService:
    def __init__(self, track, style, cues): self.values=(track,style,cues)
    def get(self, project_id, track_id): return self.values


def make_source_video(path: Path, duration: float = 2.0) -> None:
    subprocess.run([
        shutil.which("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", f"testsrc2=size=640x360:rate=30:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={duration}",
        "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(path),
    ], check=True)


def make_image(path: Path) -> None:
    from PIL import Image
    Image.new("RGBA", (640, 360), (32, 84, 145, 255)).save(path)


def runner_registry():
    runner=FFmpegRunner(shutil.which("ffmpeg")); caps=runner.discover_capabilities(); return runner, EncoderRegistry(runner,caps)


def test_real_ffmpeg_capabilities_include_software_baseline():
    runner, registry = runner_registry()
    assert registry.capabilities.has_encoder("libx264")
    assert registry.capabilities.has_encoder("aac")
    assert registry.capabilities.has_filter("subtitles") or registry.capabilities.has_filter("ass")
    assert runner.validate_encoder("libx264")


def test_real_basic_mixed_scene_render_with_crossfade_khmer_overlay(tmp_path: Path):
    image=tmp_path/"រូបភាព.png"; video=tmp_path/"clip video.mp4"; make_image(image); make_source_video(video)
    scene1={
        "sceneId":"s1","durationMs":1500,
        "visual":{"path":str(image),"mediaType":"image","fitMode":"fill","backgroundColor":"#000000","hasAudio":False},
        "audio":{"sourceAudioEnabled":False,"narrationEnabled":False},
        "overlays":[{"id":"o1","type":"headline","order":0,"visible":True,"text":"ព័ត៌មានថ្មីថ្ងៃនេះ","x":.1,"y":.15,"width":.8,"height":.2,"opacity":1.0,"startOffsetMs":0,"endOffsetMs":-1,"style":{"fontFamily":"Noto Sans Khmer","fontSize":50,"fontWeight":700,"color":"#FFFFFFFF"}}],
        "transitionIn":{"type":"cut","durationMs":0},"transitionOut":{"type":"crossfade","durationMs":300},
    }
    scene2={
        "sceneId":"s2","durationMs":1500,
        "visual":{"path":str(video),"mediaType":"video","fitMode":"fit","backgroundColor":"#111111","hasAudio":True,"sourceStartMs":0,"sourceEndMs":1500},
        "audio":{"sourceAudioEnabled":True,"sourceAudioVolume":.2,"narrationEnabled":False},
        "overlays":[],"transitionIn":{"type":"crossfade","durationMs":300},"transitionOut":{"type":"cut","durationMs":0},
    }
    settings=RenderSettings(320,180,30,"libx264","fast")
    scenes=[scene1,scene2]; expected=expected_sequence_duration_ms(scenes)
    plan=RenderPlan("p",str(tmp_path/"ចេញ video.mp4"),settings,scenes,expected,str(tmp_path/"render temp"))
    runner,registry=runner_registry(); result=FFmpegRenderer(runner,registry).render(plan)
    validation=OutputValidator(FFprobeService(lambda: shutil.which("ffprobe"))).validate(result.output_path,width=320,height=180,fps=30,expected_duration_ms=expected)
    assert result.encoder=="libx264" and validation.probe.audio_codec=="aac" and validation.duration_delta_ms<=250


def test_real_bilingual_subtitle_burn(tmp_path: Path):
    image=tmp_path/"image.png"; make_image(image)
    track=SubtitleTrack(project_id="p",name="English + Khmer",language="en",is_bilingual=True,secondary_language="km")
    style=SubtitleStyle(project_id="p",font_family="Noto Sans Khmer",font_size=36)
    cue=SubtitleCue(track_id=track.id,order=0,start_ms=100,end_ms=1400,text="Welcome to today's update.",secondary_text="សូមស្វាគមន៍មកកាន់ព័ត៌មានថ្ងៃនេះ។")
    subtitle=SubtitleRenderer(StaticSubtitleService(track,style,[cue]))
    scene={"sceneId":"s","durationMs":1600,"visual":{"path":str(image),"mediaType":"image","fitMode":"fill","backgroundColor":"#000000"},"audio":{},"overlays":[],"transitionIn":{},"transitionOut":{}}
    settings=RenderSettings(320,180,30,"libx264","fast",subtitle_track_id=track.id)
    plan=RenderPlan("p",str(tmp_path/"bilingual.mp4"),settings,[scene],1600,str(tmp_path/"tmp"),track.id)
    runner,registry=runner_registry(); result=FFmpegRenderer(runner,registry,subtitle).render(plan)
    probe=FFprobeService(lambda: shutil.which("ffprobe")).probe(result.output_path,"video")
    assert probe.width==320 and probe.height==180 and probe.duration_ms is not None


def test_real_ffmpeg_runner_cancellation_stops_process(tmp_path: Path):
    runner=FFmpegRunner(shutil.which("ffmpeg")); token=CancellationToken(); output=tmp_path/"partial.mp4"; caught=[]
    def work():
        try:
            runner.run(["-re","-f","lavfi","-i","testsrc2=size=320x180:rate=30:duration=20","-c:v","libx264","-preset","ultrafast",str(output)],expected_duration_ms=20000,cancellation=token)
        except Exception as exc:
            caught.append(exc)
    thread=threading.Thread(target=work); thread.start(); time.sleep(.35); token.cancel(); runner.cancel_active(); thread.join(timeout=8)
    assert not thread.is_alive() and caught


def test_detected_hardware_encoder_is_runtime_tested_or_skipped():
    runner,registry=runner_registry()
    candidates=[x.encoder_id for x in registry.list() if x.hardware and x.available]
    ready=[name for name in candidates if runner.validate_encoder(name)]
    if not ready: pytest.skip("FFmpeg lists hardware encoders but none are usable in this CI runtime")
    assert registry.resolve(ready[0],allow_fallback=False)==ready[0]


@pytest.mark.skipif(os.environ.get("SPVS_RUN_RENDER_PERFORMANCE") != "1", reason="Set SPVS_RUN_RENDER_PERFORMANCE=1 for the 60-second render performance check")
def test_opt_in_sixty_second_render_performance(tmp_path: Path):
    image=tmp_path/"image.png"; make_image(image)
    scene={"sceneId":"s","durationMs":60000,"visual":{"path":str(image),"mediaType":"image","fitMode":"fill","backgroundColor":"#000000"},"audio":{},"overlays":[],"transitionIn":{},"transitionOut":{}}
    settings=RenderSettings(640,360,30,"libx264","fast"); plan=RenderPlan("p",str(tmp_path/"60s.mp4"),settings,[scene],60000,str(tmp_path/"temp"))
    runner,registry=runner_registry(); started=time.monotonic(); result=FFmpegRenderer(runner,registry).render(plan); elapsed=time.monotonic()-started
    assert result.output_path.is_file() and elapsed>0


def test_real_render_service_history_restart_and_managed_delete(tmp_path: Path, monkeypatch):
    from PIL import Image
    from app.bootstrap import build_container
    from domain.media import MediaAsset, MediaType
    from services.project_service import ProjectService
    from services.render_service import RenderService
    from services.scene_service import SceneService
    from storage.repositories.media_repository import MediaRepository
    from storage.repositories.render_output_repository import RenderOutputRepository
    from storage.database import SQLiteDatabase

    monkeypatch.setenv("HOME", str(tmp_path / "home")); monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    container=build_container(); projects=container.resolve(ProjectService); project=projects.create_project("Render History","video","en","16:9",30)
    image=Path(project.project_path)/"media"/"images"/"cover.png"; image.parent.mkdir(parents=True,exist_ok=True); Image.new("RGB",(640,360),(70,30,110)).save(image)
    container.resolve(MediaRepository).create(MediaAsset(asset_id="img",project_id=project.id,media_type=MediaType.IMAGE,name="cover.png",original_path=str(image),project_path=str(image),file_size=image.stat().st_size,width=640,height=360,extension=".png"))
    scenes=container.resolve(SceneService); scene=scenes.add_scene(project.id,"Intro",1000); scenes.assign_media(project.id,scene.id,"img")
    renders=container.resolve(RenderService); output=renders.render(project.id,RenderSettings(320,180,30,"libx264","fast"))
    assert Path(output.file_path).is_file() and renders.history(project.id)[0].id==output.id
    reopened=RenderOutputRepository(SQLiteDatabase(container.resolve(SQLiteDatabase).path))
    assert reopened.get(output.id).file_path==output.file_path
    renders.delete_output(project.id,output.id)
    assert not Path(output.file_path).exists() and reopened.get(output.id) is None
