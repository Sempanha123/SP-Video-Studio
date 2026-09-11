from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from domain.story_project import STORY_TYPES, STORY_TONES
from engines.voice_registry import VoiceRegistry
from services.project_service import ProjectService
from services.scene_generation_service import SceneGenerationService
from services.scene_preview_service import ScenePreviewService
from services.scene_service import SceneService
from services.scene_validation_service import SceneValidationService
from services.script_analysis_service import ScriptAnalysisService
from services.script_service import ScriptService
from services.story_apply_service import StoryApplyService
from services.story_errors import StoryInvalidSetup
from services.story_outline_service import StoryOutlineService
from services.story_planner import DeterministicStoryPlanner, STORY_STRUCTURE_TEMPLATES
from services.story_script_service import StoryScriptService
from services.story_service import StoryService
from services.story_validation_service import StoryValidationService
from services.timeline_mapping_service import TimelineMappingService
from storage.database import SQLiteDatabase
from storage.repositories.generated_audio_repository import GeneratedAudioRepository
from storage.repositories.media_repository import MediaRepository
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.scene_repository import SceneRepository
from storage.repositories.script_repository import ScriptRepository
from storage.repositories.story_repository import StoryRepository
from storage.repositories.subtitle_repository import SubtitleRepository
from storage.repositories.timeline_repository import TimelineRepository
from storage.repositories.transcript_repository import TranscriptRepository
from storage.repositories.voice_repository import VoiceRepository
from services.voice_service import VoiceService


class FakeDirector:
    def __init__(self): self.requests=[]
    def create_plan(self, request): self.requests.append(request); return request


def make_system(tmp_path: Path, *, language='en'):
    db=SQLiteDatabase(tmp_path/'app.db'); db.initialize()
    projects=ProjectRepository(db); media=MediaRepository(db); scripts=ScriptRepository(db); audio=GeneratedAudioRepository(db)
    subtitles=SubtitleRepository(db); transcripts=TranscriptRepository(db); scenes=SceneRepository(db); story_repo=StoryRepository(db); timeline_repo=TimelineRepository(db)
    project_service=ProjectService(projects,tmp_path/'projects')
    project=project_service.create_project('Story Test','story',language,'16:9',30)
    analysis=ScriptAnalysisService(); script_service=ScriptService(scripts,projects,analysis)
    voice=VoiceService(VoiceRegistry(),VoiceRepository(db),tmp_path/'runtime'/'voices')
    generation=SceneGenerationService(analysis,audio); scene_validation=SceneValidationService(media,audio,subtitles); preview=ScenePreviewService()
    scene_service=SceneService(scenes,projects,media,audio,subtitles,script_service,transcripts,generation,scene_validation,preview)
    planner=DeterministicStoryPlanner(); story=StoryService(story_repo,projects,voice); outline=StoryOutlineService(story_repo,story,planner)
    story_script=StoryScriptService(story_repo,script_service,voice); director=FakeDirector(); apply=StoryApplyService(story_repo,scene_service,script_service,director)
    validation=StoryValidationService(story_repo,scripts,scenes,subtitles,audio,analysis)
    project_service.set_script_service(script_service); project_service.set_scene_service(scene_service); project_service.set_voice_service(voice); project_service.set_story_service(story)
    return SimpleNamespace(db=db,projects=projects,project=project,project_service=project_service,media=media,scripts=scripts,audio=audio,subtitles=subtitles,scenes=scenes,story_repo=story_repo,story=story,outline=outline,planner=planner,script_service=script_service,story_script=story_script,scene_service=scene_service,apply=apply,director=director,validation=validation,timeline_repo=timeline_repo)


def setup_outline(s, *, idea='A learner solves a difficult problem with technology.', story_type='short_story', duration=60000, tone='warm', pace='balanced'):
    s.story.update_setup(s.project.id,title='A New Story',idea=idea,story_type=story_type,target_duration_ms=duration,tone=tone,pace=pace)
    return s.outline.create_from_plan(s.project.id)


