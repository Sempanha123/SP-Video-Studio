from __future__ import annotations

import json
import math
import shutil
import sqlite3
import subprocess
import wave
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.paths import AppPaths
from domain.audio_bus import AudioBus
from domain.audio_clip import AudioClip
from domain.audio_effect import AudioEffectSpec
from domain.audio_mix import AudioMixSettings
from domain.audio_track import AudioTrack
from domain.ducking_rule import DuckingRule
from domain.storage_category import StorageCategory, StorageSafety, definition
from rendering.render_plan import RenderPlan
from services.audio_analysis_service import AudioAnalysisService
from services.audio_ducking_service import AudioDuckingService, db_to_linear
from services.audio_mixer_service import AudioMixerService, linear_to_db
from services.audio_render_service import AudioRenderService
from services.audio_validation_service import AudioValidationService
from services.audio_waveform_service import AudioWaveformService
from services.cache_service import CacheService
from storage.database import SQLiteDatabase
from storage.migrations.m025_create_audio_mixer import migrate as migrate_audio
from storage.repositories.audio_mix_repository import AudioMixRepository

FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")

class _Caps:
    def __init__(self, filters): self.filters=frozenset(filters)

class FFmpegRunner:
    def __init__(self, path): self.path=str(path)
    def discover_capabilities(self):
        done=subprocess.run([self.path,"-hide_banner","-filters"],capture_output=True,text=True,check=False)
        filters=set()
        for line in done.stdout.splitlines():
            parts=line.split()
            if len(parts)>=2 and len(parts[0])==3: filters.add(parts[1])
        return _Caps(filters)
    def run(self,args,**kwargs):
        cmd=[self.path,"-hide_banner","-loglevel","error","-y",*args]
        done=subprocess.run(cmd,capture_output=True,text=True,check=False)
        if done.returncode != 0: raise RuntimeError(done.stderr[-2000:])


def make_paths(tmp_path: Path) -> AppPaths:
    root = tmp_path / "MMOVideoStudio"
    paths = AppPaths(root=root, models=root/"models", cache=root/"cache", temp=root/"temp", logs=root/"logs", settings=root/"settings", downloads=root/"downloads")
    paths.ensure()
    return paths


def repo_for(tmp_path: Path, *projects: str) -> AudioMixRepository:
    path = tmp_path / "mix.sqlite"
    raw = sqlite3.connect(path)
    try:
        raw.execute("PRAGMA foreign_keys=ON")
        raw.execute("CREATE TABLE projects(id TEXT PRIMARY KEY)")
        for project in projects or ("p1",):
            raw.execute("INSERT INTO projects(id) VALUES(?)", (project,))
        migrate_audio(raw)
        raw.commit()
    finally:
        raw.close()
    return AudioMixRepository(SQLiteDatabase(path))


def mixer_for(tmp_path: Path, *projects: str) -> tuple[AudioMixRepository, AudioMixerService]:
    repo = repo_for(tmp_path, *(projects or ("p1",)))
    return repo, AudioMixerService(repo)


def tone_wav(path: Path, *, hz: float = 440.0, seconds: float = 1.0, rate: int = 48000, gain: float = 0.2, channels: int = 1) -> Path:
    import struct
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(rate * seconds)
    with wave.open(str(path), "wb") as out:
        out.setnchannels(channels); out.setsampwidth(2); out.setframerate(rate)
        for i in range(frames):
            value = int(32767 * gain * math.sin(2 * math.pi * hz * i / rate))
            sample = struct.pack("<h", value)
            out.writeframesraw(sample * channels)
    return path


def ffmpeg_convert(source: Path, target: Path, extra: list[str] | None = None) -> Path:
    if not FFMPEG:
        pytest.skip("ffmpeg unavailable")
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(source), *(extra or []), str(target)]
    subprocess.run(cmd, check=True, capture_output=True)
    return target


