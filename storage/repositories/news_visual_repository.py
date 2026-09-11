from __future__ import annotations
import json
from uuid import uuid4
from domain.news_visual_theme import NewsVisualTheme
from domain.news_scene_layout import NewsSceneLayoutInstance
from domain.news_visual_element import NewsVisualElement
from domain.project import utc_now_iso
from storage.database import SQLiteDatabase

def _j(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
class NewsVisualRepository:
    def __init__(self,database:SQLiteDatabase)->None:self.database=database
    def save_theme(self,t:NewsVisualTheme)->NewsVisualTheme:
        t.validate();t.updated_at=utc_now_iso()
        with self.database.connect() as c,c:
            if t.active:c.execute('UPDATE news_visual_themes SET active=0 WHERE project_id=?',(t.project_id,))
            c.execute('''INSERT INTO news_visual_themes(id,project_id,name,preset_id,active,primary_color,secondary_color,accent_color,background_color,surface_color,text_primary,text_secondary,font_heading,font_body,font_numbers,corner_radius,spacing_scale,logo_media_id,default_animation_style,metadata_json,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,preset_id=excluded.preset_id,active=excluded.active,primary_color=excluded.primary_color,secondary_color=excluded.secondary_color,accent_color=excluded.accent_color,background_color=excluded.background_color,surface_color=excluded.surface_color,text_primary=excluded.text_primary,text_secondary=excluded.text_secondary,font_heading=excluded.font_heading,font_body=excluded.font_body,font_numbers=excluded.font_numbers,corner_radius=excluded.corner_radius,spacing_scale=excluded.spacing_scale,logo_media_id=excluded.logo_media_id,default_animation_style=excluded.default_animation_style,metadata_json=excluded.metadata_json,updated_at=excluded.updated_at''',
            (t.id,t.project_id,t.name,t.preset_id,int(t.active),t.primary_color,t.secondary_color,t.accent_color,t.background_color,t.surface_color,t.text_primary,t.text_secondary,t.font_heading,t.font_body,t.font_numbers,t.corner_radius,t.spacing_scale,t.logo_media_id,t.default_animation_style,_j(t.metadata),t.created_at,t.updated_at))
        return t
    def theme(self,project_id:str,theme_id:str)->NewsVisualTheme|None:
        with self.database.connect() as c:r=c.execute('SELECT * FROM news_visual_themes WHERE id=? AND project_id=?',(theme_id,project_id)).fetchone()
        return NewsVisualTheme.from_record(r) if r else None
    def active_theme(self,project_id:str)->NewsVisualTheme|None:
        with self.database.connect() as c:r=c.execute('SELECT * FROM news_visual_themes WHERE project_id=? AND active=1 ORDER BY updated_at DESC LIMIT 1',(project_id,)).fetchone()
        return NewsVisualTheme.from_record(r) if r else None
    def themes(self,project_id:str)->list[NewsVisualTheme]:
        with self.database.connect() as c:rs=c.execute('SELECT * FROM news_visual_themes WHERE project_id=? ORDER BY active DESC,updated_at DESC',(project_id,)).fetchall()
        return [NewsVisualTheme.from_record(r) for r in rs]
    def save_layout(self,x:NewsSceneLayoutInstance)->NewsSceneLayoutInstance:
        x.updated_at=utc_now_iso()
        with self.database.connect() as c,c:c.execute('''INSERT INTO news_scene_layouts(id,project_id,scene_id,preset_id,preset_version,theme_id,status,customized,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(scene_id) DO UPDATE SET preset_id=excluded.preset_id,preset_version=excluded.preset_version,theme_id=excluded.theme_id,status=excluded.status,customized=excluded.customized,metadata_json=excluded.metadata_json,updated_at=excluded.updated_at''',(x.id,x.project_id,x.scene_id,x.preset_id,x.preset_version,x.theme_id or None,x.status,int(x.customized),_j(x.metadata),x.created_at,x.updated_at))
        return self.layout(x.project_id,x.scene_id) or x
    def layout(self,project_id:str,scene_id:str)->NewsSceneLayoutInstance|None:
        with self.database.connect() as c:r=c.execute('SELECT * FROM news_scene_layouts WHERE project_id=? AND scene_id=?',(project_id,scene_id)).fetchone()
        return NewsSceneLayoutInstance.from_record(r) if r else None
    def layouts(self,project_id:str)->list[NewsSceneLayoutInstance]:
        with self.database.connect() as c:rs=c.execute('SELECT * FROM news_scene_layouts WHERE project_id=? ORDER BY created_at',(project_id,)).fetchall()
        return [NewsSceneLayoutInstance.from_record(r) for r in rs]
    def save_element(self,x:NewsVisualElement)->NewsVisualElement:
        x.updated_at=utc_now_iso()
        with self.database.connect() as c,c:c.execute('''INSERT INTO news_visual_elements(id,project_id,scene_id,scene_overlay_id,graphic_type,claim_id,source_id,quote_type,follow_theme,status,source_hash,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(scene_overlay_id) DO UPDATE SET graphic_type=excluded.graphic_type,claim_id=excluded.claim_id,source_id=excluded.source_id,quote_type=excluded.quote_type,follow_theme=excluded.follow_theme,status=excluded.status,source_hash=excluded.source_hash,metadata_json=excluded.metadata_json,updated_at=excluded.updated_at''',(x.id,x.project_id,x.scene_id,x.scene_overlay_id,x.graphic_type,x.claim_id or None,x.source_id or None,x.quote_type,int(x.follow_theme),x.status,x.source_hash,_j(x.metadata),x.created_at,x.updated_at))
        return x
    def element(self,project_id:str,element_id:str)->NewsVisualElement|None:
        with self.database.connect() as c:r=c.execute('SELECT * FROM news_visual_elements WHERE id=? AND project_id=?',(element_id,project_id)).fetchone()
        return NewsVisualElement.from_record(r) if r else None
    def element_for_overlay(self,project_id:str,overlay_id:str)->NewsVisualElement|None:
        with self.database.connect() as c:r=c.execute('SELECT * FROM news_visual_elements WHERE scene_overlay_id=? AND project_id=?',(overlay_id,project_id)).fetchone()
        return NewsVisualElement.from_record(r) if r else None
    def elements(self,project_id:str,scene_id:str|None=None)->list[NewsVisualElement]:
        q='SELECT * FROM news_visual_elements WHERE project_id=?';args=[project_id]
        if scene_id:q+=' AND scene_id=?';args.append(scene_id)
        q+=' ORDER BY created_at'
        with self.database.connect() as c:rs=c.execute(q,tuple(args)).fetchall()
        return [NewsVisualElement.from_record(r) for r in rs]
    def delete_element(self,project_id:str,element_id:str)->None:
        with self.database.connect() as c,c:c.execute('DELETE FROM news_visual_elements WHERE id=? AND project_id=?',(element_id,project_id))
    def clear_scene_records(self,project_id:str,scene_id:str)->None:
        with self.database.connect() as c,c:
            c.execute('DELETE FROM news_visual_elements WHERE project_id=? AND scene_id=?',(project_id,scene_id))
            c.execute('DELETE FROM news_scene_layouts WHERE project_id=? AND scene_id=?',(project_id,scene_id))
    def clear_project_records(self,project_id:str,*,include_themes:bool=False)->None:
        with self.database.connect() as c,c:
            c.execute('DELETE FROM news_visual_elements WHERE project_id=?',(project_id,))
            c.execute('DELETE FROM news_scene_layouts WHERE project_id=?',(project_id,))
            if include_themes:c.execute('DELETE FROM news_visual_themes WHERE project_id=?',(project_id,))
    def duplicate_project(self,source_project_id:str,target_project_id:str,*,scene_map:dict[str,str],claim_map:dict[str,str],source_map:dict[str,str],media_map:dict[str,str]|None=None,scene_repository)->dict[str,dict[str,str]]:
        maps={'theme':{},'layout':{},'element':{}};media_map=media_map or {}
        themes=self.themes(source_project_id)
        for t in themes:
            old=t.id;t.theme_id=str(uuid4());t.project_id=target_project_id;t.logo_media_id=media_map.get(t.logo_media_id,'') if t.logo_media_id else '';t.created_at=t.updated_at=utc_now_iso();self.save_theme(t);maps['theme'][old]=t.id
        for l in self.layouts(source_project_id):
            if l.scene_id not in scene_map:continue
            old=l.id;l.layout_id=str(uuid4());l.project_id=target_project_id;l.scene_id=scene_map[l.scene_id];l.theme_id=maps['theme'].get(l.theme_id,'');l.created_at=l.updated_at=utc_now_iso();self.save_layout(l);maps['layout'][old]=l.id
        for e in self.elements(source_project_id):
            if e.scene_id not in scene_map:continue
            target_scene=scene_map[e.scene_id]; overlays=scene_repository.overlays(target_scene)
            cloned=next((o for o in overlays if str(o.metadata.get('newsVisualElementId',''))==e.id),None)
            if cloned is None:continue
            old=e.id;e.element_id=str(uuid4());e.project_id=target_project_id;e.scene_id=target_scene;e.scene_overlay_id=cloned.id;e.claim_id=claim_map.get(e.claim_id,'') if e.claim_id else '';e.source_id=source_map.get(e.source_id,'') if e.source_id else '';e.created_at=e.updated_at=utc_now_iso();cloned.metadata['newsVisualElementId']=e.id;scene_repository.update_overlay(target_project_id,cloned);self.save_element(e);maps['element'][old]=e.id
        return maps
