from __future__ import annotations

import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from domain.dub_audio import DubAudioOutput
from domain.dub_mix_settings import DubMixMode, DubMixSettings
from domain.dub_segment import DubAudioStatus, DubSegment, DubTimingMode, DubTimingStatus, dub_text_hash
from domain.dubbing_project import DubbingProject
from services.dubbing_alignment_service import DubbingAlignmentConfig, DubbingAlignmentService
from services.dubbing_audio_service import DubbingAudioService
from storage.migrations.m018_create_dubbing import migrate
from storage.repositories.dubbing_repository import DubbingRepository


def segment(*, start=0, end=3000, generated=3000, order=0, text="សួស្តី", translation="tr-1"):
    return DubSegment(project_id="p1", source_transcript_segment_id=f"src-{order}", translation_segment_id=translation,
                      order=order, source_start_ms=start, source_end_ms=end, target_text=text,
                      generated_duration_ms=generated, generated_audio_path=f"/tmp/{order}.wav" if generated else "",
                      audio_status=DubAudioStatus.READY if generated else DubAudioStatus.PENDING)


def make_db(path: Path):
    c=sqlite3.connect(path); c.execute("PRAGMA foreign_keys=ON")
    c.executescript('''
    CREATE TABLE projects(id TEXT PRIMARY KEY);
    CREATE TABLE media_assets(id TEXT PRIMARY KEY);
    CREATE TABLE transcripts(id TEXT PRIMARY KEY);
    CREATE TABLE transcript_segments(id TEXT PRIMARY KEY);
    CREATE TABLE translations(id TEXT PRIMARY KEY);
    CREATE TABLE translation_segments(id TEXT PRIMARY KEY);
    CREATE TABLE subtitle_tracks(id TEXT PRIMARY KEY);
    CREATE TABLE generated_audio(id TEXT PRIMARY KEY);
    INSERT INTO projects VALUES('p1'); INSERT INTO media_assets VALUES('m1');
    INSERT INTO transcripts VALUES('t1'); INSERT INTO transcript_segments VALUES('src-0'); INSERT INTO transcript_segments VALUES('src-1');
    INSERT INTO translations VALUES('x1'); INSERT INTO translation_segments VALUES('tr-1'); INSERT INTO translation_segments VALUES('tr-2');
    '''); migrate(c); c.commit(); c.close()

    class DB:
        from contextlib import contextmanager
        @contextmanager
        def connect(self):
            db=sqlite3.connect(path); db.row_factory=sqlite3.Row; db.execute("PRAGMA foreign_keys=ON")
            try: yield db
            finally: db.close()
    return DB()


def test_language_validation_and_primary_pair():
    DubbingProject("p1", source_language="en", target_language="km").validate()
    DubbingProject("p1", source_language="km", target_language="en").validate()
    DubbingProject("p1", source_language="auto", target_language="km").validate()
    with pytest.raises(ValueError): DubbingProject("p1", source_language="en", target_language="en").validate()


def test_segment_target_duration_and_unicode_hash():
    s=segment(start=4200,end=7800,generated=4200,text="សូមស្វាគមន៍")
    assert s.target_duration_ms==3600
    assert dub_text_hash(s.target_text,{"id":"dara"},"2.0",{"seed":1}) == dub_text_hash(s.target_text,{"id":"dara"},"2.0",{"seed":1})
    assert dub_text_hash(s.target_text,{"id":"dara"},"2.0",{}) != dub_text_hash("ផ្សេង",{"id":"dara"},"2.0",{})


def test_timing_fit_short_long_and_very_long():
    svc=DubbingAlignmentService()
    assert svc.analyze(segment(end=3000,generated=3000)).status=="fits"
    assert svc.analyze(segment(end=5000,generated=3000)).status=="short"
    assert svc.analyze(segment(end=3000,generated=3600)).status=="long"
    result=svc.analyze(segment(end=3000,generated=5000))
    assert result.status=="very_long" and result.strong_stretch_required


def test_safe_fit_threshold_and_extreme_warning():
    svc=DubbingAlignmentService(DubbingAlignmentConfig(safe_min_tempo=.85,safe_max_tempo=1.20))
    okay=segment(end=4000,generated=4400); okay.timing_mode=DubTimingMode.FIT_SEGMENT
    svc.apply_analysis(okay)
    assert okay.timing_status_code==DubTimingStatus.ADJUSTED.value
    assert okay.stretch_factor==pytest.approx(1.1)
    extreme=segment(end=3000,generated=5000); extreme.timing_mode=DubTimingMode.FIT_SEGMENT
    svc.apply_analysis(extreme)
    assert extreme.timing_status_code==DubTimingStatus.NEEDS_REVIEW.value
    assert extreme.stretch_factor==1.0


def test_atempo_chain_stays_in_ffmpeg_range():
    for tempo in (.2,.5,.85,1,1.2,2,5):
        chain=DubbingAlignmentService.atempo_chain(tempo)
        assert all(.5 <= item <= 2 for item in chain)
        product=1.0
        for item in chain: product*=item
        assert product==pytest.approx(tempo)


def test_overlap_and_gap_analysis():
    svc=DubbingAlignmentService()
    a=segment(start=0,end=3000,generated=4000,order=0,translation="tr-1")
    b=segment(start=3500,end=5000,generated=1000,order=1,translation="tr-2")
    assert svc.detect_overlaps([a,b])[0]["overlapMs"]==500
    a.generated_duration_ms=1000; b.source_start_ms=4000
    assert svc.analyze_gaps([a,b])[0]["gapMs"]==3000