def basic_spec(tmp_path: Path, *, duration_ms=2000) -> dict:
    a = tone_wav(tmp_path/"voice.wav", hz=440, seconds=1.0)
    b = tone_wav(tmp_path/"music.wav", hz=220, seconds=2.0)
    return {
        "projectId":"p1", "durationMs":duration_ms,
        "buses":[
            {"id":"bv","role":"voice","gainDb":0.0,"muted":False},
            {"id":"bm","role":"music","gainDb":0.0,"muted":False},
        ],
        "tracks":[
            {"id":"tv","name":"Voice","role":"voice","gainDb":0.0,"pan":0.0,"muted":False,"solo":False,"enabled":True,"busId":"bv"},
            {"id":"tm","name":"Music","role":"music","gainDb":-18.0,"pan":0.0,"muted":False,"solo":False,"enabled":True,"busId":"bm"},
        ],
        "clips":[
            {"id":"cv","trackId":"tv","sourcePath":str(a),"timelineStartMs":0,"durationMs":1000,"sourceInMs":0,"gainDb":0.0,"pan":0.0,"fadeInMs":0,"fadeOutMs":0,"muted":False},
            {"id":"cm","trackId":"tm","sourcePath":str(b),"timelineStartMs":0,"durationMs":2000,"sourceInMs":0,"gainDb":0.0,"pan":0.0,"fadeInMs":0,"fadeOutMs":0,"muted":False},
        ],
        "effects":[], "duckingRules":[],
        "master":{"masterGainDb":0.0,"limiterEnabled":True,"limiterLimit":0.95,"normalizationEnabled":False,"normalizationTargetLufs":-16.0},
    }


def test_audio_track_model_and_gain_pan_validation():
    item=AudioTrack("p1","Voice","voice",gain_db=-6,pan=.5); item.validate(); assert item.to_dict()["gainDb"] == -6
    with pytest.raises(ValueError): AudioTrack("p1","Bad","voice",gain_db=30).validate()
    with pytest.raises(ValueError): AudioTrack("p1","Bad","voice",pan=2).validate()


def test_audio_bus_and_master_models():
    bus=AudioBus("p1","Voice Bus","voice",gain_db=-3); bus.validate()
    master=AudioMixSettings("p1",master_gain_db=-1,limiter_enabled=True); master.validate(); assert master.limiter_enabled


def test_audio_clip_gain_fades_and_language():
    clip=AudioClip("c","p1","t","x.wav",0,4000,gain_db=-4,pan=-.2,fade_in_ms=1000,fade_out_ms=1000,speaker_name="អ្នករាយការណ៍",language="km")
    clip.validate(); assert clip.to_dict()["speakerName"] == "អ្នករាយការណ៍"


def test_repository_restart_persistence(tmp_path):
    repo,mixer=mixer_for(tmp_path,"p1")
    mixer.ensure_project("p1","news")
    voice=mixer.track_for_role("p1","voice"); mixer.update_track("p1",voice.id,gainDb=-7.5,pan=.2,muted=True,solo=True)
    mixer.update_master("p1",masterGainDb=-2,limiterEnabled=True,normalizationEnabled=True,normalizationTargetLufs=-18)
    repo2=AudioMixRepository(repo.database)
    saved=repo2.track("p1",voice.id); master=repo2.mix_settings("p1")
    assert (saved.gain_db,saved.pan,saved.muted,saved.solo)==(-7.5,.2,True,True)
    assert master.master_gain_db == -2 and master.normalization_target_lufs == -18


def test_default_workflow_tracks_and_buses(tmp_path):
    repo,mixer=mixer_for(tmp_path,"p1")
    state=mixer.ensure_project("p1","news")
    roles={x["role"] for x in state["tracks"]}; busroles={x["role"] for x in state["buses"]}
    assert {"voice","dialogue","source_audio","broll_audio","music","sfx"} <= roles
    assert {"voice","music","sfx","source"} <= busroles
    broll=next(x for x in state["tracks"] if x["role"]=="broll_audio"); assert broll["muted"] is True


