from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from domain.project import Project
from domain.media import MediaAsset, MediaType
from domain.subtitle import SubtitleTrackStatus
from domain.subtitle_cue import SubtitleCue
from domain.subtitle_style import SubtitleStyle
from domain.transcript import Transcript, TranscriptStatus
from domain.transcript_segment import TranscriptSegment
from domain.transcript_word import TranscriptWord
from domain.translation import Translation, TranslationStatus
from domain.translation_segment import TranslationSegment, TranslationSegmentStatus
from media.subtitles.ass_exporter import ASSExporter, ass_color, escape_ass_text
from media.subtitles.srt_exporter import SRTExporter, format_srt_timestamp
from media.subtitles.vtt_exporter import VTTExporter
from services.project_service import ProjectService
from services.subtitle_generation_service import SubtitleGenerationService
from services.subtitle_import_service import SubtitleImportService
from services.subtitle_preset_service import SubtitlePresetService
from services.subtitle_service import SubtitleService
from services.subtitle_timing_service import SubtitleTimingService
from services.subtitle_validation_service import SubtitleValidationService
from storage.database import SQLiteDatabase
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.media_repository import MediaRepository
from storage.repositories.subtitle_repository import SubtitleRepository
from storage.repositories.transcript_repository import TranscriptRepository
from storage.repositories.translation_repository import TranslationRepository


def make_system(tmp_path: Path):
    db=SQLiteDatabase(tmp_path/'data'/'app.db'); db.initialize()
    projects=ProjectRepository(db); media=MediaRepository(db); transcripts=TranscriptRepository(db); translations=TranslationRepository(db); subtitles=SubtitleRepository(db)
    root=tmp_path/'Projects'/'demo'; root.mkdir(parents=True)
    project=Project(project_id='project-1',title='Demo',workflow='video',language='en',project_path=str(root)); projects.create(project)
    media_path=root/'media'/'video'/'sample.mp4'; media_path.parent.mkdir(parents=True,exist_ok=True); media_path.write_bytes(b'fixture')
    media.create(MediaAsset(asset_id='media-1',project_id=project.project_id,media_type=MediaType.VIDEO,name='sample.mp4',original_path=str(media_path),project_path=str(media_path),file_size=7,duration_ms=8000,extension='.mp4'))
    transcript=Transcript(transcript_id='tr-1',project_id=project.project_id,media_id='media-1',engine='faster-whisper',model_id='whisper-small',language_mode='en',detected_language='en',status=TranscriptStatus.READY,active=True,duration_ms=8000)
    s1=TranscriptSegment(transcript_id=transcript.id,segment_id='seg-1',order=0,start_ms=0,end_ms=3500,text="Welcome to today's update.")
    s1.words=[TranscriptWord(segment_id=s1.id,word_id='w-1',order=0,start_ms=0,end_ms=900,text='Welcome',probability=.99),TranscriptWord(segment_id=s1.id,word_id='w-2',order=1,start_ms=900,end_ms=1500,text='today',probability=.98)]
    s2=TranscriptSegment(transcript_id=transcript.id,segment_id='seg-2',order=1,start_ms=3500,end_ms=8000,text='Technology moves quickly.')
    transcripts.create_with_segments(transcript,[s1,s2])
    translation=Translation(translation_id='tx-1',project_id=project.project_id,source_type='transcript',source_id=transcript.id,source_language='en',target_language='km',engine_id='local_marian',model_id='translation-en-km-opus',status=TranslationStatus.APPROVED)
    t1=TranslationSegment(translation_id=translation.id,segment_id='txs-1',source_segment_id=s1.id,order=0,start_ms=0,end_ms=3500,source_text=s1.text,machine_translation='សូមស្វាគមន៍',translated_text='សូមស្វាគមន៍មកកាន់ព័ត៌មានថ្ងៃនេះ។',status=TranslationSegmentStatus.TRANSLATED,reviewed=True)
    t2=TranslationSegment(translation_id=translation.id,segment_id='txs-2',source_segment_id=s2.id,order=1,start_ms=3500,end_ms=8000,source_text=s2.text,machine_translation='បច្ចេកវិទ្យា',translated_text='បច្ចេកវិទ្យាផ្លាស់ប្តូរយ៉ាងឆាប់រហ័ស។',status=TranslationSegmentStatus.TRANSLATED,reviewed=True)
    translations.create(translation,[t1,t2])
    generation=SubtitleGenerationService(transcripts,translations); presets=SubtitlePresetService(subtitles); validation=SubtitleValidationService(); timing=SubtitleTimingService()
    service=SubtitleService(subtitles,projects,transcripts,translations,generation,presets,validation,timing)
    return SimpleNamespace(db=db,projects=projects,media=media,transcripts=transcripts,translations=translations,subtitles=subtitles,project=project,transcript=transcript,translation=translation,service=service,presets=presets,timing=timing,validation=validation)


