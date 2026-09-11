from __future__ import annotations

from pathlib import Path

import pytest

from app.bootstrap import build_container
from services.export_service import ExportService
from services.project_service import ProjectService
from services.scene_service import SceneService
from services.subtitle_service import SubtitleService
from storage.repositories.render_output_repository import RenderOutputRepository
from media.probe import FFprobeService

pytestmark=[pytest.mark.integration]


def make_project(tmp_path:Path,monkeypatch,*,aspect="16:9",language="en"):
    monkeypatch.setenv("HOME",str(tmp_path/"home")); monkeypatch.setenv("XDG_DATA_HOME",str(tmp_path/"xdg"))
    c=build_container(); p=c.resolve(ProjectService).create_project("ព័ត៌មាន Export Integration","video",language,aspect,30)
    scenes=c.resolve(SceneService); scene=scenes.add_scene(p.id,"Scene",700); scenes.update_general(p.id,scene.id,background_color="#14213d")
    return c,p


def probe(c,path:Path):
    render=c.resolve(ExportService).render_service
    ffprobe=render.ffprobe_provider()
    return FFprobeService(lambda:ffprobe).probe(path)


def test_real_tiktok_and_youtube_exports(tmp_path:Path,monkeypatch):
    c,p=make_project(tmp_path,monkeypatch); service=c.resolve(ExportService)
    outdir=tmp_path/"exports"; outdir.mkdir()
    t=service.default_request(p.id,"tiktok"); t.output_folder=str(outdir);t.filename="tiktok.mp4";t.encoder="libx264";t.quality="fast";t.audio_enabled=False
    a=service.export(t); pa=probe(c,Path(a.file_path)); assert (pa.width,pa.height)==(1080,1920) and not pa.audio_codec
    y=service.default_request(p.id,"youtube");y.output_folder=str(outdir);y.filename="youtube.mp4";y.encoder="libx264";y.quality="fast";y.audio_enabled=False
    b=service.export(y);pb=probe(c,Path(b.file_path));assert (pb.width,pb.height)==(1920,1080) and Path(b.file_path).is_file()


def test_real_khmer_subtitle_and_unicode_export_path(tmp_path:Path,monkeypatch):
    c,p=make_project(tmp_path,monkeypatch,aspect="9:16",language="km"); subtitles=c.resolve(SubtitleService)
    track=subtitles.create_manual(p.id,"km",name="ខ្មែរ"); subtitles.add_cue(p.id,track.id,0,"ព័ត៌មានថ្មីថ្ងៃនេះ",duration_ms=650); subtitles.set_default(p.id,track.id)
    folder=tmp_path/"វីដេអូ ចេញ"; folder.mkdir(); service=c.resolve(ExportService); req=service.default_request(p.id,"tiktok");req.output_folder=str(folder);req.filename="ព័ត៌មានថ្មី.mp4";req.encoder="libx264";req.quality="fast";req.audio_enabled=False;req.subtitle_mode="burn";req.subtitle_track_id=track.id
    output=service.export(req); assert Path(output.file_path).is_file() and "ព័ត៌មានថ្មី" in Path(output.file_path).name
    info=probe(c,Path(output.file_path)); assert (info.width,info.height)==(1080,1920)


def test_real_external_srt_and_keep_both_conflict(tmp_path:Path,monkeypatch):
    c,p=make_project(tmp_path,monkeypatch,language="km"); subtitles=c.resolve(SubtitleService);track=subtitles.create_manual(p.id,"km",name="Khmer");subtitles.add_cue(p.id,track.id,0,"សួស្តី",duration_ms=650)
    service=c.resolve(ExportService);folder=tmp_path/"out";folder.mkdir();req=service.default_request(p.id,"youtube");req.width=320;req.height=180;req.output_folder=str(folder);req.filename="same.mp4";req.encoder="libx264";req.quality="fast";req.audio_enabled=False;req.subtitle_mode="external_srt";req.subtitle_track_id=track.id
    first=service.export(req); assert Path(first.file_path).is_file(); extras=first.metadata.get("subtitleExportFiles",[]);assert extras and Path(extras[0]).read_text(encoding="utf-8").find("សួស្តី")>=0
    req2=service.default_request(p.id,"youtube");req2.width=320;req2.height=180;req2.output_folder=str(folder);req2.filename="same.mp4";req2.encoder="libx264";req2.quality="fast";req2.audio_enabled=False;req2.overwrite_policy="keep_both"
    second=service.export(req2);assert Path(second.file_path).name=="same_2.mp4"


def test_export_history_survives_container_restart(tmp_path:Path,monkeypatch):
    c,p=make_project(tmp_path,monkeypatch);service=c.resolve(ExportService);req=service.default_request(p.id,"youtube");req.width=320;req.height=180;req.output_folder=str(Path(p.project_path)/"renders");req.filename="restart.mp4";req.encoder="libx264";req.quality="fast";req.audio_enabled=False
    output=service.export(req); output_id=output.id
    # New container over the same app data simulates a restart; the persisted project/render rows remain.
    c2=build_container(); rows=c2.resolve(RenderOutputRepository).list_for_project(p.id,20)
    assert any(x.id==output_id and Path(x.file_path).is_file() for x in rows)
    restored=c2.resolve(ExportService).request_from_output(p.id,output_id); assert restored.preset_id=="youtube"