def test_track_gain_mute_solo_and_multi_solo(tmp_path):
    _,m=mixer_for(tmp_path,"p1"); m.ensure_project("p1","video")
    voice=m.track_for_role("p1","voice"); music=m.track_for_role("p1","music")
    m.update_track("p1",voice.id,gainDb=-3,muted=True,solo=True); m.update_track("p1",music.id,solo=True)
    state=m.state("p1"); rows={x["role"]:x for x in state["tracks"]}
    assert rows["voice"]["gainDb"]==-3 and rows["voice"]["muted"] and rows["voice"]["solo"] and rows["music"]["solo"]


def test_clip_mix_gain_pan_fades_persist(tmp_path):
    repo,m=mixer_for(tmp_path,"p1"); m.ensure_project("p1")
    track=m.track_for_role("p1","voice")
    row=m.set_clip_mix("p1","clip1",trackId=track.id,gainDb=-5,pan=-.5,fadeInMs=250,fadeOutMs=400,muted=True)
    assert (row["gainDb"],row["pan"],row["fadeInMs"],row["fadeOutMs"],row["muted"])==(-5,-.5,250,400,True)
    assert repo.clip_mix("p1","clip1")["trackId"]==track.id


def test_crossfade_equal_power_metadata(tmp_path):
    _,m=mixer_for(tmp_path,"p1")
    a={"timelineStartMs":0,"durationMs":3000,"fadeOutMs":0}; b={"timelineStartMs":2500,"durationMs":3000,"fadeInMs":0}
    x,y=m.apply_crossfade(a,b,equal_power=True)
    assert x["fadeOutMs"]==500 and y["fadeInMs"]==500 and x["metadata"]["crossfade"]=="equal_power"


def test_track_routing_to_expected_buses(tmp_path):
    _,m=mixer_for(tmp_path,"p1"); state=m.ensure_project("p1","story")
    buses={b["id"]:b["role"] for b in state["buses"]}
    for t in state["tracks"]:
        if t["role"] in {"narration","dialogue"}: assert buses[t["busId"]]=="voice"
        if t["role"]=="music": assert buses[t["busId"]]=="music"
        if t["role"] in {"sfx","ambience"}: assert buses[t["busId"]]=="sfx"


def test_effect_order_bypass_and_voice_presets(tmp_path):
    repo,m=mixer_for(tmp_path,"p1"); m.ensure_project("p1"); track=m.track_for_role("p1","voice")
    effects=m.add_voice_effect_preset("p1",track.id,"clear_voice"); assert [x.type_code for x in effects]==["high_pass","eq"]
    m.update_effect("p1",effects[0].id,enabled=False)
    rows=repo.effects("p1","track",track.id); assert rows[0].enabled is False and rows[1].order > rows[0].order


def test_ducking_regions_and_expression():
    service=AudioDuckingService(); tracks={"v":{"busId":"bv"},"m":{"busId":"bm"}}
    clips=[{"trackId":"v","timelineStartMs":5000,"durationMs":5000,"muted":False}]
    regions=service.trigger_regions(clips,trigger_kind="bus",trigger_id="bv",tracks=tracks); assert regions==[(5000,10000)]
    expr=service.volume_expression({"duckAmountDb":-12,"attackMs":100,"releaseMs":200},regions)
    assert "between(t,5.000000,10.000000)" in expr and f"{db_to_linear(-12):.8f}" in expr


def test_music_ducking_rule_created(tmp_path):
    repo,m=mixer_for(tmp_path,"p1"); m.ensure_project("p1","news"); rule=m.set_music_ducking("p1",True,-12)
    assert rule and rule.duck_amount_db==-12 and len(repo.ducking_rules("p1"))==1


