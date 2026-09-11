from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from domain.generated_audio import GeneratedAudio, GeneratedAudioStatus
from domain.media import MediaAsset, MediaType
from domain.project import Project
from domain.scene import Scene, SceneSourceStatus, SceneStatus
from domain.scene_overlay import SceneOverlay
from domain.subtitle import SubtitleTrack
from domain.subtitle_style import SubtitleStyle
from services.project_service import ProjectService
from services.scene_generation_service import SceneGenerationService
from services.scene_preview_service import ScenePreviewService
from services.scene_service import SceneInvalidOverlay, SceneInvalidSourceRange, SceneInvalidTransition, SceneService
from services.scene_validation_service import SceneValidationService
from services.script_analysis_service import ScriptAnalysisService
from services.script_service import ScriptService
from storage.database import SQLiteDatabase
from storage.repositories.generated_audio_repository import GeneratedAudioRepository
from storage.repositories.media_repository import MediaRepository
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.scene_repository import SceneRepository
from storage.repositories.script_repository import ScriptRepository
from storage.repositories.subtitle_repository import SubtitleRepository
from storage.repositories.transcript_repository import TranscriptRepository


def make_system(tmp_path: Path):
    db=SQLiteDatabase(tmp_path/'app.db'); db.initialize()
    projects=ProjectRepository(db); media=MediaRepository(db); scripts=ScriptRepository(db); audio=GeneratedAudioRepository(db); subtitles=SubtitleRepository(db); transcripts=TranscriptRepository(db); scenes=SceneRepository(db)
    root=tmp_path/'Projects'/'demo'; root.mkdir(parents=True)
    project=Project(project_id='p1',title='Demo',workflow='video',language='en',project_path=str(root)); projects.create(project)
    img=root/'media'/'images'/'cover.png'; img.parent.mkdir(parents=True,exist_ok=True); img.write_bytes(b'img')
    vid=root/'media'/'video'/'clip.mp4'; vid.parent.mkdir(parents=True,exist_ok=True); vid.write_bytes(b'vid')
    media.create(MediaAsset(asset_id='img1',project_id=project.id,media_type=MediaType.IMAGE,name='cover.png',original_path=str(img),project_path=str(img),file_size=3,width=1080,height=1080,extension='.png'))
    media.create(MediaAsset(asset_id='vid1',project_id=project.id,media_type=MediaType.VIDEO,name='clip.mp4',original_path=str(vid),project_path=str(vid),file_size=3,duration_ms=10000,width=1920,height=1080,extension='.mp4'))
    analysis=ScriptAnalysisService(); script_service=ScriptService(scripts,projects,analysis); script,sections=script_service.load_or_create(project.id)
    sections[0].content='Welcome to the update.'; script_service.save_section(project.id,sections[0])
    wav=root/'audio'/'narration'/'take.wav'; wav.parent.mkdir(parents=True,exist_ok=True); wav.write_bytes(b'RIFFfake')
    item=GeneratedAudio(generated_audio_id='aud1',project_id=project.id,script_id=script.id,section_id=sections[0].id,engine='fake',model_id='fake',language='en',voice_mode='default',text_hash='x',file_path=str(wav),duration_ms=7200,status=GeneratedAudioStatus.COMPLETED)
    audio.create(item)
    style=SubtitleStyle(project_id=project.id); track=SubtitleTrack(track_id='sub1',project_id=project.id,name='English',language='en',style_id=style.id,is_default=True); subtitles.create_track(track,style,[])
    generation=SceneGenerationService(analysis,audio); validation=SceneValidationService(media,audio,subtitles); preview=ScenePreviewService(); service=SceneService(scenes,projects,media,audio,subtitles,script_service,transcripts,generation,validation,preview)
    return SimpleNamespace(db=db,projects=projects,media=media,scripts=scripts,audio=audio,subtitles=subtitles,transcripts=transcripts,scenes=scenes,project=project,script_service=script_service,script=script,sections=sections,service=service)


