from __future__ import annotations
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from uuid import uuid4
from commands.command_stack import CommandStack
from commands.timeline.commands import TimelineCommand

from domain.news_scene_layout import NewsSceneLayoutInstance,LAYOUT_BY_ID
from domain.news_visual_element import NewsVisualElement
from domain.scene_overlay import SceneOverlay
from services.news_branding_service import NewsBrandingService
from services.news_graphic_service import NewsGraphicService,content_hash
from services.news_layout_service import NewsLayoutService
from services.news_visual_errors import NewsVisualClaimInvalid,NewsVisualInvalidLayout,NewsVisualSourceMissing
from services.news_visual_validation_service import NewsVisualValidationService
from storage.repositories.news_visual_repository import NewsVisualRepository

class NewsVisualService:
    def __init__(self,repository:NewsVisualRepository,news_repository,scene_service,layout_service:NewsLayoutService,graphic_service:NewsGraphicService,branding_service:NewsBrandingService,validation:NewsVisualValidationService,command_stack:CommandStack|None=None)->None:
        self.repository=repository;self.news_repository=news_repository;self.scenes=scene_service;self.layouts=layout_service;self.graphics=graphic_service;self.branding=branding_service;self.validation=validation;self.command_stack=command_stack or CommandStack(150)
    def can_undo(self)->bool:return self.command_stack.can_undo
    def can_redo(self)->bool:return self.command_stack.can_redo
    def undo(self)->bool:return self.command_stack.undo()
    def redo(self)->bool:return self.command_stack.redo()
    def execute_undoable(self,label:str,project_id:str,scene_id:str|None,action,*,project_scope:bool=False):
        before=self._capture_project(project_id) if project_scope else self._capture_scene(project_id,str(scene_id or ''))
        result=action()
        after=self._capture_project(project_id) if project_scope else self._capture_scene(project_id,str(scene_id or ''))
        restore=lambda snap: self._restore_project(project_id,snap) if project_scope else self._restore_scene(project_id,str(scene_id or ''),snap)
        self.command_stack.push_executed(TimelineCommand(label,lambda:restore(after),lambda:restore(before),redo=lambda:restore(after)))
        return result
    def active_theme(self,project_id:str):
        theme=self.repository.active_theme(project_id)
        if theme is None:theme=self.repository.save_theme(self.branding.make_theme(project_id,'clean_news'))
        return theme
    def builtin_themes(self):return self.branding.builtin_themes()
    def builtin_layouts(self):return self.layouts.builtin_layouts()
    def builtin_graphics(self):return self.graphics.builtin_presets()
    def apply_theme(self,project_id:str,preset_id:str,*,overrides:dict|None=None):
        old=self.repository.active_theme(project_id);theme=self.branding.make_theme(project_id,preset_id)
        if old: theme.theme_id=old.id;theme.created_at=old.created_at;theme.logo_media_id=old.logo_media_id
        for key,value in (overrides or {}).items():
            attr={'primaryColor':'primary_color','accentColor':'accent_color','fontHeading':'font_heading','fontBody':'font_body','logoMediaId':'logo_media_id'}.get(key,key)
            if hasattr(theme,attr):setattr(theme,attr,value)
        self.repository.save_theme(theme);self._restyle_followers(project_id,theme);return theme
    def customize_theme(self,project_id:str,updates:dict):
        theme=deepcopy(self.active_theme(project_id));
        mapping={'primaryColor':'primary_color','secondaryColor':'secondary_color','accentColor':'accent_color','backgroundColor':'background_color','surfaceColor':'surface_color','textPrimary':'text_primary','textSecondary':'text_secondary','fontHeading':'font_heading','fontBody':'font_body','fontNumbers':'font_numbers','logoMediaId':'logo_media_id'}
        for key,value in updates.items():
            attr=mapping.get(key,key)
            if hasattr(theme,attr):setattr(theme,attr,value)
        theme.preset_id='custom';self.repository.save_theme(theme);self._restyle_followers(project_id,theme);return theme
    def scene_visuals(self,project_id:str,scene_id:str)->dict:
        theme=self.active_theme(project_id);layout=self.repository.layout(project_id,scene_id);elements=self.repository.elements(project_id,scene_id);scene=self.scenes.get(project_id,scene_id)[0]
        rows=[]
        for e in elements:
            overlay=next((o for o in self.scenes.repository.overlays(scene_id) if o.id==e.scene_overlay_id),None)
            if overlay is None:continue
            self._refresh_element_status(project_id,e,overlay)
            claim=self.news_repository.claim(project_id,e.claim_id) if e.claim_id else None
            issues=self.validation.validate_overlay(overlay,scene_duration_ms=scene.duration_ms,element=e,claim=claim)
            rows.append({**e.to_dict(),'overlay':overlay.to_dict(),'issues':[x.to_dict() for x in issues]})
        layout=self.repository.layout(project_id,scene_id)
        return {'theme':theme.to_dict(),'layout':layout.to_dict() if layout else {},'elements':rows,'issues':sum((r['issues'] for r in rows),[])}
    def apply_layout(self,project_id:str,scene_id:str,preset_id:str,*,mode:str='replace',content:dict|None=None)->NewsSceneLayoutInstance:
        if preset_id not in LAYOUT_BY_ID:raise NewsVisualInvalidLayout('News scene layout could not be found.')
        project=self.scenes.project_repository.get_by_id(project_id);scene=self.scenes.get(project_id,scene_id)[0]
        resolved=self.layouts.resolve_layout(preset_id,project.aspect_ratio if project else '16:9',content)
        theme=self.active_theme(project_id);existing=self.repository.layout(project_id,scene_id)
        if existing and existing.customized and mode=='replace': existing.status='reapply_required'
        if mode=='replace':self._remove_managed_overlays(project_id,scene_id)
        layout=NewsSceneLayoutInstance(project_id,scene_id,preset_id,theme.id,LAYOUT_BY_ID[preset_id].version,status='current',customized=False,layout_id=existing.id if existing else str(uuid4()),created_at=existing.created_at if existing else scene.created_at,metadata={'aspectRatio':project.aspect_ratio if project else '16:9','resolved':{k:list(v) if isinstance(v,tuple) else v for k,v in resolved.items() if k in {'card','text','source'}}})
        self.repository.save_layout(layout)
        return layout
    def detach_layout(self,project_id:str,scene_id:str):
        layout=self.repository.layout(project_id,scene_id)
        if layout:
            layout.customized=True;layout.status='detached';self.repository.save_layout(layout)
        for e in self.repository.elements(project_id,scene_id):
            e.follow_theme=False;e.metadata['detached']=True;self.repository.save_element(e)
            overlay=self._overlay(scene_id,e.scene_overlay_id)
            if overlay:overlay.metadata['managedByNewsLayout']=False;self.scenes.repository.update_overlay(project_id,overlay)
        return layout
    def mark_customized(self,project_id:str,scene_id:str)->None:
        layout=self.repository.layout(project_id,scene_id)
        if layout and not layout.customized:layout.customized=True;layout.status='customized';self.repository.save_layout(layout)
    def create_headline(self,project_id:str,scene_id:str,headline:str,*,kicker:str='',source_id:str='',breaking:bool=False,layout_id:str|None=None):
        kind='breaking' if breaking else 'headline';preset=layout_id or 'headline_focus';self.apply_layout(project_id,scene_id,preset,mode='missing')
        src=self.news_repository.source(project_id,source_id) if source_id else None;source_text=f"Source: {src.publisher or src.title}" if src else ''
        return self._create_card(project_id,scene_id,kind,headline,kicker or source_text,source_id=source_id,manual=True,role='headline')
    def create_fact_from_claim(self,project_id:str,scene_id:str,claim_id:str):
        claim=self._approved_claim(project_id,claim_id);source_id,source_text=self._source_for_claim(claim.id)
        self.apply_layout(project_id,scene_id,'fact_focus',mode='missing')
        return self._create_card(project_id,scene_id,'fact',claim.text,source_text,claim_id=claim.id,source_id=source_id,source_hash=content_hash(claim.text),role='fact')
    def create_quote_from_claim(self,project_id:str,scene_id:str,claim_id:str):
        claim=self._approved_claim(project_id,claim_id);text=claim.quote_text or claim.text;kind=claim.quote_kind or 'paraphrase';display=self.graphics.quote_display(text,kind);label=self.graphics.quote_label(kind)
        source_id,source_text=self._source_for_claim(claim.id);secondary=' • '.join(x for x in [claim.speaker,label,source_text] if x)
        self.apply_layout(project_id,scene_id,'quote_focus',mode='missing')
        return self._create_card(project_id,scene_id,'quote',display,secondary,claim_id=claim.id,source_id=source_id,source_hash=content_hash(claim.text),quote_type=kind,role='quote')
    def create_number(self,project_id:str,scene_id:str,value:str,unit:str,label:str,*,claim_id:str='',source_id:str=''):
        if not value.strip() or not label.strip():raise NewsVisualClaimInvalid('Number visual requires an explicit value and label.')
        claim=self._approved_claim(project_id,claim_id) if claim_id else None
        if claim and not source_id:source_id,_=self._source_for_claim(claim.id)
        secondary=' '.join(x for x in [unit.strip(),label.strip()] if x)
        self.apply_layout(project_id,scene_id,'number_focus',mode='missing')
        return self._create_card(project_id,scene_id,'number',value.strip(),secondary,claim_id=claim_id,source_id=source_id,source_hash=content_hash(claim.text) if claim else '',manual=not bool(claim_id),role='number',extra={'rawValue':value,'unit':unit,'label':label})
    def create_source_attribution(self,project_id:str,scene_id:str,source_id:str):
        src=self.news_repository.source(project_id,source_id)
        if src is None:raise NewsVisualSourceMissing('News source could not be found.')
        label=src.publisher or src.title or 'Source';return self._create_text_element(project_id,scene_id,'source',f'Source: {label}','',source_id=source_id,role='source')
    def create_lower_third(self,project_id:str,scene_id:str,primary:str,secondary:str='',*,source_id:str=''):
        self.apply_layout(project_id,scene_id,'media_lower_third',mode='missing');return self._create_card(project_id,scene_id,'lower_third',primary,secondary,source_id=source_id,manual=not bool(source_id),role='lower_third')
    def create_topic(self,project_id:str,scene_id:str,text:str):return self._create_text_element(project_id,scene_id,'topic',text,'',manual=True,role='topic')
    def create_intro(self,project_id:str,scene_id:str,title:str,topic:str=''):
        self.apply_layout(project_id,scene_id,'intro',mode='missing');return self._create_card(project_id,scene_id,'intro',title,topic,manual=True,role='headline')
    def create_outro(self,project_id:str,scene_id:str,text:str='Sources listed in video description'):
        self.apply_layout(project_id,scene_id,'outro',mode='missing');return self._create_card(project_id,scene_id,'outro',text,'',manual=True,role='headline')
    def update_from_claim(self,project_id:str,element_id:str):
        e=self.repository.element(project_id,element_id)
        if not e or not e.claim_id:raise NewsVisualClaimInvalid('This graphic is not linked to a claim.')
        claim=self.news_repository.claim(project_id,e.claim_id)
        if claim is None:raise NewsVisualClaimInvalid('Linked claim could not be found.')
        overlay=self._overlay(e.scene_id,e.scene_overlay_id)
        if overlay is None:raise NewsVisualSourceMissing('Graphic overlay could not be found.')
        if e.graphic_type=='quote':overlay.text=self.graphics.quote_display(claim.quote_text or claim.text,claim.quote_kind or e.quote_type);e.quote_type=claim.quote_kind or e.quote_type
        elif e.graphic_type=='number':pass
        else:overlay.text=claim.text
        e.source_hash=content_hash(claim.text);e.status='current';self.scenes.repository.update_overlay(project_id,overlay);self.repository.save_element(e);return e
    def refresh_statuses(self,project_id:str)->dict:
        counts={'current':0,'source_changed':0,'unsupported_source':0,'manual':0}
        for e in self.repository.elements(project_id):
            o=self._overlay(e.scene_id,e.scene_overlay_id)
            self._refresh_element_status(project_id,e,o)
            counts[e.status]=counts.get(e.status,0)+1
        return counts
    def readiness(self,project_id:str)->dict:
        self.refresh_statuses(project_id);elements=self.repository.elements(project_id)
        result=self.validation.validate_project(project_id,elements,lambda oid:self._overlay_by_id(project_id,oid),lambda cid:self.news_repository.claim(project_id,cid))
        result['sourceChanged']=sum(e.status=='source_changed' for e in elements);result['unsupported']=sum(e.status=='unsupported_source' for e in elements);return result
    def duplicate_project_visuals(self,source_project_id:str,target_project_id:str,*,scene_map:dict[str,str],claim_map:dict[str,str],source_map:dict[str,str],media_map:dict[str,str]|None=None):
        return self.repository.duplicate_project(source_project_id,target_project_id,scene_map=scene_map,claim_map=claim_map,source_map=source_map,media_map=media_map,scene_repository=self.scenes.repository)
    def _create_card(self,project_id,scene_id,kind,text,secondary='',*,claim_id='',source_id='',source_hash='',quote_type='',manual=False,role='fact',extra=None):
        project=self.scenes.project_repository.get_by_id(project_id);layout=self.repository.layout(project_id,scene_id) or self.apply_layout(project_id,scene_id,self.layouts.recommended(role,kind),mode='missing');resolved=self.layouts.resolve_layout(layout.preset_id,project.aspect_ratio if project else '16:9',{})
        theme=self.active_theme(project_id);card=resolved['card'];textg=resolved['text']
        shape=SceneOverlay(scene_id,len(self.scenes.repository.overlays(scene_id)),'shape',x=card[0],y=card[1],width=card[2],height=card[3],opacity=.92,style={'fillColor':theme.surface_color,'radius':theme.corner_radius},metadata={'managedByNewsLayout':True,'newsRole':'card_background','followTheme':True,'newsAppliedGeometry':[card[0],card[1],card[2],card[3]]})
        self.scenes.repository.add_overlay(project_id,shape,self.scenes.get(project_id,scene_id)[0].duration_ms)
        self._save_element_for_overlay(project_id,scene_id,shape,'decoration');self.scenes.repository.update_overlay(project_id,shape)
        return self._create_text_element(project_id,scene_id,kind,text,secondary,claim_id=claim_id,source_id=source_id,source_hash=source_hash,quote_type=quote_type,manual=manual,role=role,geometry=textg,extra=extra)
    def _create_text_element(self,project_id,scene_id,kind,text,secondary='',*,claim_id='',source_id='',source_hash='',quote_type='',manual=False,role='body',geometry=None,extra=None):
        theme=self.active_theme(project_id);project=self.scenes.project_repository.get_by_id(project_id);layout=self.repository.layout(project_id,scene_id)
        if geometry is None:
            resolved=self.layouts.resolve_layout(layout.preset_id if layout else 'full_media',project.aspect_ratio if project else '16:9',{});geometry=resolved['source'] if role=='source' else resolved['text']
        font=theme.font_numbers if role=='number' else (theme.font_heading if role in {'headline','quote'} else theme.font_body);size=78 if role=='number' else (58 if role in {'headline','quote'} else 34)
        overlay_type='lower_third' if kind=='lower_third' else ('headline' if role in {'headline','quote','number'} else 'label')
        overlay=SceneOverlay(scene_id,len(self.scenes.repository.overlays(scene_id)),overlay_type,text=text,secondary_text=secondary,x=geometry[0],y=geometry[1],width=geometry[2],height=geometry[3],style={'fontFamily':font,'fontSize':size,'fontWeight':700 if role in {'headline','number'} else 500,'color':theme.text_primary,'alignment':'left'},metadata={'managedByNewsLayout':True,'newsRole':role,'followTheme':True,'newsAppliedGeometry':[geometry[0],geometry[1],geometry[2],geometry[3]]})
        self.scenes.repository.add_overlay(project_id,overlay,self.scenes.get(project_id,scene_id)[0].duration_ms)
        e=self._save_element_for_overlay(project_id,scene_id,overlay,kind,claim_id=claim_id,source_id=source_id,source_hash=source_hash,quote_type=quote_type,status='manual' if manual else 'current',extra=extra)
        overlay.metadata['newsVisualElementId']=e.id;self.scenes.repository.update_overlay(project_id,overlay)
        return e
    def _save_element_for_overlay(self,project_id,scene_id,overlay,kind,*,claim_id='',source_id='',source_hash='',quote_type='',status='current',extra=None):
        e=NewsVisualElement(project_id,scene_id,overlay.id,kind,claim_id,source_id,quote_type,True,status,source_hash,metadata=dict(extra or {}));self.repository.save_element(e);overlay.metadata['newsVisualElementId']=e.id;return e
    def _approved_claim(self,project_id,claim_id):
        c=self.news_repository.claim(project_id,claim_id)
        if c is None or c.status_code!='approved':raise NewsVisualClaimInvalid('Fact visuals require an approved News claim.')
        return c
    def _source_for_claim(self,claim_id):
        ev=self.news_repository.evidence_for_claim(claim_id)
        if not ev:return '',''
        # Evidence/source ownership is enforced by the News schema; resolve display metadata without mutating provenance.
        with self.repository.database.connect() as c:r=c.execute('SELECT title,publisher FROM news_sources WHERE id=?',(ev[0].source_id,)).fetchone()
        label=(str(r['publisher'] or r['title']) if r else '')
        return ev[0].source_id,(f'Source: {label}' if label else '')
    def _remove_managed_overlays(self,project_id,scene_id):
        for e in list(self.repository.elements(project_id,scene_id)):
            try:self.scenes.repository.delete_overlay(project_id,e.scene_overlay_id)
            except KeyError:pass
            self.repository.delete_element(project_id,e.id)
    def _overlay(self,scene_id,overlay_id):return next((o for o in self.scenes.repository.overlays(scene_id) if o.id==overlay_id),None)
    def _overlay_by_id(self,project_id,overlay_id):
        with self.repository.database.connect() as c:r=c.execute('SELECT scene_id FROM scene_overlays WHERE id=? AND scene_id IN (SELECT id FROM scenes WHERE project_id=?)',(overlay_id,project_id)).fetchone()
        return self._overlay(str(r['scene_id']),overlay_id) if r else None
    def _refresh_element_status(self,project_id,e,overlay):
        if overlay is not None:
            applied=list(overlay.metadata.get('newsAppliedGeometry',[]) or [])
            now=[overlay.x,overlay.y,overlay.width,overlay.height]
            if len(applied)==4 and any(abs(float(a)-float(b))>1e-5 for a,b in zip(applied,now)):
                self.mark_customized(project_id,e.scene_id)
        if e.status=='manual':return e
        if e.claim_id:
            c=self.news_repository.claim(project_id,e.claim_id)
            if c is None or c.status_code in {'rejected','unsupported','conflicting'}:e.status='unsupported_source'
            elif c.status_code!='approved' or (e.source_hash and e.source_hash!=content_hash(c.text)):e.status='source_changed'
            else:e.status='current'
        self.repository.save_element(e);return e
    def _capture_scene(self,project_id,scene_id):
        if not scene_id:return {'overlays':[],'layout':None,'elements':[]}
        return {'overlays':deepcopy(self.scenes.repository.overlays(scene_id)),'layout':deepcopy(self.repository.layout(project_id,scene_id)),'elements':deepcopy(self.repository.elements(project_id,scene_id))}
    def _restore_scene(self,project_id,scene_id,snapshot):
        scene=self.scenes.repository.get(scene_id)
        if scene is None:return
        self.repository.clear_scene_records(project_id,scene_id)
        self.scenes.repository.replace_overlays(project_id,scene_id,deepcopy(snapshot.get('overlays',[])),scene.duration_ms)
        layout=deepcopy(snapshot.get('layout'))
        if layout:self.repository.save_layout(layout)
        for element in deepcopy(snapshot.get('elements',[])):self.repository.save_element(element)
    def _capture_project(self,project_id):
        scene_ids=[s.id for s in self.scenes.repository.list_for_project(project_id)]
        return {'themes':deepcopy(self.repository.themes(project_id)),'scenes':{sid:self._capture_scene(project_id,sid) for sid in scene_ids}}
    def _restore_project(self,project_id,snapshot):
        self.repository.clear_project_records(project_id,include_themes=True)
        for theme in deepcopy(snapshot.get('themes',[])):self.repository.save_theme(theme)
        for scene_id,state in snapshot.get('scenes',{}).items():self._restore_scene(project_id,scene_id,deepcopy(state))
    def _restyle_followers(self,project_id,theme):
        for e in self.repository.elements(project_id):
            if not e.follow_theme:continue
            o=self._overlay(e.scene_id,e.scene_overlay_id)
            if not o:continue
            if o.type_code=='shape':o.style['fillColor']=theme.surface_color
            else:
                role=str(o.metadata.get('newsRole','body'));o.style['fontFamily']=theme.font_numbers if role=='number' else (theme.font_heading if role in {'headline','quote'} else theme.font_body);o.style['color']=theme.text_primary
            self.scenes.repository.update_overlay(project_id,o)