def test_legacy_dub_migration_20_percent_original(tmp_path):
    _,m=mixer_for(tmp_path,"p1")
    m.migrate_legacy_dub("p1",{"originalVolume":.20,"dubVolume":1.0,"mode":"duck","duckNormalVolume":.2,"duckUnderVolume":.1,"duckFadeMs":150})
    original=m.track_for_role("p1","source_audio"); dub=m.track_for_role("p1","dub")
    assert original.gain_db == pytest.approx(linear_to_db(.2),abs=.001) and dub.gain_db==pytest.approx(0,abs=.001)
    assert any(r.target_id==original.id for r in m.repository.ducking_rules("p1"))


def test_source_audio_legacy_volume_migration(tmp_path):
    _,m=mixer_for(tmp_path,"p1"); m.ensure_project("p1")
    row=m.migrate_source_audio_volume("p1","scene-audio",.5,True)
    assert row["gainDb"]==pytest.approx(-6.0206,abs=.01) and row["muted"]


@pytest.mark.parametrize("role,expected",[("Narrator","narration"),("Reporter","voice"),("Guest","dialogue"),("Character","dialogue")])
def test_multi_speaker_routing(role,expected,tmp_path):
    _,m=mixer_for(tmp_path,"p1"); m.ensure_project("p1","news")
    assert m.route_speaker_role("p1",role).role_code==expected


def test_unicode_speaker_labels_round_trip():
    labels=[("អ្នករាយការណ៍","km"),("ผู้สื่อข่าว","th"),("Phóng viên","vi"),("Reporter","en")]
    for idx,(name,lang) in enumerate(labels):
        clip=AudioClip(str(idx),"p","t","x.wav",0,1000,speaker_name=name,language=lang); assert clip.to_dict()["speakerName"]==name


def test_music_sfx_asset_routing(tmp_path):
    _,m=mixer_for(tmp_path,"p1"); m.ensure_project("p1")
    assert m.add_asset_clip_defaults("p1","music-1","music")["trackId"]==m.track_for_role("p1","music").id
    assert m.add_asset_clip_defaults("p1","sfx-1","sfx")["trackId"]==m.track_for_role("p1","sfx").id


def test_template_settings_are_semantic_and_reusable(tmp_path):
    _,m=mixer_for(tmp_path,"p1","p2"); m.ensure_project("p1","news")
    m.set_music_ducking("p1",True,-14); voice=m.track_for_role("p1","voice"); m.add_voice_effect_preset("p1",voice.id,"clear_voice")
    template=m.template_settings("p1")
    serialized=json.dumps(template); assert "p1" not in serialized and voice.id not in serialized
    m.apply_template_settings("p2",template)
    state=m.state("p2"); assert any(x["role"]=="voice" for x in state["tracks"]) and state["duckingRules"]


def test_project_duplication_remaps_ids(tmp_path):
    repo,m=mixer_for(tmp_path,"p1","p2"); m.ensure_project("p1","news")
    t=m.track_for_role("p1","voice"); m.set_clip_mix("p1","oldclip",trackId=t.id,gainDb=-4); m.set_music_ducking("p1",True,-11)
    maps=m.duplicate_project("p1","p2",clip_id_map={"oldclip":"newclip"})
    assert maps["track"][t.id] != t.id and repo.clip_mix("p2","newclip")["gainDb"]==-4
    assert all(r.project_id=="p2" for r in repo.ducking_rules("p2"))


def test_project_delete_cascades_mixer_metadata(tmp_path):
    repo,m=mixer_for(tmp_path,"p1"); m.ensure_project("p1")
    with repo.database.connect() as c,c: c.execute("DELETE FROM projects WHERE id='p1'")
    assert repo.tracks("p1")==[] and repo.buses("p1")==[]