def test_schema_v17_story_tables(tmp_path):
    s=make_system(tmp_path); assert s.db.current_version()==17
    with s.db.connect() as c: names={r['name'] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {'story_projects','story_outlines','story_beats','story_characters','story_mappings'} <= names


def test_story_setup_and_registries(tmp_path):
    s=make_system(tmp_path); meta=s.story.load_or_create(s.project.id)
    assert meta.story_type=='short_story' and meta.language=='en'
    assert {'short_story','documentary_story','educational_story','motivational_story','mystery'} <= STORY_TYPES
    assert {'warm','calm','dramatic','inspirational'} <= STORY_TONES
    assert {'5_beat_story','explainer','documentary','motivational','mystery_short','educational'} <= set(STORY_STRUCTURE_TEMPLATES)
    with pytest.raises(StoryInvalidSetup): s.story.update_setup(s.project.id,story_type='bad')

@pytest.mark.parametrize('duration,pace,min_count,max_count',[(30000,'balanced',3,5),(60000,'balanced',5,8),(180000,'balanced',8,14)])
def test_planner_beat_count_and_duration(duration,pace,min_count,max_count,tmp_path):
    s=make_system(tmp_path); s.story.update_setup(s.project.id,idea='Original idea',target_duration_ms=duration,pace=pace)
    meta=s.story.load_or_create(s.project.id); plan=s.planner.plan(meta)
    assert min_count<=len(plan.beats)<=max_count
    assert sum(b.target_duration_ms for b in plan.beats)==duration


def test_60_second_short_story_structure(tmp_path):
    s=make_system(tmp_path); _,beats=setup_outline(s)
    kinds=[b.beat_type for b in beats]
    assert kinds[0]=='hook' and 'setup' in kinds and 'development' in kinds and 'climax' in kinds and kinds[-1]=='resolution'
    assert sum(b.target_duration_ms for b in beats)==60000


def test_educational_and_motivational_profiles(tmp_path):
    s=make_system(tmp_path); s.story.update_setup(s.project.id,idea='Teach a useful skill',story_type='educational_story',target_duration_ms=180000)
    assert {'hook','context','explanation','example','lesson','outro'} <= {b.beat_type for b in s.planner.plan(s.story.load_or_create(s.project.id)).beats}
    s.story.update_setup(s.project.id,story_type='motivational_story')
    assert {'problem','struggle','turning_point','lesson'} <= {b.beat_type for b in s.planner.plan(s.story.load_or_create(s.project.id)).beats}


def test_beat_crud_reorder_duplicate_and_undo_redo(tmp_path):
    s=make_system(tmp_path); o,beats=setup_outline(s); original=[b.id for b in beats]
    added=s.outline.add_beat(s.project.id,o.id,'Extra','custom',4000); assert added.id in [b.id for b in s.story_repo.beats(o.id)]
    assert s.outline.undo(); assert added.id not in [b.id for b in s.story_repo.beats(o.id)]
    assert s.outline.redo(); assert added.id in [b.id for b in s.story_repo.beats(o.id)]
    s.outline.move_beat(s.project.id,added.id,0); assert s.story_repo.beats(o.id)[0].id==added.id
    assert s.outline.undo(); assert [b.id for b in s.story_repo.beats(o.id)][:len(original)]==original
    clone=s.outline.duplicate_beat(s.project.id,beats[0].id); assert clone.id!=beats[0].id and clone.title.endswith('Copy')
    assert s.outline.undo(); assert s.story_repo.beat(s.project.id,clone.id) is None
    assert s.outline.redo(); assert s.story_repo.beat(s.project.id,clone.id) is not None
    s.outline.delete_beat(s.project.id,clone.id); assert s.story_repo.beat(s.project.id,clone.id) is None
    assert s.outline.undo(); assert s.story_repo.beat(s.project.id,clone.id) is not None


def test_outline_lock_refresh_preserves_locked_and_user_modified(tmp_path):
    s=make_system(tmp_path); o,beats=setup_outline(s); locked=s.outline.update_beat(s.project.id,beats[0].id,title='My Locked Hook'); s.outline.set_locked(s.project.id,locked.id,True)
    refreshed=s.outline.refresh_structure(s.project.id,o.id)
    got=next(b for b in refreshed if b.id==locked.id); assert got.title=='My Locked Hook' and got.locked


def test_duration_normalization_preserves_locked(tmp_path):
    s=make_system(tmp_path); o,beats=setup_outline(s)
    s.outline.update_beat(s.project.id,beats[0].id,target_duration_ms=10000); s.outline.set_locked(s.project.id,beats[0].id,True)
    for b in s.story_repo.beats(o.id)[1:]: s.outline.update_beat(s.project.id,b.id,target_duration_ms=13000)
    fitted=s.outline.fit_to_target(s.project.id,o.id)
    assert next(b for b in fitted if b.id==beats[0].id).target_duration_ms==10000
    assert sum(b.target_duration_ms for b in fitted)==60000


def test_outline_approval_and_setup_change_marks_outdated(tmp_path):
    s=make_system(tmp_path); o,_=setup_outline(s); assert s.outline.approve(s.project.id,o.id).status=='approved'
    s.story.update_setup(s.project.id,tone='calm'); assert s.story_repo.latest_outline(s.project.id).status=='outdated'


def test_character_and_narrator_voice(tmp_path):
    s=make_system(tmp_path); c=s.story.add_character(s.project.id,'Narrator','narrator','Main narrator',voice_id='preset-james')
    assert s.story_repo.character(s.project.id,c.id).voice_id=='preset-james'
    assert s.story.set_narrator_voice(s.project.id,'preset-james').narrator_voice_id=='preset-james'
    s.story.delete_character(s.project.id,c.id); assert s.story_repo.character(s.project.id,c.id) is None


def test_script_creation_and_source_changed_sync(tmp_path):
    s=make_system(tmp_path); o,beats=setup_outline(s); script,sections=s.story_script.create_from_outline(s.project.id,o.id)
    assert len(sections)==len(beats); assert all(sec.metadata.get('storyBeatId') for sec in sections)
    target=beats[2]; old_section=next(sec for sec in sections if sec.metadata['storyBeatId']==target.id); old_text=old_section.content
    s.outline.update_beat(s.project.id,target.id,description='A changed beat meaning.')
    _,synced=s.story_script.sync(s.project.id,o.id); current=next(sec for sec in synced if sec.id==old_section.id)
    assert current.content==old_text and current.metadata['storySourceStatus']=='source_changed'
    assert s.story_repo.beat(s.project.id,target.id).id==target.id


def test_script_new_beat_sync_and_translation_context(tmp_path):
    s=make_system(tmp_path); o,_=setup_outline(s); script,sections=s.story_script.create_from_outline(s.project.id,o.id)
    new=s.outline.add_beat(s.project.id,o.id,'New Context','context',5000); _,after=s.story_script.sync(s.project.id,o.id)
    mapping=s.story_repo.mappings(s.project.id,mapping_type='script_section',beat_id=new.id); assert mapping and any(x.title=='New Context' for x in after)
    ctx=s.apply.translation_context(s.project.id); assert ctx['scriptId']==script.id and set(ctx['sectionToBeat'].values()) >= {new.id}


def test_create_scenes_from_outline_and_timeline_derivation(tmp_path):
    s=make_system(tmp_path); o,beats=setup_outline(s); s.story_script.create_from_outline(s.project.id,o.id); created=s.apply.create_scenes_from_outline(s.project.id,o.id)
    assert len(created)==len(beats); assert [x.order for x in s.scenes.list_for_project(s.project.id)]==list(range(len(beats)))
    assert all(x.metadata.get('storyBeatId') for x in created)
    mapping=TimelineMappingService(s.scenes,s.media,s.audio,s.subtitles,s.timeline_repo); clips=mapping.build_clips(s.project.id)
    assert len(clips['video'])==len(beats) and mapping.duration_ms(s.project.id)==sum(x.duration_ms for x in created)


def test_director_integration_uses_story_request_without_mutation(tmp_path):
    s=make_system(tmp_path); o,_=setup_outline(s); s.story_script.create_from_outline(s.project.id,o.id); req=s.apply.director_plan(s.project.id,platform='youtube')
    assert req.workflow=='story' and req.content_source_type=='script' and req.target_duration_ms==60000
    assert s.story_repo.beats(o.id)


def test_subtitle_and_story_readiness_reuse_shared_system(tmp_path):
    s=make_system(tmp_path); o,_=setup_outline(s); s.outline.approve(s.project.id,o.id); s.story_script.create_from_outline(s.project.id,o.id); s.story.set_narrator_voice(s.project.id,'preset-james'); s.apply.create_scenes_from_outline(s.project.id,o.id)
    report=s.validation.validate(s.project.id); assert report['sceneCount']>0 and report['voiceSelected'] is True
    assert report['subtitleCount']==0  # Story subtitles are optional and remain in shared Subtitle Studio.


def test_project_duplication_remaps_story_sections_and_scenes(tmp_path):
    s=make_system(tmp_path); o,beats=setup_outline(s); _,sections=s.story_script.create_from_outline(s.project.id,o.id); scenes=s.apply.create_scenes_from_outline(s.project.id,o.id)
    dup=s.project_service.duplicate_project(s.project.id); dm=s.story_repo.get_project(dup.id); do=s.story_repo.latest_outline(dup.id); db=s.story_repo.beats(do.id); maps=s.story_repo.mappings(dup.id)
    assert dm and do and len(db)==len(beats); assert {b.id for b in db}.isdisjoint({b.id for b in beats})
    assert all(m['projectId']==dup.id for m in maps)
    assert not ({m['targetId'] for m in maps if m['mappingType']=='script_section'} & {x.id for x in sections})
    assert not ({m['targetId'] for m in maps if m['mappingType']=='scene'} & {x.id for x in scenes})


def test_project_delete_cascades_story_only(tmp_path):
    s=make_system(tmp_path); setup_outline(s); pid=s.project.id; s.project_service.delete_project(pid)
    assert s.story_repo.get_project(pid) is None and s.story_repo.outlines(pid)==[]


def test_khmer_story_unicode_restart(tmp_path):
    s=make_system(tmp_path,language='km'); idea='យុវជនម្នាក់ចាប់ផ្តើមរៀនបច្ចេកវិទ្យាថ្មី ហើយប្រើចំណេះដឹងរបស់គាត់ដើម្បីដោះស្រាយបញ្ហាមួយ។'
    o,beats=setup_outline(s,idea=idea); s.outline.update_beat(s.project.id,beats[0].id,title='រឿងបច្ចេកវិទ្យាថ្មី',description=idea); _,sections=s.story_script.create_from_outline(s.project.id,o.id)
    restarted=StoryRepository(SQLiteDatabase(tmp_path/'app.db')); ro=restarted.latest_outline(s.project.id); rb=restarted.beats(ro.id)
    assert rb[0].title=='រឿងបច្ចេកវិទ្យាថ្មី' and idea in rb[0].description
    assert any('រឿង' in x.title for x in sections)


def test_replace_structure_preserves_mapping_for_retained_locked_beat(tmp_path):
    s=make_system(tmp_path); o,beats=setup_outline(s); s.story_script.create_from_outline(s.project.id,o.id); first=beats[0]; mapping=s.story_repo.mappings(s.project.id,mapping_type='script_section',beat_id=first.id)[0]
    s.outline.update_beat(s.project.id,first.id,title='Locked custom'); s.outline.set_locked(s.project.id,first.id,True); s.outline.refresh_structure(s.project.id,o.id)
    after=s.story_repo.mappings(s.project.id,mapping_type='script_section',beat_id=first.id)
    assert after and after[0]['id']==mapping['id']


def test_large_story_50_beats_and_mappings(tmp_path):
    s=make_system(tmp_path); o,_=setup_outline(s,duration=600000)
    # Build a deterministic 50-beat manual outline without requiring a cloud writer.
    existing=s.story_repo.beats(o.id)
    for i in range(len(existing),50): s.outline.add_beat(s.project.id,o.id,f'Beat {i+1}','development',12000)
    _,sections=s.story_script.create_from_outline(s.project.id,o.id)
    assert len(s.story_repo.beats(o.id))==50 and len(sections)==50

def test_story_picks_up_existing_project_voice_assignment(tmp_path):
    s=make_system(tmp_path); s.story.voice_service.assign_project(s.project.id,'preset-james')
    meta=s.story.load_or_create(s.project.id)
    assert meta.narrator_voice_id=='preset-james'