def test_phase12_schema_migration(tmp_path: Path):
    sys=make_system(tmp_path); assert sys.db.current_version() == 15
    with sys.db.connect() as c: tables={r['name'] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {'subtitle_tracks','subtitle_cues','subtitle_words','subtitle_styles','subtitle_user_presets'} <= tables


def test_create_from_transcript_preserves_words_and_timestamps(tmp_path: Path):
    sys=make_system(tmp_path); track=sys.service.create_from_transcript(sys.project.id,sys.transcript.id)
    track,style,cues=sys.service.get(sys.project.id,track.id)
    assert [(q.start_ms,q.end_ms) for q in cues]==[(0,3500),(3500,8000)]
    assert cues[0].words[0].text=='Welcome' and cues[0].words[0].start_ms==0
    assert track.is_default and style.name=='Clean'


def test_create_from_reviewed_translation_and_khmer_unicode(tmp_path: Path):
    sys=make_system(tmp_path); track=sys.service.create_from_translation(sys.project.id,sys.translation.id)
    _,_,cues=sys.service.get(sys.project.id,track.id)
    assert track.language=='km'; assert cues[0].text.startswith('សូមស្វាគមន៍')
    assert cues[0].start_ms==0 and cues[1].end_ms==8000


def test_bilingual_alignment_uses_source_ids(tmp_path: Path):
    sys=make_system(tmp_path); track=sys.service.create_bilingual(sys.project.id,sys.transcript.id,sys.translation.id)
    _,_,cues=sys.service.get(sys.project.id,track.id)
    assert cues[0].source_segment_id=='seg-1'; assert cues[0].text.startswith('Welcome'); assert cues[0].secondary_text.startswith('សូម')
    assert cues[0].words


def test_bilingual_missing_segment_is_reported(tmp_path: Path):
    sys=make_system(tmp_path);
    with sys.db.connect() as connection, connection: connection.execute("DELETE FROM translation_segments WHERE id=?", ('txs-2',))
    track=sys.service.create_bilingual(sys.project.id,sys.transcript.id,sys.translation.id)
    assert 'seg-2' in track.metadata['unmatchedSourceSegmentIds']


def test_manual_track_add_delete_and_default_persist(tmp_path: Path):
    sys=make_system(tmp_path); track=sys.service.create_manual(sys.project.id,'en')
    cue=sys.service.add_cue(sys.project.id,track.id,1200,'Hello',2000); assert cue.start_ms==1200
    sys.service.set_default(sys.project.id,track.id); assert sys.subtitles.default_for_project(sys.project.id).id==track.id
    sys.service.delete_cue(sys.project.id,track.id,cue.id); assert sys.subtitles.cues(track.id)==[]


def test_split_merge_round_trip(tmp_path: Path):
    sys=make_system(tmp_path); track=sys.service.create_manual(sys.project.id,'en'); cue=sys.service.add_cue(sys.project.id,track.id,0,'Hello world',6000)
    a,b=sys.service.split_cue(sys.project.id,track.id,cue.id,3000,'Hello','world'); assert (a.start_ms,a.end_ms,b.start_ms,b.end_ms)==(0,3000,3000,6000)
    merged=sys.service.merge_cues(sys.project.id,track.id,a.id,b.id); assert merged.start_ms==0 and merged.end_ms==6000 and merged.text=='Hello world'


def test_shift_timing_and_negative_guard(tmp_path: Path):
    sys=make_system(tmp_path); track=sys.service.create_manual(sys.project.id,'en'); sys.service.add_cue(sys.project.id,track.id,1000,'A'); sys.service.add_cue(sys.project.id,track.id,3000,'B')
    shifted=sys.service.shift_timing(sys.project.id,track.id,500); assert [q.start_ms for q in shifted]==[1500,3500]
    with pytest.raises(ValueError): sys.service.shift_timing(sys.project.id,track.id,-2000)


def test_validation_overlap_short_long_reading_speed_and_lines(tmp_path: Path):
    style=SubtitleStyle(project_id='p',max_lines=2)
    cues=[SubtitleCue(track_id='t',order=0,start_ms=0,end_ms=200,text='Very long subtitle text that cannot reasonably be read this fast.'),SubtitleCue(track_id='t',order=1,start_ms=150,end_ms=12000,text='one\ntwo\nthree')]
    issues=SubtitleValidationService().validate(cues,style,'en')
    codes={i.code for i in issues}; assert {'too_short','reading_too_fast','overlap','too_long','too_many_lines'} <= codes


def test_khmer_reading_speed_uses_character_metric():
    style=SubtitleStyle(project_id='p'); cue=SubtitleCue(track_id='t',order=0,start_ms=0,end_ms=300,text='សួស្តីនេះជាព័ត៌មានថ្មីសម្រាប់ថ្ងៃនេះ')
    codes={i.code for i in SubtitleValidationService().validate([cue],style,'km')}; assert 'reading_too_fast' in codes


def test_srt_vtt_ass_exports_and_khmer(tmp_path: Path):
    sys=make_system(tmp_path); track=sys.service.create_from_translation(sys.project.id,sys.translation.id)
    srt=sys.service.export(sys.project.id,track.id,'srt',tmp_path/'ខ្មែរ.srt'); vtt=sys.service.export(sys.project.id,track.id,'vtt',tmp_path/'ខ្មែរ.vtt'); ass=sys.service.export(sys.project.id,track.id,'ass',tmp_path/'ខ្មែរ.ass')
    assert 'សូមស្វាគមន៍' in srt.read_text(encoding='utf-8'); assert vtt.read_text(encoding='utf-8').startswith('WEBVTT'); assert '[V4+ Styles]' in ass.read_text(encoding='utf-8')
    assert format_srt_timestamp(3723004)=='01:02:03,004'


def test_ass_color_conversion_and_escaping():
    assert ass_color('#112233')=='&H00332211&'; assert ass_color('#11223380')=='&H7F332211&'
    escaped=escape_ass_text('{bad}\\tag\nnext'); assert '{bad}' not in escaped and r'\N' in escaped


def test_srt_and_vtt_round_trip(tmp_path: Path):
    style=SubtitleStyle(project_id='p'); track=SimpleNamespace()
    cue=SubtitleCue(track_id='t',order=0,start_ms=1234,end_ms=4567,text='Hello\nWorld')
    from domain.subtitle import SubtitleTrack
    tr=SubtitleTrack(project_id='p',name='T',language='en')
    imp=SubtitleImportService()
    sp=tmp_path/'x.srt'; SRTExporter().export(tr,[cue],style,sp); parsed=imp.parse(sp,'new'); assert parsed[0].start_ms==1234 and parsed[0].text=='Hello\nWorld'
    vp=tmp_path/'x.vtt'; VTTExporter().export(tr,[cue],style,vp); parsed2=imp.parse(vp,'new'); assert parsed2[0].end_ms==4567


def test_style_serialization_preset_application_and_builtin_protection(tmp_path: Path):
    sys=make_system(tmp_path); track=sys.service.create_manual(sys.project.id,'en',preset_id='bold'); _,style,_=sys.service.get(sys.project.id,track.id); assert style.font_weight==800
    style=sys.service.update_style(sys.project.id,track.id,{'font_size':70.0}); preset_id=sys.presets.save_user_preset('My Style',style); assert any(p['id']==preset_id for p in sys.presets.list_presets())
    sys.presets.delete_user_preset(preset_id); assert not any(p['id']==preset_id for p in sys.presets.list_presets())
    with pytest.raises(ValueError): sys.presets.delete_user_preset('clean')


def test_active_cue_and_word_lookup(tmp_path: Path):
    sys=make_system(tmp_path); track=sys.service.create_from_transcript(sys.project.id,sys.transcript.id); cue=sys.service.active_cue(sys.project.id,track.id,1000); assert cue and cue.id
    assert sys.service.active_word(cue,1000).text=='today'
    assert sys.service.active_cue(sys.project.id,track.id,9000) is None


def test_source_sync_preserves_manual_edit_and_marks_changed(tmp_path: Path):
    sys=make_system(tmp_path); track=sys.service.create_from_transcript(sys.project.id,sys.transcript.id); cue=sys.subtitles.cues(track.id)[0]
    sys.service.update_cue(sys.project.id,track.id,cue.id,text='Short custom caption')
    sys.transcripts.update_segment_text(sys.transcript.id,'seg-1','Source transcript changed',edited=True)
    result=sys.service.sync_source(sys.project.id,track.id); updated=sys.subtitles.cue(cue.id); track2=sys.subtitles.get_track(track.id)
    assert result['changed']==1; assert updated.text=='Short custom caption'; assert updated.metadata['sourceChanged'] is True; assert track2.status_code=='outdated'


def test_source_missing_keeps_track_editable(tmp_path: Path):
    sys=make_system(tmp_path); track=sys.service.create_from_transcript(sys.project.id,sys.transcript.id); sys.transcripts.delete(sys.project.id,sys.transcript.id)
    result=sys.service.sync_source(sys.project.id,track.id); current=sys.subtitles.get_track(track.id); assert current.status_code=='source_missing'; assert result['removed']==2; assert len(sys.subtitles.cues(track.id))==2


def test_duplicate_track_has_independent_ids_and_style(tmp_path: Path):
    sys=make_system(tmp_path); track=sys.service.create_from_transcript(sys.project.id,sys.transcript.id); clone=sys.service.duplicate_track(sys.project.id,track.id)
    assert clone.id!=track.id; assert clone.style_id!=track.style_id
    assert {q.id for q in sys.subtitles.cues(clone.id)}.isdisjoint({q.id for q in sys.subtitles.cues(track.id)})


def test_track_delete_does_not_delete_source(tmp_path: Path):
    sys=make_system(tmp_path); track=sys.service.create_from_transcript(sys.project.id,sys.transcript.id); sys.service.delete_track(sys.project.id,track.id)
    assert sys.transcripts.get(sys.transcript.id) is not None


def test_restart_persistence_text_timing_style_default(tmp_path: Path):
    sys=make_system(tmp_path); track=sys.service.create_manual(sys.project.id,'km',preset_id='news'); cue=sys.service.add_cue(sys.project.id,track.id,500,'សួស្តី',2500); sys.service.update_cue(sys.project.id,track.id,cue.id,start_ms=700,end_ms=3200); sys.service.update_style(sys.project.id,track.id,{'font_size':58.0}); sys.service.set_default(sys.project.id,track.id)
    reopened=SubtitleRepository(SQLiteDatabase(sys.db.path)); tr=reopened.get_track(track.id); st=reopened.style(tr.style_id); q=reopened.cues(track.id)[0]
    assert tr.is_default and st.font_size==58.0 and q.text=='សួស្តី' and (q.start_ms,q.end_ms)==(700,3200)


def test_project_delete_cascades_subtitles_but_not_user_presets(tmp_path: Path):
    sys=make_system(tmp_path); track=sys.service.create_manual(sys.project.id,'en'); _,style,_=sys.service.get(sys.project.id,track.id); preset=sys.presets.save_user_preset('Global',style)
    sys.projects.delete(sys.project.id); assert sys.subtitles.get_track(track.id) is None; assert any(p['id']==preset for p in sys.subtitles.user_presets())


def test_ffmpeg_filter_escapes_windows_unicode_paths():
    from services.subtitle_preview_service import escape_ffmpeg_subtitle_path, build_subtitle_filter
    value=escape_ffmpeg_subtitle_path(r"C:\Video Files\ខ្មែរ\track [1].ass")
    assert "C\\:" in value
    assert "ខ្មែរ" in value
    assert r"\[1\]" in value
    assert "ass='" in build_subtitle_filter(r"C:\Video Files\ខ្មែរ\track.ass")


def test_large_track_binary_lookup_and_validation(tmp_path: Path):
    sys=make_system(tmp_path); track=sys.service.create_manual(sys.project.id,'en')
    cues=[SubtitleCue(track_id=track.id,order=i,start_ms=i*2000,end_ms=i*2000+1500,text=f'Caption {i}') for i in range(1000)]
    sys.subtitles.replace_cues(sys.project.id,track.id,cues)
    assert len(sys.subtitles.cues(track.id))==1000
    active=sys.service.active_cue(sys.project.id,track.id,1_234_100)
    assert active is not None and active.order==617
    issues=sys.service.validate_track(sys.project.id,track.id)
    assert isinstance(issues,list)


def test_project_subtitle_duplication_remaps_bilingual_source_ids(tmp_path: Path):
    sys=make_system(tmp_path)
    track=sys.service.create_bilingual(sys.project.id,sys.transcript.id,sys.translation.id)
    target_root=tmp_path/'Projects'/'copy'; target_root.mkdir(parents=True)
    target=Project(project_id='project-copy',title='Copy',workflow='video',language='en',project_path=str(target_root)); sys.projects.create(target)
    count=sys.service.duplicate_project_subtitles(
        sys.project.id,target.id,
        transcript_map={'tr-1':'tr-copy'},translation_map={'tx-1':'tx-copy'},
        transcript_segment_map={'seg-1':'seg-copy-1','seg-2':'seg-copy-2'},
        translation_segment_map={'txs-1':'txs-copy-1','txs-2':'txs-copy-2'},
    )
    assert count==1
    cloned=sys.subtitles.list_for_project(target.id)[0]
    assert cloned.source_id=='tx-copy'
    assert cloned.metadata['transcriptId']=='tr-copy'
    assert [q.source_segment_id for q in sys.subtitles.cues(cloned.id)]==['seg-copy-1','seg-copy-2']
    assert cloned.id!=track.id and cloned.style_id!=track.style_id


def test_basic_ass_import_round_trip(tmp_path: Path):
    sys=make_system(tmp_path); track=sys.service.create_from_translation(sys.project.id,sys.translation.id)
    path=sys.service.export(sys.project.id,track.id,'ass',tmp_path/'roundtrip.ass')
    imported=SubtitleImportService().parse(path,'new-track')
    assert len(imported)==2
    assert imported[0].start_ms==0 and 'សូមស្វាគមន៍' in imported[0].text