def test_render_graph_contains_trim_delay_gain_pan_fades():
    service=AudioRenderService()
    spec={"durationMs":3000,"tracks":[{"id":"t","enabled":True,"muted":False,"solo":False,"gainDb":-3,"pan":.5,"busId":""}],"buses":[],"clips":[{"id":"c","trackId":"t","sourcePath":"input.wav","timelineStartMs":500,"durationMs":1500,"sourceInMs":250,"gainDb":-2,"pan":-.25,"fadeInMs":100,"fadeOutMs":200,"muted":False}],"effects":[],"duckingRules":[],"master":{"masterGainDb":-1,"limiterEnabled":True,"limiterLimit":.95}}
    cmd=service.build_command(spec,"out.wav",available_filters={"alimiter"}); graph=cmd[cmd.index("-filter_complex")+1]
    for token in ("atrim=start=0.250000","adelay=500","afade=t=in","afade=t=out","pan=stereo","alimiter=limit=0.9500"):
        assert token in graph


def test_ffmpeg_effect_graph_eq_highpass_lowpass_compressor_limiter():
    service=AudioRenderService(); effects=[
        {"ownerType":"track","ownerId":"t","type":"high_pass","order":0,"enabled":True,"settings":{"frequency":80}},
        {"ownerType":"track","ownerId":"t","type":"low_pass","order":1,"enabled":True,"settings":{"frequency":16000}},
        {"ownerType":"track","ownerId":"t","type":"eq","order":2,"enabled":True,"settings":{"lowDb":1,"midDb":-1,"highDb":2}},
        {"ownerType":"track","ownerId":"t","type":"compressor","order":3,"enabled":True,"settings":{"ratio":2}},
    ]
    spec={"durationMs":1000,"tracks":[{"id":"t","enabled":True,"muted":False,"solo":False,"gainDb":0,"pan":0,"busId":""}],"buses":[],"clips":[{"id":"c","trackId":"t","sourcePath":"x.wav","timelineStartMs":0,"durationMs":1000,"gainDb":0,"pan":0,"muted":False}],"effects":effects,"duckingRules":[],"master":{"limiterEnabled":True}}
    cmd=service.build_command(spec,"out.wav",available_filters={"highpass","lowpass","equalizer","acompressor","alimiter"}); graph=cmd[cmd.index("-filter_complex")+1]
    assert graph.index("highpass") < graph.index("lowpass") < graph.index("equalizer") < graph.index("acompressor")


def test_effect_bypass_excluded_from_graph():
    service=AudioRenderService(); spec=basic_spec(Path("/tmp")); spec["clips"][0]["sourcePath"]="x.wav"; spec["clips"][1]["muted"]=True
    spec["effects"]=[{"ownerType":"track","ownerId":"tv","type":"high_pass","order":0,"enabled":False,"settings":{}}]
    graph=service.build_command(spec,"out.wav",available_filters={"highpass","alimiter"})[-9] if False else service.build_command(spec,"out.wav",available_filters={"highpass","alimiter"})
    text=graph[graph.index("-filter_complex")+1]; assert "highpass" not in text


def test_solo_render_only_solo_tracks(tmp_path):
    spec=basic_spec(tmp_path); spec["tracks"][1]["solo"]=True
    cmd=AudioRenderService().build_command(spec,tmp_path/"out.wav",available_filters={"alimiter"}); text=cmd[cmd.index("-filter_complex")+1]
    assert "[0:a]" not in text and "[1:a]" in text or cmd.count("-i")==1


def test_muted_bus_does_not_leak_to_master(tmp_path):
    spec=basic_spec(tmp_path); spec["buses"][1]["muted"]=True
    cmd=AudioRenderService().build_command(spec,tmp_path/"out.wav",available_filters={"alimiter"}); text=cmd[cmd.index("-filter_complex")+1]
    assert "b_bm" not in text


def test_audio_validation_missing_and_clipping(tmp_path):
    spec={"tracks":[{"id":"t","name":"Voice","gainDb":12,"muted":False,"busId":"missing"}],"buses":[],"clips":[{"sourcePath":str(tmp_path/"no.wav"),"timelineStartMs":0,"durationMs":2000,"sourceInMs":0,"muted":False}],"effects":[]}
    codes={x["code"] for x in AudioValidationService().validate_mix(spec,project_duration_ms=1000)}
    assert {"missing_bus","extreme_gain","missing_audio","outside_project"} <= codes