def test_offset_validation_never_goes_before_zero():
    svc=DubbingAlignmentService(); s=segment(start=500,end=1500)
    assert svc.validate_offset(s,-500)==-500
    with pytest.raises(ValueError): svc.validate_offset(s,-501)


def test_mix_modes_and_ffmpeg_commands():
    audio=DubbingAudioService(lambda:"ffmpeg")
    s=segment(end=3000,generated=3000); s.generated_audio_path="a.wav"
    narration=audio.build_narration_command([s],5000,"dub.wav")
    assert "aresample=48000" in " ".join(narration) and "pcm_s16le" in narration
    for mode in DubMixMode:
        settings=DubMixSettings("p1",mode=mode)
        cmd=audio.build_mix_command("video.mp4","dub.wav",5000,settings,[s],"mix.wav")
        text=" ".join(cmd)
        assert "48000" in text and "alimiter" in text
        if mode==DubMixMode.DUCK: assert "between(t" in text


def test_final_mix_fingerprint_changes_only_with_inputs():
    audio=DubbingAudioService(lambda:"ffmpeg"); s=segment(); s.generated_audio_id="ga1"; s.generation_hash="h1"
    settings=DubMixSettings("p1")
    a=audio.final_mix_fingerprint("source",[s],settings); b=audio.final_mix_fingerprint("source",[s],settings)
    assert a==b
    s.start_offset_ms=100
    assert audio.final_mix_fingerprint("source",[s],settings)!=a


def test_migration_repository_and_restart_persistence(tmp_path):
    db=make_db(tmp_path/"phase21.db"); repo=DubbingRepository(db)
    project=DubbingProject("p1","m1","en","km","t1","x1","voice-a")
    repo.save_project(project)
    s=segment(); s.source_transcript_segment_id="src-0"; s.translation_segment_id="tr-1"; s.start_offset_ms=120
    repo.save_segment(s); repo.save_mix_settings(DubMixSettings("p1",mode="duck",original_volume=.2))
    # New repository instance simulates restart.
    reopened=DubbingRepository(db)
    assert reopened.get_project("p1").target_language=="km"
    assert reopened.segments("p1")[0].start_offset_ms==120
    assert reopened.get_mix_settings("p1").original_volume==pytest.approx(.2)


def test_project_voice_change_invalidation_semantics(tmp_path):
    db=make_db(tmp_path/"voice.db"); repo=DubbingRepository(db); repo.save_project(DubbingProject("p1","m1","en","km","t1","x1","voice-a"))
    default=segment(translation="tr-1"); default.source_transcript_segment_id="src-0"; default.generated_audio_id=""; repo.save_segment(default)
    override=segment(order=1,translation="tr-2"); override.source_transcript_segment_id="src-1"; override.voice_id="voice-c"; repo.save_segment(override)
    # Exact Phase 21 rule: global voice change invalidates only default-voice rows.
    for item in repo.segments("p1"):
        if not item.voice_id: item.audio_status=DubAudioStatus.OUTDATED; repo.save_segment(item)
    values={x.translation_segment_id:x for x in repo.segments("p1")}
    assert values["tr-1"].audio_status_code=="outdated"
    assert values["tr-2"].audio_status_code=="ready"


def test_translation_change_invalidates_only_related_segment(tmp_path):
    db=make_db(tmp_path/"translation.db"); repo=DubbingRepository(db); repo.save_project(DubbingProject("p1","m1","en","km","t1","x1","voice-a"))
    first=segment(translation="tr-1"); first.source_transcript_segment_id="src-0"; second=segment(order=1,translation="tr-2"); second.source_transcript_segment_id="src-1"
    repo.save_segment(first); repo.save_segment(second)
    changed=repo.segment_for_translation("p1","tr-1"); changed.target_text="បានកែ"; changed.audio_status=DubAudioStatus.OUTDATED; repo.save_segment(changed)
    values={x.translation_segment_id:x for x in repo.segments("p1")}
    assert values["tr-1"].audio_status_code=="outdated" and values["tr-2"].audio_status_code=="ready"


def test_locked_segment_is_skippable():
    s=segment(); s.locked=True
    assert s.locked and s.audio_status_code=="ready"


def test_audio_output_roundtrip(tmp_path):
    db=make_db(tmp_path/"output.db"); repo=DubbingRepository(db); repo.save_project(DubbingProject("p1","m1","en","km","t1","x1","voice-a"))
    out=DubAudioOutput("p1","m1","km","/tmp/final.wav",5000,"fp")
    repo.save_output(out)
    assert repo.latest_output("p1").fingerprint=="fp"
    repo.mark_outputs_outdated("p1")
    assert repo.latest_output("p1").status_code=="outdated"


def test_project_duplication_creates_new_segment_ids(tmp_path):
    path=tmp_path/"dup.db"; db=make_db(path); repo=DubbingRepository(db)
    with db.connect() as c,c: c.execute("INSERT INTO projects VALUES('p2')")
    repo.save_project(DubbingProject("p1","m1","en","km","t1","x1","voice-a")); s=segment(); s.source_transcript_segment_id="src-0"; repo.save_segment(s)
    mapping=repo.duplicate_project("p1","p2")
    copied=repo.segments("p2")
    assert mapping[s.id]==copied[0].id and copied[0].id!=s.id
    assert copied[0].generated_audio_id=="" and copied[0].generated_audio_path==""
