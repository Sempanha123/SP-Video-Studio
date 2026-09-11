from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace

import pytest

from domain.news_claim import NewsClaim
from domain.scene_overlay import SceneOverlay
from domain.render_settings import RenderSettings
from rendering.scene_renderer import SceneRenderer
from services.news_branding_service import NewsBrandingService
from services.news_brief_service import NewsBriefService
from services.news_claim_service import NewsClaimService
from services.news_extraction_service import NewsExtractionService
from services.news_graphic_service import NewsGraphicService
from services.news_layout_service import NewsLayoutService
from services.news_script_service import NewsScriptService
from services.news_service import NewsService
from services.news_source_service import NewsSourceService
from services.news_validation_service import NewsValidationService
from services.news_visual_service import NewsVisualService
from services.news_visual_validation_service import NewsVisualValidationService,contrast_ratio
from services.project_service import ProjectService
from services.scene_generation_service import SceneGenerationService
from services.scene_preview_service import ScenePreviewService
from services.scene_service import SceneService
from services.scene_validation_service import SceneValidationService
from services.script_analysis_service import ScriptAnalysisService
from services.script_service import ScriptService
from storage.database import SQLiteDatabase
from storage.repositories.generated_audio_repository import GeneratedAudioRepository
from storage.repositories.media_repository import MediaRepository
from storage.repositories.news_repository import NewsRepository
from storage.repositories.news_visual_repository import NewsVisualRepository
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.scene_repository import SceneRepository
from storage.repositories.script_repository import ScriptRepository
from storage.repositories.subtitle_repository import SubtitleRepository
from storage.repositories.transcript_repository import TranscriptRepository


def make_system(tmp_path:Path, *, aspect='9:16', language='en'):
    db=SQLiteDatabase(tmp_path/'app.db');db.initialize()
    projects=ProjectRepository(db);media=MediaRepository(db);scripts=ScriptRepository(db);audio=GeneratedAudioRepository(db);subtitles=SubtitleRepository(db);transcripts=TranscriptRepository(db);scenes=SceneRepository(db);news_repo=NewsRepository(db);visual_repo=NewsVisualRepository(db)
    ps=ProjectService(projects,tmp_path/'projects');project=ps.create_project('Visual News','news',language,aspect,30)
    analysis=ScriptAnalysisService();script_service=ScriptService(scripts,projects,analysis);ps.set_script_service(script_service)
    scene_service=SceneService(scenes,projects,media,audio,subtitles,script_service,transcripts,SceneGenerationService(analysis,audio),SceneValidationService(media,audio,subtitles),ScenePreviewService());ps.set_scene_service(scene_service)
    sources=NewsSourceService(news_repo,projects);claims=NewsClaimService(news_repo,NewsExtractionService());validation=NewsValidationService(news_repo);briefs=NewsBriefService(news_repo);news_scripts=NewsScriptService(news_repo,script_service,briefs,validation,scene_service=scene_service);news=NewsService(news_repo,projects,sources,claims,briefs,news_scripts,validation);ps.set_news_service(news);news.load_or_create(project.id)
    branding=NewsBrandingService();layouts=NewsLayoutService();graphics=NewsGraphicService();visual_validation=NewsVisualValidationService();visuals=NewsVisualService(visual_repo,news_repo,scene_service,layouts,graphics,branding,visual_validation);ps.set_news_visual_service(visuals);news.visual_service=visuals
    scene=scene_service.add_scene(project.id,'Lead',5000);scene_service.set_background_enabled(project.id,scene.id,True)
    return SimpleNamespace(db=db,projects=projects,project=project,ps=ps,scenes=scenes,scene_service=scene_service,scene=scene,news_repo=news_repo,visual_repo=visual_repo,sources=sources,claims=claims,news=news,visuals=visuals,branding=branding,layouts=layouts,graphics=graphics)