def test_render_plan_audio_mix_snapshot(tmp_path):
    from domain.render_settings import RenderSettings
    mix={"projectId":"p1","clips":[{"id":"a"}]}
    plan=RenderPlan("p1",str(tmp_path/"x.mp4"),RenderSettings(1920,1080),[{"sceneId":"s","durationMs":1000}],1000,str(tmp_path/"tmp"),audio_mix_spec=mix)
    plan.validate(); snap=plan.snapshot(); assert snap["schemaVersion"]==2 and snap["audioMixSpec"]==mix


def test_waveform_wav_cache_and_invalidation(tmp_path):
    paths=make_paths(tmp_path); cache=CacheService(paths); wav=tone_wav(tmp_path/"សំឡេង.wav")
    service=AudioWaveformService(cache,lambda:FFMPEG); one=service.generate(wav,buckets=100); two=service.generate(wav,buckets=100)
    assert one["buckets"] and two["cacheHit"] is True
    target=service.cache_path(wav,100); assert target.is_file(); service.invalidate(wav,buckets=100); assert not target.exists(); assert service.generate(wav,buckets=100)["cacheHit"] is False


def test_waveform_mp3_and_video_audio(tmp_path):
    if not FFMPEG: pytest.skip("ffmpeg unavailable")
    paths=make_paths(tmp_path); cache=CacheService(paths); wav=tone_wav(tmp_path/"src.wav")
    mp3=ffmpeg_convert(wav,tmp_path/"a.mp3")
    video=tmp_path/"v.mp4"; subprocess.run([FFMPEG,"-hide_banner","-loglevel","error","-y","-f","lavfi","-i","color=s=64x64:d=1","-i",str(wav),"-shortest","-c:v","libx264","-c:a","aac",str(video)],check=True,capture_output=True)
    service=AudioWaveformService(cache,lambda:FFMPEG)
    assert service.generate(mp3,buckets=50)["buckets"] and service.generate(video,buckets=50)["buckets"]


def test_waveform_category_is_safe_cache():
    d=definition(StorageCategory.AUDIO_WAVEFORM_CACHE); assert d.safety==StorageSafety.SAFE_TO_CLEAR and d.cache


def test_peak_and_loudness_analysis_and_normalization(tmp_path):
    if not FFMPEG: pytest.skip("ffmpeg unavailable")
    wav=tone_wav(tmp_path/"tone.wav",gain=.1,seconds=1.5)
    service=AudioAnalysisService(lambda:FFMPEG); meter=service.analyze(wav)
    assert -40 < meter.peak_db < -10 and meter.integrated_lufs is not None
    gain=service.normalization_gain_db(meter,-16); assert -60 <= gain <= 12
    peak_gain=service.peak_normalization_gain_db(meter,-1); assert -60 <= peak_gain <= 12


def test_real_basic_mix_render(tmp_path):
    if not FFMPEG: pytest.skip("ffmpeg unavailable")
    spec=basic_spec(tmp_path); runner=FFmpegRunner(FFMPEG); caps=runner.discover_capabilities(); out=tmp_path/"basic.wav"
    AudioRenderService(runner).render_mix(spec,out,available_filters=caps.filters)
    assert out.is_file() and out.stat().st_size>1000
    if FFPROBE:
        done=subprocess.run([FFPROBE,"-v","error","-show_entries","stream=sample_rate,channels","-of","json",str(out)],capture_output=True,text=True,check=True); data=json.loads(done.stdout)["streams"][0]
        assert data["sample_rate"]=="48000" and data["channels"]==2


