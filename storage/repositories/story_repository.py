from __future__ import annotations
import json
from copy import deepcopy
from uuid import uuid4

from domain.project import utc_now_iso
from domain.story_project import StoryProjectMetadata
from domain.story_outline import StoryOutline
from domain.story_beat import StoryBeat
from domain.story_character import StoryCharacter
from storage.database import SQLiteDatabase


def _j(value:object)->str:return json.dumps(value,ensure_ascii=False,separators=(",",":"))
def _d(value:str|None,default):
    try:return json.loads(value or "")
    except Exception:return default

class StoryRepository:
    def __init__(self,database:SQLiteDatabase)->None:self.database=database

    def get_project(self,project_id:str)->StoryProjectMetadata|None:
        with self.database.connect() as c:r=c.execute('SELECT * FROM story_projects WHERE project_id=?',(project_id,)).fetchone()
        return StoryProjectMetadata.from_record(r) if r else None
    def save_project(self,item:StoryProjectMetadata)->StoryProjectMetadata:
        item.validate()
        with self.database.connect() as c,c:
            c.execute('''INSERT INTO story_projects(project_id,title,idea,story_type,language,target_duration_ms,audience,tone,pace,status,narrator_voice_id,notes,source_fingerprint,metadata_json,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(project_id) DO UPDATE SET title=excluded.title,idea=excluded.idea,story_type=excluded.story_type,language=excluded.language,target_duration_ms=excluded.target_duration_ms,audience=excluded.audience,tone=excluded.tone,pace=excluded.pace,status=excluded.status,narrator_voice_id=excluded.narrator_voice_id,notes=excluded.notes,source_fingerprint=excluded.source_fingerprint,metadata_json=excluded.metadata_json,updated_at=excluded.updated_at''',
            (item.project_id,item.title,item.idea,item.story_type,item.language,item.target_duration_ms,item.audience,item.tone,item.pace,item.status,item.narrator_voice_id,item.notes,item.source_fingerprint,_j(item.metadata),item.created_at,item.updated_at))
        return item

    def outlines(self,project_id:str)->list[StoryOutline]:
        with self.database.connect() as c:rows=c.execute('SELECT * FROM story_outlines WHERE project_id=? ORDER BY created_at',(project_id,)).fetchall()
        return [StoryOutline.from_record(r) for r in rows]
    def latest_outline(self,project_id:str)->StoryOutline|None:
        with self.database.connect() as c:r=c.execute('SELECT * FROM story_outlines WHERE project_id=? ORDER BY updated_at DESC LIMIT 1',(project_id,)).fetchone()
        return StoryOutline.from_record(r) if r else None
    def outline(self,project_id:str,outline_id:str)->StoryOutline|None:
        with self.database.connect() as c:r=c.execute('SELECT * FROM story_outlines WHERE id=? AND project_id=?',(outline_id,project_id)).fetchone()
        return StoryOutline.from_record(r) if r else None
    def create_outline(self,item:StoryOutline,beats:list[StoryBeat])->StoryOutline:
        item.validate()
        with self.database.connect() as c,c:
            c.execute('INSERT INTO story_outlines(id,project_id,title,summary,status,outline_version,source_fingerprint,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)',(item.id,item.project_id,item.title,item.summary,item.status,item.version,item.source_fingerprint,_j(item.metadata),item.created_at,item.updated_at))
            for beat in beats:self._insert_beat(c,beat)
        return item
    def save_outline(self,item:StoryOutline)->StoryOutline:
        item.validate();item.updated_at=utc_now_iso()
        with self.database.connect() as c,c:
            cur=c.execute('UPDATE story_outlines SET title=?,summary=?,status=?,outline_version=?,source_fingerprint=?,metadata_json=?,updated_at=? WHERE id=? AND project_id=?',(item.title,item.summary,item.status,item.version,item.source_fingerprint,_j(item.metadata),item.updated_at,item.id,item.project_id))
            if cur.rowcount==0:raise KeyError('Story outline not found.')
        return item
    def delete_outline(self,project_id:str,outline_id:str)->None:
        with self.database.connect() as c,c:c.execute('DELETE FROM story_outlines WHERE id=? AND project_id=?',(outline_id,project_id))

    def beats(self,outline_id:str)->list[StoryBeat]:
        with self.database.connect() as c:rows=c.execute('SELECT * FROM story_beats WHERE outline_id=? ORDER BY beat_order,created_at',(outline_id,)).fetchall()
        return [StoryBeat.from_record(r) for r in rows]
    def beat(self,project_id:str,beat_id:str)->StoryBeat|None:
        with self.database.connect() as c:r=c.execute('''SELECT b.* FROM story_beats b JOIN story_outlines o ON o.id=b.outline_id WHERE b.id=? AND o.project_id=?''',(beat_id,project_id)).fetchone()
        return StoryBeat.from_record(r) if r else None
    def add_beat(self,project_id:str,item:StoryBeat)->StoryBeat:
        item.validate()
        with self.database.connect() as c,c:
            owner=c.execute('SELECT 1 FROM story_outlines WHERE id=? AND project_id=?',(item.outline_id,project_id)).fetchone()
            if not owner:raise KeyError('Story outline not found.')
            self._insert_beat(c,item)
        return item
    def save_beat(self,project_id:str,item:StoryBeat)->StoryBeat:
        item.validate();item.updated_at=utc_now_iso()
        with self.database.connect() as c,c:
            cur=c.execute('''UPDATE story_beats SET beat_order=?,beat_type=?,title=?,description=?,target_duration_ms=?,emotion=?,visual_direction=?,script_section_id=?,locked=?,user_modified=?,chapter_title=?,character_id=?,voice_override_id=?,notes=?,metadata_json=?,updated_at=? WHERE id=? AND outline_id IN (SELECT id FROM story_outlines WHERE project_id=?)''',(item.order,item.beat_type,item.title,item.description,item.target_duration_ms,item.emotion,item.visual_direction,item.script_section_id or None,int(item.locked),int(item.user_modified),item.chapter_title,item.character_id or None,item.voice_override_id,item.notes,_j(item.metadata),item.updated_at,item.id,project_id))
            if cur.rowcount==0:raise KeyError('Story beat not found.')
        return item
    def delete_beat(self,project_id:str,beat_id:str)->None:
        with self.database.connect() as c,c:c.execute('DELETE FROM story_beats WHERE id=? AND outline_id IN (SELECT id FROM story_outlines WHERE project_id=?)',(beat_id,project_id))
    def replace_beats(self,project_id:str,outline_id:str,beats:list[StoryBeat])->None:
        """Replace outline structure while preserving mappings for retained beat IDs."""
        with self.database.connect() as c,c:
            if not c.execute('SELECT 1 FROM story_outlines WHERE id=? AND project_id=?',(outline_id,project_id)).fetchone():raise KeyError('Story outline not found.')
            existing={str(r['id']) for r in c.execute('SELECT id FROM story_beats WHERE outline_id=?',(outline_id,)).fetchall()}
            wanted={b.id for b in beats}
            for beat_id in existing-wanted:
                c.execute('DELETE FROM story_beats WHERE id=? AND outline_id=?',(beat_id,outline_id))
            now=utc_now_iso()
            for order,b in enumerate(beats):
                b.order=order;b.outline_id=outline_id;b.updated_at=now;b.validate()
                if b.id in existing:
                    c.execute('''UPDATE story_beats SET beat_order=?,beat_type=?,title=?,description=?,target_duration_ms=?,emotion=?,visual_direction=?,script_section_id=?,locked=?,user_modified=?,chapter_title=?,character_id=?,voice_override_id=?,notes=?,metadata_json=?,updated_at=? WHERE id=? AND outline_id=?''',(b.order,b.beat_type,b.title,b.description,b.target_duration_ms,b.emotion,b.visual_direction,b.script_section_id or None,int(b.locked),int(b.user_modified),b.chapter_title,b.character_id or None,b.voice_override_id,b.notes,_j(b.metadata),b.updated_at,b.id,outline_id))
                else:self._insert_beat(c,b)
    def save_order(self,project_id:str,outline_id:str,beats:list[StoryBeat])->None:
        now=utc_now_iso()
        with self.database.connect() as c,c:
            if not c.execute('SELECT 1 FROM story_outlines WHERE id=? AND project_id=?',(outline_id,project_id)).fetchone():raise KeyError('Story outline not found.')
            for order,b in enumerate(beats):
                b.order=order;b.updated_at=now;c.execute('UPDATE story_beats SET beat_order=?,updated_at=? WHERE id=? AND outline_id=?',(order,now,b.id,outline_id))

    def characters(self,project_id:str)->list[StoryCharacter]:
        with self.database.connect() as c:rows=c.execute('SELECT * FROM story_characters WHERE project_id=? ORDER BY created_at',(project_id,)).fetchall()
        return [StoryCharacter.from_record(r) for r in rows]
    def character(self,project_id:str,character_id:str)->StoryCharacter|None:
        with self.database.connect() as c:r=c.execute('SELECT * FROM story_characters WHERE id=? AND project_id=?',(character_id,project_id)).fetchone()
        return StoryCharacter.from_record(r) if r else None
    def save_character(self,item:StoryCharacter)->StoryCharacter:
        item.validate();item.updated_at=utc_now_iso()
        with self.database.connect() as c,c:c.execute('''INSERT INTO story_characters(id,project_id,name,role,description,voice_id,notes,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,role=excluded.role,description=excluded.description,voice_id=excluded.voice_id,notes=excluded.notes,metadata_json=excluded.metadata_json,updated_at=excluded.updated_at''',(item.id,item.project_id,item.name,item.role,item.description,item.voice_id,item.notes,_j(item.metadata),item.created_at,item.updated_at))
        return item
    def delete_character(self,project_id:str,character_id:str)->None:
        with self.database.connect() as c,c:
            c.execute("UPDATE story_beats SET character_id=NULL WHERE character_id=? AND outline_id IN (SELECT id FROM story_outlines WHERE project_id=?)",(character_id,project_id))
            c.execute('DELETE FROM story_characters WHERE id=? AND project_id=?',(character_id,project_id))

    def mappings(self,project_id:str,*,mapping_type:str|None=None,beat_id:str|None=None)->list[dict[str,object]]:
        q='SELECT * FROM story_mappings WHERE project_id=?';args:list[object]=[project_id]
        if mapping_type:q+=' AND mapping_type=?';args.append(mapping_type)
        if beat_id:q+=' AND beat_id=?';args.append(beat_id)
        q+=' ORDER BY created_at'
        with self.database.connect() as c:rows=c.execute(q,tuple(args)).fetchall()
        return [self._mapping_dict(r) for r in rows]
    def mapping_for_target(self,project_id:str,mapping_type:str,target_id:str)->dict[str,object]|None:
        with self.database.connect() as c:r=c.execute('SELECT * FROM story_mappings WHERE project_id=? AND mapping_type=? AND target_id=?',(project_id,mapping_type,target_id)).fetchone()
        return self._mapping_dict(r) if r else None
    def save_mapping(self,project_id:str,beat_id:str,mapping_type:str,target_id:str,source_hash:str,status:str='current',metadata:dict|None=None,mapping_id:str|None=None)->str:
        mid=mapping_id or str(uuid4());now=utc_now_iso()
        with self.database.connect() as c,c:
            existing=c.execute('SELECT id,created_at FROM story_mappings WHERE project_id=? AND beat_id=? AND mapping_type=? AND target_id=?',(project_id,beat_id,mapping_type,target_id)).fetchone()
            if existing:mid=str(existing['id']);created=str(existing['created_at'])
            else:created=now
            c.execute('''INSERT INTO story_mappings(id,project_id,beat_id,mapping_type,target_id,source_hash,status,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET beat_id=excluded.beat_id,target_id=excluded.target_id,source_hash=excluded.source_hash,status=excluded.status,metadata_json=excluded.metadata_json,updated_at=excluded.updated_at''',(mid,project_id,beat_id,mapping_type,target_id,source_hash,status,_j(metadata or {}),created,now))
        return mid
    def update_mapping_status(self,project_id:str,mapping_id:str,status:str)->None:
        with self.database.connect() as c,c:c.execute('UPDATE story_mappings SET status=?,updated_at=? WHERE id=? AND project_id=?',(status,utc_now_iso(),mapping_id,project_id))
    def delete_mappings_for_beat(self,project_id:str,beat_id:str)->None:
        with self.database.connect() as c,c:c.execute('DELETE FROM story_mappings WHERE project_id=? AND beat_id=?',(project_id,beat_id))

    def duplicate_project(self,source_project_id:str,target_project_id:str,*,section_map:dict[str,str]|None=None,scene_map:dict[str,str]|None=None)->dict[str,dict[str,str]]:
        section_map=section_map or {};scene_map=scene_map or {};maps={"outline":{},"beat":{},"character":{},"mapping":{}}
        meta=self.get_project(source_project_id)
        if meta:
            clone=deepcopy(meta);clone.project_id=target_project_id;clone.created_at=clone.updated_at=utc_now_iso();self.save_project(clone)
        chars=self.characters(source_project_id)
        for item in chars:
            old=item.id;item.character_id=str(uuid4());item.project_id=target_project_id;item.created_at=item.updated_at=utc_now_iso();self.save_character(item);maps['character'][old]=item.id
        for outline in self.outlines(source_project_id):
            old_outline=outline.id;beats=self.beats(outline.id);outline.outline_id=str(uuid4());outline.project_id=target_project_id;outline.created_at=outline.updated_at=utc_now_iso();mapped_beats=[]
            for beat in beats:
                old=beat.id;beat.beat_id=str(uuid4());beat.outline_id=outline.id;beat.script_section_id=section_map.get(beat.script_section_id,'') if beat.script_section_id else '';beat.character_id=maps['character'].get(beat.character_id,'') if beat.character_id else '';beat.created_at=beat.updated_at=utc_now_iso();mapped_beats.append(beat);maps['beat'][old]=beat.id
            self.create_outline(outline,mapped_beats);maps['outline'][old_outline]=outline.id
        for row in self.mappings(source_project_id):
            target=str(row['targetId']);kind=str(row['mappingType'])
            if kind=='script_section':target=section_map.get(target,'')
            elif kind=='scene':target=scene_map.get(target,'')
            if not target:continue
            mapped_beat=maps['beat'].get(str(row['beatId']),'')
            if not mapped_beat:continue
            new_id=self.save_mapping(target_project_id,mapped_beat,kind,target,str(row['sourceHash']),str(row['status']),dict(row['metadata']))
            maps['mapping'][str(row['id'])]=new_id
        return maps

    @staticmethod
    def _insert_beat(c,item:StoryBeat)->None:
        item.validate();c.execute('''INSERT INTO story_beats(id,outline_id,beat_order,beat_type,title,description,target_duration_ms,emotion,visual_direction,script_section_id,locked,user_modified,chapter_title,character_id,voice_override_id,notes,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(item.id,item.outline_id,item.order,item.beat_type,item.title,item.description,item.target_duration_ms,item.emotion,item.visual_direction,item.script_section_id or None,int(item.locked),int(item.user_modified),item.chapter_title,item.character_id or None,item.voice_override_id,item.notes,_j(item.metadata),item.created_at,item.updated_at))
    @staticmethod
    def _mapping_dict(r)->dict[str,object]:
        return {"id":str(r['id']),"projectId":str(r['project_id']),"beatId":str(r['beat_id']),"mappingType":str(r['mapping_type']),"targetId":str(r['target_id']),"sourceHash":str(r['source_hash'] or ''),"status":str(r['status']),"metadata":_d(str(r['metadata_json'] or '{}'),{}),"createdAt":str(r['created_at']),"updatedAt":str(r['updated_at'])}
