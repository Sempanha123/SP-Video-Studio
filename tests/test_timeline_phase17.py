from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import time

import pytest

from commands.command_stack import CommandStack
from domain.generated_audio import GeneratedAudio, GeneratedAudioStatus
from domain.media import MediaAsset, MediaType
from domain.project import Project
from domain.subtitle import SubtitleTrack
from domain.subtitle_cue import SubtitleCue
from domain.subtitle_style import SubtitleStyle
from domain.timeline import Timeline
from domain.timeline_marker import TimelineMarker
from domain.timeline_track import TimelineTrack
from services.scene_generation_service import SceneGenerationService
from services.scene_preview_service import ScenePreviewService
from services.scene_service import SceneService
from services.scene_validation_service import SceneValidationService
from services.script_analysis_service import ScriptAnalysisService
from services.script_service import ScriptService
from services.timeline_edit_service import TimelineClipLocked, TimelineEditService, TimelineInvalidSplit, TimelineInvalidTrim
from services.timeline_mapping_service import TimelineMappingService
from services.timeline_service import TimelineService
from services.timeline_snap_service import TimelineSnapService
from services.timeline_validation_service import TimelineValidationService
from storage.database import SQLiteDatabase
from storage.repositories.generated_audio_repository import GeneratedAudioRepository
from storage.repositories.media_repository import MediaRepository
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.scene_repository import SceneRepository
from storage.repositories.script_repository import ScriptRepository
from storage.repositories.subtitle_repository import SubtitleRepository
from storage.repositories.timeline_repository import TimelineRepository
from storage.repositories.transcript_repository import TranscriptRepository


class SubtitleFacade:
    def __init__(self, repo: SubtitleRepository): self.repo=repo
    def update_cue(self, project_id: str, track_id: str, cue_id: str, *, start_ms=None, end_ms=None, **_):
        cue=self.repo.cue(cue_id)
        if cue is None or cue.track_id!=track_id: raise KeyError(cue_id)
        if start_ms is not None: cue.start_ms=int(start_ms)
        if end_ms is not None: cue.end_ms=int(end_ms)
        cue.edited=True
        return self.repo.update_cue(project_id,cue)


def make_system(tmp_path: Path):
    db=SQLiteDatabase(tmp_path/'app.db'); db.initialize()
    projects=ProjectRepository(db); media=MediaRepository(db); scripts=ScriptRepository(db); audio=GeneratedAudioRepository(db); subtitles=SubtitleRepository(db); transcripts=TranscriptRepository(db); scenes=SceneRepository(db); timeline=TimelineRepository(db)
    root=tmp_path/'Projects'/'ព័ត៌មាន Demo'; root.mkdir(parents=True)
    project=Project(project_id='p1',title='Demo',workflow='video',language='en',project_path=str(root),fps=30.0); projects.create(project)
    img=root/'media'/'images'/'cover.png'; img.parent.mkdir(parents=True,exist_ok=True); img.write_bytes(b'img')
    vid=root/'media'/'video'/'clip.mp4'; vid.parent.mkdir(parents=True,exist_ok=True); vid.write_bytes(b'vid')
    media.create(MediaAsset(asset_id='img1',project_id='p1',media_type=MediaType.IMAGE,name='cover.png',original_path=str(img),project_path=str(img),file_size=3,width=1080,height=1080,extension='.png'))
    media.create(MediaAsset(asset_id='vid1',project_id='p1',media_type=MediaType.VIDEO,name='clip.mp4',original_path=str(vid),project_path=str(vid),file_size=3,duration_ms=12000,width=1920,height=1080,fps=30,codec='h264',audio_codec='aac',extension='.mp4'))
    analysis=ScriptAnalysisService(); script_service=ScriptService(scripts,projects,analysis); script,sections=script_service.load_or_create('p1')
    sections[0].content='Welcome to the update.'; script_service.save_section('p1',sections[0])
    wav=root/'audio'/'narration'/'take.wav'; wav.parent.mkdir(parents=True,exist_ok=True); wav.write_bytes(b'RIFFfake')
    audio.create(GeneratedAudio(generated_audio_id='aud1',project_id='p1',script_id=script.id,section_id=sections[0].id,engine='fake',model_id='fake',language='en',voice_mode='default',text_hash='x',file_path=str(wav),duration_ms=4500,status=GeneratedAudioStatus.COMPLETED,metadata={'voiceName':'Narrator'}))
    style=SubtitleStyle(project_id='p1'); track=SubtitleTrack(track_id='sub1',project_id='p1',name='English',language='en',style_id=style.id,is_default=True)
    cues=[SubtitleCue(track_id='sub1',order=0,start_ms=500,end_ms=2200,text='Hello'), SubtitleCue(track_id='sub1',order=1,start_ms=4300,end_ms=6200,text='ព័ត៌មានថ្មីសម្រាប់ថ្ងៃនេះ')]
    subtitles.create_track(track,style,cues)
    generation=SceneGenerationService(analysis,audio); validation=SceneValidationService(media,audio,subtitles); preview=ScenePreviewService(); scene_service=SceneService(scenes,projects,media,audio,subtitles,script_service,transcripts,generation,validation,preview)
    subtitle_facade=SubtitleFacade(subtitles); stack=CommandStack(150)
    mapping=TimelineMappingService(scenes,media,audio,subtitles,timeline); edits=TimelineEditService(scene_service,scenes,subtitle_facade,subtitles,timeline,stack); tservice=TimelineService(timeline,projects,mapping,edits,TimelineSnapService(),TimelineValidationService())
    return SimpleNamespace(db=db,projects=projects,media=media,scripts=scripts,audio=audio,subtitles=subtitles,scenes=scenes,timeline=timeline,project=project,scene_service=scene_service,mapping=mapping,edits=edits,service=tservice,cues=cues)