def test_phase13_schema_and_scene_serialization(tmp_path: Path):
    sys=make_system(tmp_path); assert sys.db.current_version() == 16
    scene=Scene(project_id='p',order=2,name='Main',duration_ms=8000); data=scene.to_dict(); assert data['order']==2 and data['durationMs']==8000
    with sys.db.connect() as c: tables={r['name'] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {'scenes','scene_layers','scene_overlays'} <= tables


def test_add_delete_reorder_duplicate_and_total_duration(tmp_path: Path):
    s=make_system(tmp_path); a=s.service.add_scene('p1','A',1000); b=s.service.add_scene('p1','B',2000); c=s.service.duplicate_scene('p1',a.id)
    assert [x.order for x in s.service.list_scenes('p1')]==[0,1,2]
    s.service.move_scene('p1',c.id,0); assert s.service.list_scenes('p1')[0].id==c.id
    s.service.set_enabled('p1',b.id,False); assert s.service.project_summary('p1')['totalDurationMs']==2000
    s.service.delete_scene('p1',a.id); assert [x.order for x in s.service.list_scenes('p1')]==[0,1]


def test_empty_scene_incomplete_then_image_ready(tmp_path: Path):
    s=make_system(tmp_path); scene=s.service.add_scene('p1'); assert s.service.list_scenes('p1')[0].status_code=='incomplete'
    scene=s.service.assign_media('p1',scene.id,'img1'); assert scene.primary_media_id=='img1'; assert s.service.list_scenes('p1')[0].status_code=='ready'
    scene=s.service.set_fit_mode('p1',scene.id,'fit'); assert scene.fit_mode=='fit'


def test_video_range_and_longer_than_video_warning(tmp_path: Path):
    s=make_system(tmp_path); scene=s.service.add_scene('p1',duration_ms=12000); s.service.assign_media('p1',scene.id,'vid1')
    codes={i.code for i in s.service.validate_scene('p1',scene.id)}; assert 'video_too_short' in codes
    with pytest.raises(SceneInvalidSourceRange): s.service.set_video_range('p1',scene.id,9000,11000)
    s.service.set_video_range('p1',scene.id,1000,9000); assert s.scenes.get(scene.id).source_start_ms==1000


def test_missing_and_replace_media(tmp_path: Path):
    s=make_system(tmp_path); scene=s.service.add_scene('p1'); s.service.assign_media('p1',scene.id,'img1'); s.media.delete('img1')
    codes={i.code for i in s.service.validate_scene('p1',scene.id)}; assert 'missing_media' in codes
    s.service.replace_media('p1',scene.id,'vid1'); assert s.scenes.get(scene.id).primary_media_id=='vid1'


def test_narration_assignment_warning_and_match_duration(tmp_path: Path):
    s=make_system(tmp_path); scene=s.service.add_scene('p1',duration_ms=3000); s.service.assign_narration('p1',scene.id,'aud1')
    assert 'narration_too_long' in {i.code for i in s.service.validate_scene('p1',scene.id)}
    updated=s.service.match_duration_to_narration('p1',scene.id); assert updated.duration_ms==7200


def test_audio_settings_and_subtitle_assignment(tmp_path: Path):
    s=make_system(tmp_path); scene=s.service.add_scene('p1'); scene=s.service.set_audio('p1',scene.id,source_enabled=True,source_volume=.25,narration_volume=.8)
    assert scene.audio.source_audio_enabled and scene.audio.source_audio_volume==.25
    assert s.service.assign_subtitle('p1',scene.id,'sub1').subtitle_track_id=='sub1'


def test_transition_validation(tmp_path: Path):
    s=make_system(tmp_path); scene=s.service.add_scene('p1',duration_ms=4000)
    assert s.service.set_transition('p1',scene.id,'fade',500).transition_out.type_code=='fade'
    with pytest.raises(SceneInvalidTransition): s.service.set_transition('p1',scene.id,'crossfade',3000)


def test_overlay_creation_order_unicode_and_validation(tmp_path: Path):
    s=make_system(tmp_path); scene=s.service.add_scene('p1',duration_ms=5000)
    h=s.service.add_text_overlay('p1',scene.id,'ព័ត៌មានថ្មីថ្ងៃនេះ','headline'); low=s.service.add_lower_third('p1',scene.id,'សែម បញ្ញា','អ្នកបង្កើត')
    logo=s.service.add_logo('p1',scene.id,'img1'); assert [x.order for x in s.service.overlays('p1',scene.id)]==[0,1,2]
    changed=s.service.update_overlay('p1',scene.id,h.id,{'x':.2,'y':.2,'opacity':.5}); assert changed.text.startswith('ព័ត៌មាន') and changed.opacity==.5
    s.service.move_overlay('p1',scene.id,logo.id,-1); assert s.service.overlays('p1',scene.id)[1].id==logo.id
    with pytest.raises(SceneInvalidOverlay): s.service.update_overlay('p1',scene.id,h.id,{'x':1.2})
    s.service.delete_overlay('p1',scene.id,low.id); assert len(s.service.overlays('p1',scene.id))==2


def test_create_scenes_from_script_excludes_disabled_and_uses_narration(tmp_path: Path):
    s=make_system(tmp_path); s.script_service.set_section_enabled('p1',s.sections[1].id,False)
    created=s.service.create_from_script('p1'); assert len(created)==2; assert created[0].name=='Hook'; assert created[0].narration_audio_id=='aud1'; assert created[0].duration_ms==7200
    assert all(x.script_section_id!=s.sections[1].id for x in created)


def test_script_source_change_mandatory_preserves_scene_edits(tmp_path: Path):
    s=make_system(tmp_path); created=s.service.create_from_script('p1'); scene=created[0]; s.service.assign_media('p1',scene.id,'img1'); s.service.add_text_overlay('p1',scene.id,'Custom','headline')
    sec=s.sections[0]; sec.content='Changed source text'; s.script_service.save_section('p1',sec); result=s.service.sync_with_script('p1',create_new=False)
    current=s.scenes.get(scene.id); assert result['changed']==1 and current.source_status_code=='source_changed'; assert current.primary_media_id=='img1'; assert len(s.scenes.overlays(scene.id))==1
    s.service.sync_scene_from_script('p1',scene.id); assert s.scenes.get(scene.id).source_status_code=='current'


def test_script_source_missing_keeps_scene(tmp_path: Path):
    s=make_system(tmp_path); scene=s.service.create_from_script('p1')[0]; s.script_service.delete_section('p1',s.sections[0].id); result=s.service.sync_with_script('p1',create_new=False)
    assert result['missing']==1 and s.scenes.get(scene.id).source_status_code=='source_missing'


def test_sync_new_script_section_creates_only_new_scene(tmp_path: Path):
    s=make_system(tmp_path); s.service.create_from_script('p1'); new=s.script_service.add_section('p1','Extra'); result=s.service.sync_with_script('p1'); assert result['added']==1
    ids=[x.script_section_id for x in s.service.list_scenes('p1')]; assert ids.count(new.id)==1


def test_render_spec_and_project_sequence(tmp_path: Path):
    s=make_system(tmp_path); a=s.service.add_scene('p1','A',1000); s.service.assign_media('p1',a.id,'img1'); s.service.add_text_overlay('p1',a.id,'Hello','headline'); b=s.service.add_scene('p1','B',2500); s.service.update_general('p1',b.id,background_color='#000000')
    spec=s.service.build_scene_render_spec('p1',a.id); assert spec['visual']['mediaId']=='img1' and spec['overlays'][0]['text']=='Hello'
    sequence=s.service.build_project_scene_sequence('p1'); assert [(x['startMs'],x['endMs']) for x in sequence['scenes']]==[(0,1000),(1000,3500)]; assert sequence['totalDurationMs']==3500


def test_scene_delete_does_not_delete_shared_assets(tmp_path: Path):
    s=make_system(tmp_path); scene=s.service.add_scene('p1'); s.service.assign_media('p1',scene.id,'img1'); s.service.assign_narration('p1',scene.id,'aud1'); s.service.assign_subtitle('p1',scene.id,'sub1'); s.service.delete_scene('p1',scene.id)
    assert s.media.get_by_id('img1') is not None and s.audio.get('aud1') is not None and s.subtitles.get_track('sub1') is not None


def test_restart_persistence_with_khmer_overlay(tmp_path: Path):
    s=make_system(tmp_path); scene=s.service.add_scene('p1','ខ្មែរ',6500); s.service.assign_media('p1',scene.id,'img1'); s.service.set_transition('p1',scene.id,'fade',300); ov=s.service.add_text_overlay('p1',scene.id,'ព័ត៌មានបច្ចេកវិទ្យាថ្មី','headline'); s.service.update_overlay('p1',scene.id,ov.id,{'x':.15,'y':.18})
    repo=SceneRepository(SQLiteDatabase(s.db.path)); loaded=repo.get(scene.id); overlays=repo.overlays(scene.id); assert loaded.name=='ខ្មែរ' and loaded.transition_out.type_code=='fade'; assert overlays[0].text=='ព័ត៌មានបច្ចេកវិទ្យាថ្មី' and overlays[0].x==.15


def test_100_scene_behavior(tmp_path: Path):
    s=make_system(tmp_path)
    for i in range(100): s.service.add_scene('p1',f'Scene {i+1}',1000+i)
    assert len(s.service.list_scenes('p1'))==100; s.service.move_scene('p1',s.service.list_scenes('p1')[-1].id,0); assert s.service.list_scenes('p1')[0].name=='Scene 100'
    assert s.service.project_summary('p1')['sceneCount']==100; assert len(s.service.build_project_scene_sequence('p1')['scenes'])==100


def test_create_scenes_from_transcript_groups_segments(tmp_path: Path):
    from domain.transcript import Transcript, TranscriptStatus
    from domain.transcript_segment import TranscriptSegment
    s=make_system(tmp_path)
    transcript=Transcript(transcript_id='tr1',project_id='p1',media_id='vid1',engine='fake',model_id='whisper-small',language_mode='en',detected_language='en',duration_ms=22000,status=TranscriptStatus.READY,active=True)
    segments=[
        TranscriptSegment(transcript_id='tr1',order=0,start_ms=0,end_ms=4000,text='Opening.'),
        TranscriptSegment(transcript_id='tr1',order=1,start_ms=4000,end_ms=9000,text='First detail.'),
        TranscriptSegment(transcript_id='tr1',order=2,start_ms=9000,end_ms=16000,text='Second detail.'),
        TranscriptSegment(transcript_id='tr1',order=3,start_ms=16000,end_ms=22000,text='Closing.'),
    ]
    s.transcripts.create_with_segments(transcript,segments)
    scenes=s.service.create_from_transcript('p1','tr1',group_ms=10000,append=True)
    assert len(scenes)==3
    assert [x.duration_ms for x in scenes]==[9000,7000,6000]
    assert scenes[0].transcript_segment_id==segments[0].id
    assert all(x.primary_media_id=='vid1' for x in scenes)


def test_project_scene_duplication_remaps_all_project_owned_ids(tmp_path: Path):
    s=make_system(tmp_path)
    target_root=tmp_path/'Projects'/'copy'; target_root.mkdir(parents=True)
    target=Project(project_id='p2',title='Copy',workflow='video',language='en',project_path=str(target_root)); s.projects.create(target)
    scene=s.service.add_scene('p1','Mapped',5000)
    scene=s.service.assign_media('p1',scene.id,'img1')
    scene=s.service.assign_narration('p1',scene.id,'aud1')
    scene=s.service.assign_subtitle('p1',scene.id,'sub1')
    scene.script_section_id=s.sections[0].id
    scene.transcript_segment_id='trseg-old'
    scene.translation_segment_id='tlseg-old'
    s.scenes.update(scene)
    logo=s.service.add_logo('p1',scene.id,'img1')
    mapping=s.service.duplicate_project_scenes(
        'p1','p2',media_map={'img1':'img2'},audio_map={'aud1':'aud2'},script_section_map={s.sections[0].id:'sec2'},
        transcript_segment_map={'trseg-old':'trseg2'},translation_segment_map={'tlseg-old':'tlseg2'},subtitle_track_map={'sub1':'sub2'},
    )
    clone=s.scenes.get(mapping[scene.id]); assert clone is not None
    assert clone.project_id=='p2' and clone.primary_media_id=='img2' and clone.narration_audio_id=='aud2'
    assert clone.subtitle_track_id=='sub2' and clone.script_section_id=='sec2'
    assert clone.transcript_segment_id=='trseg2' and clone.translation_segment_id=='tlseg2'
    clone_overlays=s.scenes.overlays(clone.id); assert clone_overlays[0].id!=logo.id and clone_overlays[0].asset_id=='img2'
    assert not {clone.primary_media_id,clone.narration_audio_id,clone.subtitle_track_id,clone.script_section_id,clone.transcript_segment_id,clone.translation_segment_id} & {'img1','aud1','sub1',s.sections[0].id,'trseg-old','tlseg-old'}


def test_project_delete_cascades_scene_records_only(tmp_path: Path):
    s=make_system(tmp_path); scene=s.service.add_scene('p1'); s.service.add_text_overlay('p1',scene.id,'Owned overlay','headline')
    s.projects.delete('p1')
    assert s.scenes.get(scene.id) is None and s.scenes.overlays(scene.id)==[]
