from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from app.bootstrap import build_container
from domain.media import MediaAsset, MediaType
from domain.render_settings import RenderSettings
from media.probe import FFprobeService
from services.project_service import ProjectService
from services.render_service import RenderService
from services.scene_service import SceneService
from services.timeline_service import TimelineService
from storage.repositories.media_repository import MediaRepository

pytestmark=pytest.mark.skipif(not (shutil.which('ffmpeg') and shutil.which('ffprobe')),reason='FFmpeg/FFprobe not available')


def make_color(path:Path,rgb:tuple[int,int,int]):
    from PIL import Image
    Image.new('RGB',(320,180),rgb).save(path)


def make_two_color_video(path:Path):
    subprocess.run([
        shutil.which('ffmpeg'),'-hide_banner','-loglevel','error','-y',
        '-f','lavfi','-i','color=c=red:size=320x180:rate=30:duration=2',
        '-f','lavfi','-i','color=c=blue:size=320x180:rate=30:duration=2',
        '-filter_complex','[0:v][1:v]concat=n=2:v=1:a=0[v]','-map','[v]','-c:v','libx264','-pix_fmt','yuv420p',str(path)
    ],check=True)


def frame_at(path:Path,out:Path,seconds:float):
    subprocess.run([shutil.which('ffmpeg'),'-hide_banner','-loglevel','error','-y','-ss',str(seconds),'-i',str(path),'-frames:v','1',str(out)],check=True)
    from PIL import Image
    image=Image.open(out).convert('RGB'); return image.getpixel((image.width//2,image.height//2))


def test_timeline_reorder_trim_split_render_regression(tmp_path:Path,monkeypatch):
    monkeypatch.setenv('HOME',str(tmp_path/'home')); monkeypatch.setenv('XDG_DATA_HOME',str(tmp_path/'xdg'))
    c=build_container(); projects=c.resolve(ProjectService); project=projects.create_project('Timeline Render','video','en','16:9',30)
    repo=c.resolve(MediaRepository); root=Path(project.project_path)
    green=root/'media'/'images'/'green.png'; green.parent.mkdir(parents=True,exist_ok=True); make_color(green,(0,210,0))
    red=root/'media'/'images'/'red.png'; make_color(red,(210,0,0))
    video=root/'media'/'video'/'two-color.mp4'; video.parent.mkdir(parents=True,exist_ok=True); make_two_color_video(video)
    repo.create(MediaAsset(asset_id='green',project_id=project.id,media_type=MediaType.IMAGE,name='green.png',original_path=str(green),project_path=str(green),file_size=green.stat().st_size,width=320,height=180,extension='.png'))
    repo.create(MediaAsset(asset_id='red',project_id=project.id,media_type=MediaType.IMAGE,name='red.png',original_path=str(red),project_path=str(red),file_size=red.stat().st_size,width=320,height=180,extension='.png'))
    repo.create(MediaAsset(asset_id='video',project_id=project.id,media_type=MediaType.VIDEO,name='two-color.mp4',original_path=str(video),project_path=str(video),file_size=video.stat().st_size,duration_ms=4000,width=320,height=180,fps=30,codec='h264',extension='.mp4'))
    scenes=c.resolve(SceneService); timeline=c.resolve(TimelineService)
    a=scenes.add_scene(project.id,'Red',1000); scenes.assign_media(project.id,a.id,'red')
    b=scenes.add_scene(project.id,'Video',4000); scenes.assign_media(project.id,b.id,'video'); scenes.set_video_range(project.id,b.id,0,4000)
    g=scenes.add_scene(project.id,'Green',1000); scenes.assign_media(project.id,g.id,'green')
    # Reorder green before red; trim video from left to keep only its blue half; split red into two scenes.
    timeline.edits.reorder_scene(project.id,g.id,0)
    timeline.edits.trim_scene_left(project.id,b.id,2000)
    red2=timeline.edits.split_scene(project.id,a.id,500)
    assert [x.name for x in scenes.list_scenes(project.id)][:2]==['Green','Red']
    assert scenes.get(project.id,b.id)[0].source_start_ms==2000
    assert scenes.get(project.id,red2)[0].duration_ms==500
    expected=timeline.duration_ms(project.id); assert expected==4000
    output=c.resolve(RenderService).render(project.id,RenderSettings(320,180,30,'libx264','fast'))
    probe=FFprobeService(lambda:shutil.which('ffprobe')).probe(Path(output.file_path),'video')
    assert abs((probe.duration_ms or 0)-expected)<=250
    rgb=frame_at(Path(output.file_path),tmp_path/'first.png',0.15)
    assert rgb[1]>rgb[0] and rgb[1]>rgb[2]  # reordered green scene is first in actual output
    blue=frame_at(Path(output.file_path),tmp_path/'trimmed.png',2.5)
    assert blue[2]>blue[0] and blue[2]>blue[1]  # 2–4s source trim reaches the blue half