def add_standard_scenes(s):
    a=s.scene_service.add_scene('p1','Image',5000); s.scene_service.assign_media('p1',a.id,'img1'); s.scene_service.add_text_overlay('p1',a.id,'ព័ត៌មានថ្មីថ្ងៃនេះ','headline')
    b=s.scene_service.add_scene('p1','Video',6000); s.scene_service.assign_media('p1',b.id,'vid1'); s.scene_service.set_video_range('p1',b.id,1000,7000); s.scene_service.assign_narration('p1',b.id,'aud1'); s.scene_service.set_audio('p1',b.id,source_enabled=True,source_volume=.35,narration_volume=.8)
    c=s.scene_service.add_scene('p1','Outro',3000); s.scene_service.update_general('p1',c.id,background_color='#111111')
    return a,b,c


def test_phase17_schema_tracks_and_state(tmp_path: Path):
    s=make_system(tmp_path); assert s.db.current_version()==14
    with s.db.connect() as c: tables={r['name'] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {'timeline_state','timeline_tracks','timeline_markers'} <= tables
    tracks=s.timeline.ensure_tracks('p1'); assert [x.type_code for x in tracks][:5]==['overlay','video','subtitle','voice','source_audio']
    state=s.timeline.get_state('p1'); assert state.snap_enabled and state.zoom_level==80.0
    assert Timeline('p1').to_dict()['projectId']=='p1'; assert TimelineTrack('p','video','Video',0).type_code=='video'; assert TimelineMarker('p',100,'Beat').label=='Beat'


def test_scene_derived_tracks_narration_audio_overlay_and_subtitles(tmp_path: Path):
    s=make_system(tmp_path); a,b,_=add_standard_scenes(s); clips=s.mapping.build_clips('p1')
    assert [c.source_type for c in clips['video']]==['scene_image','scene_video','scene_video']
    assert len(clips['overlay'])==1 and clips['overlay'][0].label.startswith('ព័ត៌មាន')
    assert len(clips['voice'])==1 and clips['voice'][0].metadata['audioId']=='aud1'
    assert len(clips['source_audio'])==1 and clips['source_audio'][0].source_id==b.id
    assert [x.label for x in clips['subtitle']]==['Hello','ព័ត៌មានថ្មីសម្រាប់ថ្ងៃនេះ']


def test_transition_overlap_duration_and_time_mapping(tmp_path: Path):
    s=make_system(tmp_path); a,b,c=add_standard_scenes(s); s.scene_service.set_transition('p1',a.id,'crossfade',500)
    assert s.service.duration_ms('p1')==13500
    ranges=s.mapping.scene_ranges('p1'); assert [(x['startMs'],x['endMs']) for x in ranges]==[(0,5000),(4500,10500),(10500,13500)]
    assert s.service.project_to_scene_time('p1',4700)==(b.id,200)  # overlap prefers incoming scene
    assert s.service.scene_to_project_time('p1',c.id,100)==10600


def test_reorder_and_ripple_storyboard_sync(tmp_path: Path):
    s=make_system(tmp_path); a,b,c=add_standard_scenes(s); s.edits.reorder_scene('p1',c.id,0)
    assert [x.name for x in s.scene_service.list_scenes('p1')]==['Outro','Image','Video']
    before=s.mapping.scene_ranges('p1'); s.edits.trim_scene_right('p1',c.id,5000); after=s.mapping.scene_ranges('p1')
    assert s.scenes.get(c.id).duration_ms==5000
    assert int(after[1]['startMs'])-int(before[1]['startMs'])==2000
    # Storyboard changes are immediately visible in timeline because Scene is canonical.
    s.scene_service.update_general('p1',a.id,duration_ms=7000); assert next(x for x in s.mapping.build_clips('p1')['video'] if x.source_id==a.id).duration_ms==7000


def test_video_right_and_left_trim_non_destructive(tmp_path: Path):
    s=make_system(tmp_path); _,b,_=add_standard_scenes(s)
    s.edits.trim_scene_right('p1',b.id,4000); scene=s.scenes.get(b.id); assert scene.duration_ms==4000 and scene.source_start_ms==1000 and scene.source_end_ms==5000
    s.edits.trim_scene_left('p1',b.id,1000); scene=s.scenes.get(b.id); assert scene.duration_ms==3000 and scene.source_start_ms==2000 and scene.source_end_ms==5000
    with pytest.raises(TimelineInvalidTrim): s.edits.trim_scene_right('p1',b.id,11001)


def test_image_trim_and_minimum_duration(tmp_path: Path):
    s=make_system(tmp_path); a,_,_=add_standard_scenes(s); s.edits.trim_scene_right('p1',a.id,2500); assert s.scenes.get(a.id).duration_ms==2500
    s.edits.trim_scene_right('p1',a.id,1); assert s.scenes.get(a.id).duration_ms==100
    with pytest.raises(TimelineInvalidTrim): s.edits.trim_scene_left('p1',a.id,99)


def test_video_split_source_ranges_and_image_split(tmp_path: Path):
    s=make_system(tmp_path); a,b,_=add_standard_scenes(s); second=s.edits.split_scene('p1',b.id,2500); first=s.scenes.get(b.id); part2=s.scenes.get(second)
    assert (first.duration_ms,part2.duration_ms)==(2500,3500); assert (first.source_start_ms,first.source_end_ms)==(1000,3500); assert (part2.source_start_ms,part2.source_end_ms)==(3500,7000); assert part2.narration_audio_id==''
    second_img=s.edits.split_scene('p1',a.id,2000); assert [s.scenes.get(a.id).duration_ms,s.scenes.get(second_img).duration_ms]==[2000,3000]
    assert s.scenes.get(second_img).primary_media_id=='img1'
    with pytest.raises(TimelineInvalidSplit): s.edits.split_scene('p1',a.id,50)


def test_duplicate_delete_and_undo_redo(tmp_path: Path):
    s=make_system(tmp_path); a,_,_=add_standard_scenes(s); count=len(s.scene_service.list_scenes('p1')); clone=s.edits.duplicate_scene('p1',a.id); assert len(s.scene_service.list_scenes('p1'))==count+1
    assert s.edits.undo() and s.scenes.get(clone) is None; assert s.edits.redo() and s.scenes.get(clone) is not None
    s.edits.delete_scene('p1',clone); assert s.scenes.get(clone) is None; assert s.edits.undo() and s.scenes.get(clone) is not None


def test_undo_trim_split_reorder_and_command_coalescing(tmp_path: Path):
    s=make_system(tmp_path); a,b,c=add_standard_scenes(s)
    s.edits.trim_scene_right('p1',a.id,4000); s.edits.trim_scene_right('p1',a.id,3500)
    # Timeline trim commands are separate structural commits; audio sliders below coalesce.
    assert s.scenes.get(a.id).duration_ms==3500; s.edits.undo(); assert s.scenes.get(a.id).duration_ms==4000; s.edits.redo(); assert s.scenes.get(a.id).duration_ms==3500
    sid=s.edits.split_scene('p1',b.id,2000); assert s.scenes.get(sid); s.edits.undo(); assert s.scenes.get(sid) is None; s.edits.redo(); assert s.scenes.get(sid)
    old=[x.id for x in s.scene_service.list_scenes('p1')]; s.edits.reorder_scene('p1',c.id,0); s.edits.undo(); assert [x.id for x in s.scene_service.list_scenes('p1')]==old
    s.edits.set_scene_audio('p1',b.id,narration_volume=.7); depth=len(s.edits.stack._undo); s.edits.set_scene_audio('p1',b.id,narration_volume=.6); assert len(s.edits.stack._undo)==depth


def test_track_lock_mute_visibility_and_render_semantics_data(tmp_path: Path):
    s=make_system(tmp_path); a,b,_=add_standard_scenes(s); s.timeline.ensure_tracks('p1'); s.edits.set_track_state('p1','video',locked=True)
    with pytest.raises(TimelineClipLocked): s.edits.trim_scene_right('p1',a.id,3000)
    s.edits.set_track_state('p1','video',locked=False); s.edits.set_track_state('p1','voice',muted=True); s.edits.set_track_state('p1','overlay',visible=False)
    assert s.timeline.track_by_type('p1','voice').muted and not s.timeline.track_by_type('p1','overlay').visible
    clips=s.mapping.build_clips('p1'); assert clips['voice'][0].muted


def test_overlay_move_trim_delete_undo_and_active_lookup(tmp_path: Path):
    s=make_system(tmp_path); a,_,_=add_standard_scenes(s); ov=s.scenes.overlays(a.id)[0]
    s.edits.set_overlay_timing('p1',a.id,ov.id,1000,2500); changed=s.scenes.overlays(a.id)[0]; assert (changed.start_offset_ms,changed.end_offset_ms)==(1000,2500)
    assert s.service.active_overlays('p1',1500)[0].id==ov.id
    s.edits.delete_overlay('p1',a.id,ov.id); assert s.scenes.overlays(a.id)==[]; s.edits.undo(); assert s.scenes.overlays(a.id)[0].text=='ព័ត៌មានថ្មីថ្ងៃនេះ'


def test_subtitle_studio_timeline_two_way_sync(tmp_path: Path):
    s=make_system(tmp_path); add_standard_scenes(s); cue=s.subtitles.cues('sub1')[0]
    s.edits.set_subtitle_timing('p1',cue.id,800,2600); assert (s.subtitles.cue(cue.id).start_ms,s.subtitles.cue(cue.id).end_ms)==(800,2600)
    # Simulate Subtitle Studio canonical update; timeline derives it on next load.
    item=s.subtitles.cue(cue.id); item.start_ms=1100; item.end_ms=2800; s.subtitles.update_cue('p1',item)
    clip=next(x for x in s.mapping.build_clips('p1')['subtitle'] if x.source_id==cue.id); assert (clip.start_ms,clip.end_ms)==(1100,2800)
    s.edits.undo(); assert (s.subtitles.cue(cue.id).start_ms,s.subtitles.cue(cue.id).end_ms)==(500,2200)


def test_voice_sync_and_audio_volume_mute(tmp_path: Path):
    s=make_system(tmp_path); _,b,_=add_standard_scenes(s); s.edits.set_scene_audio('p1',b.id,narration_volume=.42,source_volume=.18,narration_enabled=False)
    scene=s.scenes.get(b.id); assert scene.audio.narration_volume==.42 and scene.audio.source_audio_volume==.18 and not scene.audio.narration_enabled
    clip=next(x for x in s.mapping.build_clips('p1')['voice'] if x.source_id==b.id); assert clip.metadata['volume']==.42 and not clip.enabled
    # Changing active narration assignment in Scene/Voice workflow updates derived timeline clip immediately.
    s.scene_service.assign_narration('p1',b.id,''); assert s.mapping.build_clips('p1')['voice']==[]


def test_transition_edit_and_undo(tmp_path: Path):
    s=make_system(tmp_path); a,_,_=add_standard_scenes(s); s.edits.set_transition('p1',a.id,'crossfade',400); assert s.scenes.get(a.id).transition_out.duration_ms==400
    s.edits.undo(); assert s.scenes.get(a.id).transition_out.type_code=='cut'


def test_snap_threshold_targets_and_playhead(tmp_path: Path):
    s=make_system(tmp_path); add_standard_scenes(s); s.service.add_marker('p1',3333,'Beat')
    snap=s.service.snapping.snap(3300,[0,3333,5000],100,8); assert snap.snapped and snap.time_ms==3333; assert s.service.snapping.threshold_ms(100,8)==80
    assert s.service.snap_time('p1',4990,100,include_playhead=7777)==5000
    assert s.service.snap_time('p1',7760,100,include_playhead=7777)==7777


def test_marker_crud_persistence_and_khmer(tmp_path: Path):
    s=make_system(tmp_path); add_standard_scenes(s); marker=s.service.add_marker('p1',1500,'ចំណុចសំខាន់'); assert marker.label=='ចំណុចសំខាន់'
    s.service.update_marker('p1',marker.id,1700,'ព័ត៌មាន'); repo=TimelineRepository(SQLiteDatabase(s.db.path)); assert repo.markers('p1')[0].label=='ព័ត៌មាន'
    s.service.delete_marker('p1',marker.id); assert repo.markers('p1')==[]


def test_zoom_fit_and_editor_state_restart(tmp_path: Path):
    s=make_system(tmp_path); add_standard_scenes(s); s.service.save_editor_state('p1',playhead_ms=1234,zoom_level=145.5,scroll_position=77,snap_enabled=False,selected_clip_id='scene:x')
    repo=TimelineRepository(SQLiteDatabase(s.db.path)); state=repo.get_state('p1'); assert state.playhead_ms==1234 and state.zoom_level==145.5 and state.scroll_position==77 and not state.snap_enabled


def test_project_duplication_and_project_delete_timeline_records(tmp_path: Path):
    s=make_system(tmp_path); add_standard_scenes(s); s.service.add_marker('p1',1000,'Hook'); s.timeline.ensure_tracks('p1'); s.edits.set_track_state('p1','subtitle',locked=True)
    root=tmp_path/'Projects'/'copy'; root.mkdir(parents=True); p2=Project(project_id='p2',title='Copy',workflow='video',language='en',project_path=str(root)); s.projects.create(p2)
    mapping=s.service.duplicate_project_timeline('p1','p2'); assert mapping and s.timeline.markers('p2')[0].id!=s.timeline.markers('p1')[0].id; assert s.timeline.track_by_type('p2','subtitle').locked
    s.projects.delete('p1'); assert s.timeline.markers('p1')==[] and s.timeline.list_tracks('p1')==[]


def test_validation_and_missing_source_clip(tmp_path: Path):
    s=make_system(tmp_path); a,_,_=add_standard_scenes(s); s.media.delete('img1'); data=s.service.load('p1'); clip=next(c for c in data['clips']['video'] if c.source_id==a.id); assert clip.metadata['missing']
    assert any(i.code=='missing_source' for i in data['issues'])


def test_large_project_100_scenes_1000_subtitles_200_overlays(tmp_path: Path):
    s=make_system(tmp_path)
    # Replace starter subtitle cues with a large deterministic set.
    cues=[SubtitleCue(track_id='sub1',order=i,start_ms=i*120,end_ms=i*120+100,text=f'Cue {i}') for i in range(1000)]; s.subtitles.replace_cues('p1','sub1',cues)
    for i in range(100):
        scene=s.scene_service.add_scene('p1',f'Scene {i+1}',1200); s.scene_service.assign_media('p1',scene.id,'img1')
        s.scene_service.add_text_overlay('p1',scene.id,f'Overlay {i*2}','label'); s.scene_service.add_text_overlay('p1',scene.id,f'Overlay {i*2+1}','label')
    start=time.perf_counter(); clips=s.mapping.build_clips('p1'); elapsed=time.perf_counter()-start
    assert len(clips['video'])==100 and len(clips['subtitle'])==1000 and len(clips['overlay'])==200
    assert elapsed<5.0


def test_khmer_timeline_clip_unicode_survives_restart(tmp_path: Path):
    s=make_system(tmp_path); scene=s.scene_service.add_scene('p1','ព័ត៌មានថ្មីសម្រាប់ថ្ងៃនេះ',3000); s.scene_service.assign_media('p1',scene.id,'img1'); s.scene_service.add_text_overlay('p1',scene.id,'ព័ត៌មានថ្មីថ្ងៃនេះ','headline')
    clips=s.mapping.build_clips('p1'); assert any('ព័ត៌មាន' in c.label for c in clips['video']); assert any('ព័ត៌មាន' in c.label for c in clips['overlay'])
    mapping=TimelineMappingService(SceneRepository(SQLiteDatabase(s.db.path)),MediaRepository(SQLiteDatabase(s.db.path)),GeneratedAudioRepository(SQLiteDatabase(s.db.path)),SubtitleRepository(SQLiteDatabase(s.db.path)),TimelineRepository(SQLiteDatabase(s.db.path)))
    assert any('ព័ត៌មាន' in c.label for c in mapping.build_clips('p1')['video'])


def test_render_plan_canonical_data_reflects_reorder_trim_overlay_subtitle_audio(tmp_path: Path):
    s=make_system(tmp_path); a,b,c=add_standard_scenes(s); s.edits.reorder_scene('p1',c.id,0); s.edits.trim_scene_right('p1',b.id,3500)
    ov=s.scenes.overlays(a.id)[0]; s.edits.set_overlay_timing('p1',a.id,ov.id,500,1500); cue=s.subtitles.cues('sub1')[0]; s.edits.set_subtitle_timing('p1',cue.id,900,1900); s.edits.set_scene_audio('p1',b.id,source_volume=.2)
    seq=s.scene_service.build_project_scene_sequence('p1'); assert seq['scenes'][0]['sceneId']==c.id
    spec=s.scene_service.build_scene_render_spec('p1',b.id); assert spec['durationMs']==3500 and spec['audio']['sourceAudioVolume']==.2
    spec_a=s.scene_service.build_scene_render_spec('p1',a.id); assert spec_a['overlays'][0]['startOffsetMs']==500 and spec_a['overlays'][0]['endOffsetMs']==1500
    assert (s.subtitles.cue(cue.id).start_ms,s.subtitles.cue(cue.id).end_ms)==(900,1900)


def test_frame_time_rounding_is_stable_at_30fps(tmp_path: Path):
    s=make_system(tmp_path); add_standard_scenes(s)
    # Milliseconds stay canonical; frame stepping quantizes from frame index rather than accumulating deltas.
    assert s.service.quantize_to_frame('p1',1000)==1000
    assert s.service.quantize_to_frame('p1',1033) in {1033,1034}
    assert s.service.quantize_to_frame('p1',10000)==10000
    assert s.service.frame_step_ms('p1')==33


def test_phase16_schema_migrates_to_phase17_without_fresh_database(tmp_path: Path, monkeypatch):
    import storage.database as database_module
    from storage.migrations import MIGRATIONS
    path=tmp_path/'upgrade.db'; original=MIGRATIONS
    monkeypatch.setattr(database_module,'MIGRATIONS',original[:13]); old=SQLiteDatabase(path); old.initialize(); assert old.current_version()==13
    monkeypatch.setattr(database_module,'MIGRATIONS',original); old.initialize(); assert old.current_version()==14
    with old.connect() as c:
        tables={r['name'] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {'timeline_state','timeline_tracks','timeline_markers'} <= tables


def test_combined_creative_edits_restart_persistence(tmp_path: Path):
    s=make_system(tmp_path); a,b,c=add_standard_scenes(s); cue=s.subtitles.cues('sub1')[0]
    s.edits.reorder_scene('p1',c.id,0); s.edits.trim_scene_right('p1',b.id,3200); part2=s.edits.split_scene('p1',a.id,1800)
    s.edits.set_subtitle_timing('p1',cue.id,900,2100); s.edits.set_scene_audio('p1',b.id,narration_volume=.55,source_volume=.2); marker=s.service.add_marker('p1',1250,'ព័ត៌មាន')
    db2=SQLiteDatabase(s.db.path); scenes=SceneRepository(db2); subtitles=SubtitleRepository(db2); timeline=TimelineRepository(db2)
    loaded=scenes.list_for_project('p1'); assert loaded[0].id==c.id and scenes.get(b.id).duration_ms==3200 and scenes.get(part2) is not None
    assert (subtitles.cue(cue.id).start_ms,subtitles.cue(cue.id).end_ms)==(900,2100)
    audio_scene=scenes.get(b.id); assert audio_scene.audio.narration_volume==.55 and audio_scene.audio.source_audio_volume==.2
    assert timeline.markers('p1')[0].id==marker.id and timeline.markers('p1')[0].label=='ព័ត៌មាន'