def test_news_ducking_real_graph_and_render(tmp_path):
    if not FFMPEG: pytest.skip("ffmpeg unavailable")
    spec=basic_spec(tmp_path,duration_ms=3000); spec["clips"][0]["timelineStartMs"]=500; spec["clips"][0]["durationMs"]=1000
    spec["duckingRules"]=[{"id":"d","triggerKind":"bus","triggerId":"bv","targetKind":"bus","targetId":"bm","duckAmountDb":-12,"attackMs":120,"releaseMs":220,"enabled":True}]
    runner=FFmpegRunner(FFMPEG); caps=runner.discover_capabilities(); cmd=AudioRenderService().build_command(spec,tmp_path/"news.wav",available_filters=caps.filters); graph=cmd[cmd.index("-filter_complex")+1]
    assert "volume='if(between" in graph
    AudioRenderService(runner).render_mix(spec,tmp_path/"news.wav",available_filters=caps.filters); assert (tmp_path/"news.wav").is_file()


def test_interview_independent_gain_mute_solo_render(tmp_path):
    if not FFMPEG: pytest.skip("ffmpeg unavailable")
    a=tone_wav(tmp_path/"reporter.wav",hz=440,seconds=1); b=tone_wav(tmp_path/"guest.wav",hz=660,seconds=1); c=tone_wav(tmp_path/"room.wav",hz=120,seconds=1)
    spec={"durationMs":1000,"buses":[],"tracks":[
        {"id":"r","gainDb":0,"pan":-.2,"muted":False,"solo":True,"enabled":True,"busId":""},
        {"id":"g","gainDb":-2,"pan":.2,"muted":False,"solo":True,"enabled":True,"busId":""},
        {"id":"a","gainDb":-20,"pan":0,"muted":False,"solo":False,"enabled":True,"busId":""}],
        "clips":[{"id":"1","trackId":"r","sourcePath":str(a),"timelineStartMs":0,"durationMs":1000},{"id":"2","trackId":"g","sourcePath":str(b),"timelineStartMs":0,"durationMs":1000},{"id":"3","trackId":"a","sourcePath":str(c),"timelineStartMs":0,"durationMs":1000}],"effects":[],"duckingRules":[],"master":{"limiterEnabled":True}}
    runner=FFmpegRunner(FFMPEG); caps=runner.discover_capabilities(); out=tmp_path/"interview.wav"; AudioRenderService(runner).render_mix(spec,out,available_filters=caps.filters); assert out.is_file()


def test_sample_rate_mono_stereo_conversion(tmp_path):
    if not FFMPEG: pytest.skip("ffmpeg unavailable")
    mono=tone_wav(tmp_path/"mono441.wav",rate=44100,channels=1); stereo=tone_wav(tmp_path/"stereo48.wav",rate=48000,channels=2,hz=330)
    spec={"durationMs":1000,"buses":[],"tracks":[{"id":"t","gainDb":0,"pan":0,"muted":False,"solo":False,"enabled":True,"busId":""}],"clips":[{"id":"a","trackId":"t","sourcePath":str(mono),"timelineStartMs":0,"durationMs":1000},{"id":"b","trackId":"t","sourcePath":str(stereo),"timelineStartMs":0,"durationMs":1000}],"effects":[],"duckingRules":[],"master":{"limiterEnabled":True}}
    runner=FFmpegRunner(FFMPEG); caps=runner.discover_capabilities(); out=tmp_path/"sr.wav"; AudioRenderService(runner).render_mix(spec,out,available_filters=caps.filters)
    done=subprocess.run([FFPROBE,"-v","error","-show_entries","stream=sample_rate,channels","-of","json",str(out)],capture_output=True,text=True,check=True); stream=json.loads(done.stdout)["streams"][0]; assert stream["sample_rate"]=="48000" and stream["channels"]==2


def test_mix_preview_cache_key_changes_with_gain(tmp_path):
    paths=make_paths(tmp_path); cache=CacheService(paths); service=AudioRenderService(cache_service=cache); spec=basic_spec(tmp_path)
    p1=service.preview_path(spec,"p1"); spec["tracks"][0]["gainDb"]=-3; p2=service.preview_path(spec,"p1")
    assert p1 != p2 and p1.parent.name=="audio-mix"