def supported_claim(s,text='Company announced Product X on September 10.',*,claim_type='fact',quote=None):
    src=s.sources.add_manual(s.project.id,'Official',text,publisher='Example Organization')
    snap=s.news_repo.latest_snapshot(s.project.id,src.id)
    claim=s.claims.create_manual(s.project.id,text,claim_type=claim_type,source_id=src.id,snapshot_id=snap.id,evidence_text=text,quote=quote)
    s.claims.approve(s.project.id,claim.id)
    return src,claim


def test_schema_v16_news_visual_tables(tmp_path):
    s=make_system(tmp_path);assert s.db.current_version()==16
    with s.db.connect() as c:names={r['name'] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {'news_visual_themes','news_scene_layouts','news_visual_elements'}<=names


def test_builtin_theme_registry_unique_and_professional():
    rows=NewsBrandingService().builtin_themes();assert len(rows)==6 and len({x['id'] for x in rows})==6
    assert {'clean_news','modern_news','breaking_news','documentary_news','minimal_news','tech_news'}=={x['id'] for x in rows}
    assert all('cnn' not in x['name'].lower() and 'bbc' not in x['name'].lower() for x in rows)


def test_theme_application_customization_and_restart(tmp_path):
    s=make_system(tmp_path);theme=s.visuals.apply_theme(s.project.id,'tech_news');assert theme.preset_id=='tech_news'
    custom=s.visuals.customize_theme(s.project.id,{'accentColor':'#AA8844','fontHeading':'Noto Sans Khmer'});assert custom.preset_id=='custom' and custom.accent_color=='#AA8844'
    repo=NewsVisualRepository(SQLiteDatabase(tmp_path/'app.db'));got=repo.active_theme(s.project.id);assert got and got.accent_color=='#AA8844' and got.font_heading=='Noto Sans Khmer'

@pytest.mark.parametrize('ratio',['16:9','9:16','1:1'])
def test_headline_layout_resolves_normalized_for_all_ratios(ratio):
    data=NewsLayoutService().resolve_layout('headline_focus',ratio,{})
    for key in ('card','text','source'):
        x,y,w,h=data[key];assert 0<=x<=1 and 0<=y<=1 and 0<w<=1 and 0<h<=1 and x+w<=1.001 and y+h<=1.001


def test_vertical_layout_rearranges_instead_of_uniform_scaling():
    svc=NewsLayoutService();wide=svc.resolve_layout('split_visual','16:9',{})['card'];vert=svc.resolve_layout('split_visual','9:16',{})['card'];assert wide!=vert and wide[0]>.4 and vert[1]>.5


def test_headline_breaking_lower_topic_intro_outro_cards(tmp_path):
    s=make_system(tmp_path);src,_=supported_claim(s)
    h=s.visuals.create_headline(s.project.id,s.scene.id,'Major Technology Update',source_id=src.id);b=s.visuals.create_headline(s.project.id,s.scene.id,'Breaking Update',breaking=True)
    low=s.visuals.create_lower_third(s.project.id,s.scene.id,'Phnom Penh','Cambodia');topic=s.visuals.create_topic(s.project.id,s.scene.id,'Technology');intro=s.visuals.create_intro(s.project.id,s.scene.id,'Daily Update','Technology');out=s.visuals.create_outro(s.project.id,s.scene.id)
    assert {x.graphic_type for x in (h,b,low,topic,intro,out)}=={'headline','breaking','lower_third','topic','intro','outro'}
    assert any(o.type_code=='shape' for o in s.scenes.overlays(s.scene.id))


def test_fact_card_source_changed_then_user_updates(tmp_path):
    s=make_system(tmp_path);src,claim=supported_claim(s);e=s.visuals.create_fact_from_claim(s.project.id,s.scene.id,claim.id)
    ov=s.scenes.overlays(s.scene.id);text=next(o.text for o in ov if o.id==e.scene_overlay_id);assert text==claim.text and e.source_id==src.id
    edited=s.claims.edit(s.project.id,claim.id,'Company announced Product Y on September 11.');assert edited.status_code=='needs_review'
    state=s.visuals.scene_visuals(s.project.id,s.scene.id);row=next(x for x in state['elements'] if x['id']==e.id);assert row['status']=='source_changed'
    before=next(o for o in s.scenes.overlays(s.scene.id) if o.id==e.scene_overlay_id).text;assert 'Product X' in before
    s.visuals.update_from_claim(s.project.id,e.id);after=next(o for o in s.scenes.overlays(s.scene.id) if o.id==e.scene_overlay_id).text;assert 'Product Y' in after


def test_rejected_claim_visual_warns_and_readiness_reflects(tmp_path):
    s=make_system(tmp_path);_,claim=supported_claim(s);e=s.visuals.create_fact_from_claim(s.project.id,s.scene.id,claim.id);s.claims.reject(s.project.id,claim.id)
    rows=s.visuals.scene_visuals(s.project.id,s.scene.id)['elements'];row=next(x for x in rows if x['id']==e.id);assert row['status']=='unsupported_source';assert any(i['code']=='rejected_claim' for i in row['issues'])
    ready=s.visuals.readiness(s.project.id);assert ready['unsupported']>=1 and ready['errors']>=1

@pytest.mark.parametrize('kind,expected_quotes,label',[('exact',True,''),('translated_quote',True,'Translated'),('paraphrase',False,'Paraphrase')])
def test_quote_types_preserve_treatment(tmp_path,kind,expected_quotes,label):
    s=make_system(tmp_path);src,claim=supported_claim(s,'Alex said the launch is tomorrow.',claim_type='quote',quote={'text':'We launch tomorrow.','speaker':'Alex','kind':kind,'original':'We launch tomorrow.'})
    e=s.visuals.create_quote_from_claim(s.project.id,s.scene.id,claim.id);o=next(x for x in s.scenes.overlays(s.scene.id) if x.id==e.scene_overlay_id)
    assert (o.text.startswith('“') and o.text.endswith('”')) is expected_quotes
    assert (label in o.secondary_text) if label else True
    assert e.quote_type==kind and e.source_id==src.id


def test_number_card_keeps_exact_raw_value_and_provenance(tmp_path):
    s=make_system(tmp_path);src,claim=supported_claim(s,'Usage increased by 42 percent.',claim_type='number');e=s.visuals.create_number(s.project.id,s.scene.id,'42','%','Increase in usage',claim_id=claim.id)
    saved=s.visual_repo.element(s.project.id,e.id);assert saved.metadata['rawValue']=='42' and saved.metadata['unit']=='%' and saved.claim_id==claim.id and saved.source_id==src.id


def test_source_attribution_is_compact_and_does_not_render_url(tmp_path):
    s=make_system(tmp_path);src,_=supported_claim(s);e=s.visuals.create_source_attribution(s.project.id,s.scene.id,src.id);o=next(x for x in s.scenes.overlays(s.scene.id) if x.id==e.scene_overlay_id)
    assert o.text=='Source: Example Organization' and 'http' not in o.text


def test_layout_reapply_preserves_unrelated_overlay(tmp_path):
    s=make_system(tmp_path);manual=s.scene_service.add_text_overlay(s.project.id,s.scene.id,'User overlay','headline');_,claim=supported_claim(s);s.visuals.create_fact_from_claim(s.project.id,s.scene.id,claim.id)
    s.visuals.apply_layout(s.project.id,s.scene.id,'headline_focus',mode='replace');ids={o.id for o in s.scenes.overlays(s.scene.id)};assert manual.id in ids
    assert all(not e for e in s.visual_repo.elements(s.project.id,s.scene.id))


def test_detach_layout_stops_theme_following(tmp_path):
    s=make_system(tmp_path);_,claim=supported_claim(s);s.visuals.create_fact_from_claim(s.project.id,s.scene.id,claim.id);layout=s.visuals.detach_layout(s.project.id,s.scene.id);assert layout.customized and layout.status=='detached'
    assert all(not e.follow_theme for e in s.visual_repo.elements(s.project.id,s.scene.id))


def test_storyboard_edit_marks_layout_customized_without_data_loss(tmp_path):
    s=make_system(tmp_path);_,claim=supported_claim(s);e=s.visuals.create_fact_from_claim(s.project.id,s.scene.id,claim.id);o=next(x for x in s.scenes.overlays(s.scene.id) if x.id==e.scene_overlay_id)
    s.scene_service.update_overlay(s.project.id,s.scene.id,o.id,{'x':min(.8,o.x+.05)})
    state=s.visuals.scene_visuals(s.project.id,s.scene.id);assert state['layout']['customized'] is True and any(x['id']==e.id for x in state['elements'])


def test_khmer_and_mixed_language_persist(tmp_path):
    s=make_system(tmp_path,language='km');src,claim=supported_claim(s,'ក្រុមហ៊ុនបានប្រកាសផលិតផលថ្មីនៅថ្ងៃនេះ។');e=s.visuals.create_fact_from_claim(s.project.id,s.scene.id,claim.id);s.visuals.create_headline(s.project.id,s.scene.id,'OpenAI\nបច្ចេកវិទ្យាថ្មី')
    repo=NewsVisualRepository(SQLiteDatabase(tmp_path/'app.db'));assert repo.element(s.project.id,e.id).claim_id==claim.id
    texts=[o.text for o in s.scenes.overlays(s.scene.id)];assert any('ក្រុមហ៊ុន' in x for x in texts) and any('OpenAI' in x and 'បច្ចេកវិទ្យា' in x for x in texts)


def test_contrast_and_overflow_validation(tmp_path):
    s=make_system(tmp_path);theme=s.visuals.active_theme(s.project.id);assert contrast_ratio(theme.text_primary,theme.background_color)>4.5
    theme.text_primary='#111111';theme.background_color='#111111';assert any(i.code=='poor_contrast' for i in s.visuals.validation.validate_theme(theme))
    o=SceneOverlay(s.scene.id,0,'headline',text='word '*300,x=.1,y=.1,width=.2,height=.08);issues=s.visuals.validation.validate_overlay(o,scene_duration_ms=5000);assert any(i.code=='text_overflow' for i in issues)


def test_shape_overlay_is_generic_and_renderer_builds_drawbox(tmp_path):
    class Runner:
        def run(self,*a,**k):return None
    renderer=SceneRenderer(Runner());settings=RenderSettings(width=320,height=180,fps=30)
    spec={'sceneId':'s','durationMs':1000,'visual':{'backgroundColor':'#000000','fitMode':'fill'},'audio':{},'overlays':[SceneOverlay('s',0,'shape',x=.1,y=.2,width=.5,height=.3,style={'fillColor':'#123456'}).to_dict()]}
    cmd=renderer.build_command(spec,settings,tmp_path/'out.nut',temp_dir=tmp_path/'tmp');joined=' '.join(cmd);assert 'drawbox=' in joined and '#123456' in joined


def test_scene_render_spec_contains_news_shape_and_text(tmp_path):
    s=make_system(tmp_path);_,claim=supported_claim(s);s.visuals.create_fact_from_claim(s.project.id,s.scene.id,claim.id);spec=s.scene_service.build_scene_render_spec(s.project.id,s.scene.id);types={x['type'] for x in spec['overlays']};assert {'shape','label'}<=types or {'shape','headline'}<=types


def test_project_duplication_remaps_claim_source_and_scene_links(tmp_path):
    s=make_system(tmp_path);src,claim=supported_claim(s);e=s.visuals.create_fact_from_claim(s.project.id,s.scene.id,claim.id)
    dup=s.ps.duplicate_project(s.project.id);layouts=s.visual_repo.layouts(dup.id);elements=s.visual_repo.elements(dup.id);assert layouts and elements
    assert all(x.project_id==dup.id for x in elements);assert all(x.scene_id!=s.scene.id for x in elements)
    assert all((not x.claim_id or x.claim_id!=claim.id) and (not x.source_id or x.source_id!=src.id) for x in elements)
    assert all(s.news_repo.claim(dup.id,x.claim_id) is not None for x in elements if x.claim_id)


def test_project_delete_cascades_visual_records(tmp_path):
    s=make_system(tmp_path);_,claim=supported_claim(s);s.visuals.create_fact_from_claim(s.project.id,s.scene.id,claim.id);s.ps.delete_project(s.project.id)
    assert s.visual_repo.themes(s.project.id)==[] and s.visual_repo.layouts(s.project.id)==[] and s.visual_repo.elements(s.project.id)==[]


def test_news_overview_includes_visual_readiness(tmp_path):
    s=make_system(tmp_path);_,claim=supported_claim(s);s.visuals.create_fact_from_claim(s.project.id,s.scene.id,claim.id);overview=s.news.overview(s.project.id);assert overview['newsVisualTotal']>=1 and overview['newsVisualReady']>=1


def test_news_graphics_appear_on_generic_timeline_overlay_track(tmp_path):
    from commands.command_stack import CommandStack
    from services.timeline_edit_service import TimelineEditService
    from services.timeline_mapping_service import TimelineMappingService
    from storage.repositories.timeline_repository import TimelineRepository
    s=make_system(tmp_path);_,claim=supported_claim(s);e=s.visuals.create_fact_from_claim(s.project.id,s.scene.id,claim.id)
    timeline=TimelineRepository(s.db);timeline.ensure_tracks(s.project.id)
    mapping=TimelineMappingService(s.scenes,s.scene_service.media_repository,s.scene_service.audio_repository,s.scene_service.subtitle_repository,timeline)
    clips=mapping.build_clips(s.project.id)['overlay'];ids={c.source_id for c in clips};assert e.scene_overlay_id in ids
    active=mapping.get_active_overlays(s.project.id,1000);assert any(o.id==e.scene_overlay_id for o in active)
    # Timeline edits the same canonical SceneOverlay record; Visual Studio sees it immediately.
    edits=TimelineEditService(s.scene_service,s.scenes,object(),s.scene_service.subtitle_repository,timeline,CommandStack(20))
    edits.set_overlay_timing(s.project.id,s.scene.id,e.scene_overlay_id,600,1800)
    visual=s.visuals.scene_visuals(s.project.id,s.scene.id)
    row=next(x for x in visual['elements'] if x['id']==e.id)
    assert row['overlay']['startOffsetMs']==600 and row['overlay']['endOffsetMs']==1800


def test_news_visual_create_fact_undo_redo_restores_generic_overlays_and_metadata(tmp_path):
    s=make_system(tmp_path);_,claim=supported_claim(s)
    before_overlay_ids={o.id for o in s.scenes.overlays(s.scene.id)}
    s.visuals.execute_undoable(
        'Create Fact Card',s.project.id,s.scene.id,
        lambda:s.visuals.create_fact_from_claim(s.project.id,s.scene.id,claim.id),
    )
    created_elements=s.visual_repo.elements(s.project.id,s.scene.id)
    assert created_elements and s.visuals.can_undo()
    created_overlay_ids={o.id for o in s.scenes.overlays(s.scene.id)}
    assert created_overlay_ids!=before_overlay_ids
    assert s.visuals.undo() is True
    assert {o.id for o in s.scenes.overlays(s.scene.id)}==before_overlay_ids
    assert s.visual_repo.elements(s.project.id,s.scene.id)==[]
    assert s.visuals.redo() is True
    assert {o.id for o in s.scenes.overlays(s.scene.id)}==created_overlay_ids
    restored=s.visual_repo.elements(s.project.id,s.scene.id)
    assert len(restored)==len(created_elements) and any(x.claim_id==claim.id for x in restored)


def test_news_visual_theme_change_undo_redo_restores_project_theme_and_follower_style(tmp_path):
    s=make_system(tmp_path);_,claim=supported_claim(s)
    e=s.visuals.create_fact_from_claim(s.project.id,s.scene.id,claim.id)
    overlay_before=next(o for o in s.scenes.overlays(s.scene.id) if o.id==e.scene_overlay_id)
    before_font=overlay_before.style.get('fontFamily')
    before_preset=s.visuals.active_theme(s.project.id).preset_id
    s.visuals.execute_undoable(
        'Apply Tech Theme',s.project.id,s.scene.id,
        lambda:s.visuals.apply_theme(s.project.id,'tech_news'),project_scope=True,
    )
    assert s.visuals.active_theme(s.project.id).preset_id=='tech_news'
    assert s.visuals.undo() is True
    assert s.visuals.active_theme(s.project.id).preset_id==before_preset
    overlay_undo=next(o for o in s.scenes.overlays(s.scene.id) if o.id==e.scene_overlay_id)
    assert overlay_undo.style.get('fontFamily')==before_font
    assert s.visuals.redo() is True
    assert s.visuals.active_theme(s.project.id).preset_id=='tech_news'


def test_phase18_schema_v15_upgrades_to_news_visual_schema_v16(tmp_path, monkeypatch):
    import storage.database as database_module
    from storage.migrations import MIGRATIONS
    path=tmp_path/'phase18.db'; original=MIGRATIONS
    monkeypatch.setattr(database_module,'MIGRATIONS',[m for m in original if m.version<=15])
    old=SQLiteDatabase(path); old.initialize(); assert old.current_version()==15
    monkeypatch.setattr(database_module,'MIGRATIONS',original)
    old.initialize(); assert old.current_version()==16
    with old.connect() as c:
        tables={r['name'] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {'news_visual_themes','news_scene_layouts','news_visual_elements'}<=tables


def test_news_visual_restart_persists_theme_three_scenes_links_and_customization(tmp_path):
    s=make_system(tmp_path);src,claim=supported_claim(s)
    s.visuals.customize_theme(s.project.id,{'accentColor':'#A07A45','fontHeading':'Noto Sans Khmer'})
    second=s.scene_service.add_scene(s.project.id,'Fact',5000);s.scene_service.set_background_enabled(s.project.id,second.id,True)
    third=s.scene_service.add_scene(s.project.id,'Lower',5000);s.scene_service.set_background_enabled(s.project.id,third.id,True)
    s.visuals.create_headline(s.project.id,s.scene.id,'ព័ត៌មានបច្ចេកវិទ្យាថ្មី',source_id=src.id)
    fact=s.visuals.create_fact_from_claim(s.project.id,second.id,claim.id)
    s.visuals.create_lower_third(s.project.id,third.id,'Phnom Penh','Cambodia',source_id=src.id)
    s.visuals.mark_customized(s.project.id,second.id)
    db2=SQLiteDatabase(s.db.path);repo2=NewsVisualRepository(db2);scenes2=SceneRepository(db2)
    theme=repo2.active_theme(s.project.id);assert theme and theme.preset_id=='custom' and theme.accent_color=='#A07A45'
    assert len(repo2.layouts(s.project.id))==3
    elements=repo2.elements(s.project.id);assert len(elements)>=6 and any(e.id==fact.id and e.claim_id==claim.id for e in elements)
    layout2=repo2.layout(s.project.id,second.id);assert layout2 and layout2.customized
    assert len(scenes2.list_for_project(s.project.id))==3


def test_news_visual_large_project_derivation_100_scenes(tmp_path):
    from services.timeline_mapping_service import TimelineMappingService
    from storage.repositories.timeline_repository import TimelineRepository
    s=make_system(tmp_path)
    # First scene plus 99 more; use lightweight generic News headline cards so the test
    # exercises the same overlay data consumed by Storyboard, Timeline, and renderer.
    s.visuals.create_headline(s.project.id,s.scene.id,'Scene 1')
    for index in range(2,101):
        scene=s.scene_service.add_scene(s.project.id,f'News {index}',1200)
        s.scene_service.set_background_enabled(s.project.id,scene.id,True)
        s.visuals.create_headline(s.project.id,scene.id,f'Headline {index}')
    assert len(s.scene_service.list_scenes(s.project.id))==100
    assert len(s.visual_repo.elements(s.project.id))>=200
    timeline=TimelineRepository(s.db)
    mapping=TimelineMappingService(s.scenes,s.scene_service.media_repository,s.scene_service.audio_repository,s.scene_service.subtitle_repository,timeline)
    clips=mapping.build_clips(s.project.id)
    assert len(clips['video'])==100 and len(clips['overlay'])>=200