def test_master_limiter_and_normalization_filters_required():
    spec={"durationMs":1000,"tracks":[],"buses":[],"clips":[],"effects":[],"duckingRules":[],"master":{"limiterEnabled":True,"normalizationEnabled":True,"normalizationTargetLufs":-16}}
    with pytest.raises(Exception): AudioRenderService().build_command(spec,"x.wav",available_filters={"alimiter"})
    cmd=AudioRenderService().build_command(spec,"x.wav",available_filters={"alimiter","loudnorm"}); assert "loudnorm=I=-16.00" in cmd[cmd.index("-filter_complex")+1]


def test_preset_news_story_shorts_dub(tmp_path):
    _,m=mixer_for(tmp_path,"p1")
    for preset in ("news","story","shorts","dub"):
        state=m.apply_preset("p1",preset); assert state["master"]["preset"]==preset


def test_dub_convenience_presets(tmp_path):
    _,m=mixer_for(tmp_path,"p1"); m.apply_dub_preset("p1","dub_only"); assert m.track_for_role("p1","source_audio").muted
    m.apply_dub_preset("p1","dub_quiet_original"); assert not m.track_for_role("p1","source_audio").muted


def test_large_project_mix_spec_100_clips(tmp_path):
    _,m=mixer_for(tmp_path,"p1"); m.ensure_project("p1"); track=m.track_for_role("p1","music")
    clips=[{"id":f"c{i}","trackId":track.id,"role":"music","sourcePath":f"x{i}.wav","timelineStartMs":i*100,"durationMs":1000,"gainDb":-12,"pan":0,"muted":False} for i in range(120)]
    spec=m.build_mix_spec("p1",clips,13000); assert len(spec["clips"])==120 and len(spec["tracks"])>=4


def test_database_migration_tables(tmp_path):
    repo=repo_for(tmp_path,"p1")
    with repo.database.connect() as c:
        tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"audio_tracks","audio_buses","audio_clip_mix","audio_effects","audio_ducking_rules","audio_mix_settings"} <= tables


def test_qml_mixer_structure():
    root=Path(__file__).resolve().parents[1]
    required=["AudioMixer.qml","MixerTrack.qml","MixerStrip.qml","AudioInspector.qml","AudioMeter.qml","WaveformView.qml","MasterStrip.qml","DuckingPanel.qml"]
    for name in required:
        text=(root/"ui"/"qml"/"audio"/name).read_text(encoding="utf-8"); assert "Theme." in text and text.count("{") == text.count("}")
    timeline=(root/"ui"/"qml"/"timeline"/"TimelineEditor.qml").read_text(encoding="utf-8"); assert "AudioMixer" in timeline and "Mixer" in timeline


def test_news_story_dub_open_mixer_actions():
    root=Path(__file__).resolve().parents[1]
    for rel in ("ui/qml/news/NewsStudio.qml","ui/qml/story/StoryStudio.qml","ui/qml/dubbing/TranslateDubStudio.qml"):
        text=(root/rel).read_text(encoding="utf-8"); assert "Mixer" in text


def test_runtime_wiring_and_no_second_renderer():
    root=Path(__file__).resolve().parents[1]; text=(root/"app"/"phase30_runtime.py").read_text(encoding="utf-8")
    assert "class AudioProject" not in text and "class AudioRenderer" not in text
    assert "render_service.build_plan" in text and "audio_mix_spec" in text
    assert "app.phase30_runtime:run" in (root/"pyproject.toml").read_text(encoding="utf-8")


def test_phase29_waveform_cache_is_separate_from_generated_audio():
    root=Path(__file__).resolve().parents[1]; text=(root/"services"/"cache_service.py").read_text(encoding="utf-8")
    assert 'AUDIO_WAVEFORM_CACHE: "audio/waveforms"' in text and 'name != "waveforms"' in text
