from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path

NOW="2026-01-01T00:00:00+00:00"

# Milestones are names/table families taken from the repository's real migrations.
# They document fixture coverage without inventing historical columns that did not exist.
REAL_MILESTONE_FIXTURES = {
    "early_project_media": (1, 2, ("projects", "media_assets")),
    "script_only": (3, 3, ("scripts", "script_sections")),
    "scene_subtitle": (9, 10, ("subtitle_tracks", "subtitle_cues", "scenes")),
    "advanced_timeline": (14, 14, ("timeline_clips",)),
    "news": (15, 16, ("news_projects", "news_sources", "news_claims")),
    "story_dub": (17, 18, ("story_projects", "story_beats", "dubbing_projects", "dub_mix_settings")),
    "phase22_multilingual": (19, 19, ("speakers", "speech_blocks", "scene_layers")),
    "audio_mixer": (25, 25, ("audio_tracks", "audio_buses", "audio_mix_settings")),
    "current": (28, 28, ("projects", "migration_history", "migration_state")),
}

SCHEMA="""
PRAGMA foreign_keys=ON;
CREATE TABLE projects(id TEXT PRIMARY KEY,title TEXT NOT NULL,workflow TEXT NOT NULL,language TEXT NOT NULL,aspect_ratio TEXT NOT NULL,fps INTEGER NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,last_opened_at TEXT,thumbnail_path TEXT,status TEXT NOT NULL,project_path TEXT NOT NULL UNIQUE,version INTEGER NOT NULL,project_schema_version INTEGER NOT NULL DEFAULT 1);
CREATE TABLE media_assets(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,file_path TEXT NOT NULL,metadata_json TEXT NOT NULL DEFAULT '{}',FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE);
CREATE TABLE scripts(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,title TEXT NOT NULL,language TEXT NOT NULL,status TEXT NOT NULL,pace TEXT NOT NULL DEFAULT 'normal',version INTEGER NOT NULL,notes TEXT,metadata_json TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE);
CREATE TABLE script_sections(id TEXT PRIMARY KEY,script_id TEXT NOT NULL,section_order INTEGER NOT NULL,section_type TEXT NOT NULL,title TEXT NOT NULL,content TEXT NOT NULL,notes TEXT,enabled INTEGER NOT NULL,metadata_json TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,FOREIGN KEY(script_id) REFERENCES scripts(id) ON DELETE CASCADE);
CREATE TABLE scenes(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,name TEXT NOT NULL,metadata_json TEXT NOT NULL DEFAULT '{}',FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE);
CREATE TABLE scene_layers(id TEXT PRIMARY KEY,scene_id TEXT NOT NULL,media_id TEXT,metadata_json TEXT NOT NULL DEFAULT '{}',FOREIGN KEY(scene_id) REFERENCES scenes(id) ON DELETE CASCADE,FOREIGN KEY(media_id) REFERENCES media_assets(id) ON DELETE SET NULL);
CREATE TABLE subtitle_tracks(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,name TEXT NOT NULL,language TEXT NOT NULL,FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE);
CREATE TABLE subtitle_cues(id TEXT PRIMARY KEY,track_id TEXT NOT NULL,text TEXT NOT NULL,start_ms INTEGER NOT NULL,end_ms INTEGER NOT NULL,FOREIGN KEY(track_id) REFERENCES subtitle_tracks(id) ON DELETE CASCADE);
CREATE TABLE speakers(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,name TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'speaker',voice_id TEXT NOT NULL DEFAULT '',language TEXT NOT NULL DEFAULT 'en',description TEXT NOT NULL DEFAULT '',avatar TEXT NOT NULL DEFAULT '',metadata_json TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL,updated_at TEXT NOT NULL,FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE);
CREATE TABLE speech_blocks(id TEXT PRIMARY KEY,script_section_id TEXT NOT NULL,block_order INTEGER NOT NULL,speaker_id TEXT,text TEXT NOT NULL DEFAULT '',language TEXT NOT NULL DEFAULT 'en',voice_override_id TEXT NOT NULL DEFAULT '',speech_source_type TEXT NOT NULL DEFAULT 'tts',pause_before_ms INTEGER NOT NULL DEFAULT 0,pause_after_ms INTEGER NOT NULL DEFAULT 180,scene_id TEXT,start_offset_ms INTEGER,audio_id TEXT NOT NULL DEFAULT '',metadata_json TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL,updated_at TEXT NOT NULL,FOREIGN KEY(script_section_id) REFERENCES script_sections(id) ON DELETE CASCADE,FOREIGN KEY(speaker_id) REFERENCES speakers(id) ON DELETE SET NULL,FOREIGN KEY(scene_id) REFERENCES scenes(id) ON DELETE SET NULL);
CREATE TABLE generated_audio(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,file_path TEXT NOT NULL,FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE);
CREATE TABLE timeline_clips(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,scene_id TEXT,media_id TEXT,metadata_json TEXT NOT NULL DEFAULT '{}',FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,FOREIGN KEY(scene_id) REFERENCES scenes(id) ON DELETE SET NULL,FOREIGN KEY(media_id) REFERENCES media_assets(id) ON DELETE SET NULL);
CREATE TABLE dubbing_projects(project_id TEXT PRIMARY KEY,source_language TEXT NOT NULL DEFAULT 'auto',target_language TEXT NOT NULL DEFAULT 'km',metadata_json TEXT NOT NULL DEFAULT '{}',FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE);
CREATE TABLE dub_mix_settings(project_id TEXT PRIMARY KEY,mode TEXT NOT NULL DEFAULT 'duck',original_volume REAL NOT NULL DEFAULT .25,dub_volume REAL NOT NULL DEFAULT 1,duck_normal_volume REAL NOT NULL DEFAULT .25,duck_under_volume REAL NOT NULL DEFAULT .12,duck_fade_ms INTEGER NOT NULL DEFAULT 120,metadata_json TEXT NOT NULL DEFAULT '{}',updated_at TEXT NOT NULL,FOREIGN KEY(project_id) REFERENCES dubbing_projects(project_id) ON DELETE CASCADE);
CREATE TABLE audio_buses(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,name TEXT NOT NULL,role TEXT NOT NULL,bus_order INTEGER NOT NULL DEFAULT 0,gain_db REAL NOT NULL DEFAULT 0,muted INTEGER NOT NULL DEFAULT 0,metadata_json TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL,updated_at TEXT NOT NULL,FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE);
CREATE TABLE audio_tracks(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,name TEXT NOT NULL,role TEXT NOT NULL,track_order INTEGER NOT NULL DEFAULT 0,gain_db REAL NOT NULL DEFAULT 0,pan REAL NOT NULL DEFAULT 0,muted INTEGER NOT NULL DEFAULT 0,solo INTEGER NOT NULL DEFAULT 0,enabled INTEGER NOT NULL DEFAULT 1,bus_id TEXT,metadata_json TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL,updated_at TEXT NOT NULL,FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,FOREIGN KEY(bus_id) REFERENCES audio_buses(id) ON DELETE SET NULL);
CREATE TABLE audio_mix_settings(project_id TEXT PRIMARY KEY,master_gain_db REAL NOT NULL DEFAULT 0,limiter_enabled INTEGER NOT NULL DEFAULT 1,limiter_limit REAL NOT NULL DEFAULT .95,normalization_enabled INTEGER NOT NULL DEFAULT 0,normalization_target_lufs REAL NOT NULL DEFAULT -16,preset TEXT NOT NULL DEFAULT 'custom',metadata_json TEXT NOT NULL DEFAULT '{}',updated_at TEXT NOT NULL,FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE);
CREATE TABLE asset_library_items(id TEXT PRIMARY KEY,name TEXT NOT NULL,managed INTEGER NOT NULL,path TEXT NOT NULL,rights_json TEXT NOT NULL DEFAULT '{}');
CREATE TABLE batches(id TEXT PRIMARY KEY,name TEXT NOT NULL,status TEXT NOT NULL,template_snapshot TEXT NOT NULL,settings_json TEXT NOT NULL DEFAULT '{}');
CREATE TABLE migration_history(id INTEGER PRIMARY KEY AUTOINCREMENT,scope TEXT NOT NULL,subject_id TEXT NOT NULL DEFAULT '',migration_id TEXT NOT NULL,from_version INTEGER NOT NULL,to_version INTEGER NOT NULL,status TEXT NOT NULL,record_counts_json TEXT NOT NULL DEFAULT '{}',warning_count INTEGER NOT NULL DEFAULT 0,backup_path TEXT NOT NULL DEFAULT '',started_at TEXT NOT NULL,completed_at TEXT NOT NULL DEFAULT '',app_version TEXT NOT NULL DEFAULT '');
"""

@dataclass
class FixtureProject:
    project_id:str; project_path:str; project_schema_version:int=1; version:int=1; language:str="en"

class FixtureRepository:
    def __init__(self,db_path:Path,project_id:str):self.db_path=db_path;self.project_id=project_id
    def get_by_id(self,project_id:str):
        if project_id!=self.project_id:return None
        c=sqlite3.connect(self.db_path);c.row_factory=sqlite3.Row
        try:r=c.execute('SELECT * FROM projects WHERE id=?',(project_id,)).fetchone()
        finally:c.close()
        return FixtureProject(str(r['id']),str(r['project_path']),int(r['project_schema_version']),int(r['version']),str(r['language'])) if r else None

class FixtureDatabase:
    def __init__(self,path:Path):self.path=path
    def connect(self):
        c=sqlite3.connect(self.path);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return _ConnectionContext(c)
    def backup_to(self,target:Path):
        target.parent.mkdir(parents=True,exist_ok=True);src=sqlite3.connect(self.path);dst=sqlite3.connect(target)
        try:src.backup(dst);dst.commit()
        finally:dst.close();src.close()
        return target

class _ConnectionContext:
    def __init__(self,c):self.c=c
    def __enter__(self):return self.c
    def __exit__(self,*args):self.c.close()


def make_legacy_fixture(root:Path,*,later:bool=False)->tuple[FixtureDatabase,FixtureRepository,Path,str]:
    root.mkdir(parents=True,exist_ok=True);project_id='later-project' if later else 'early-project';project_dir=root/project_id;project_dir.mkdir()
    for name in ('media','audio','subtitles','generated','thumbnails','renders','sources','cache'):(project_dir/name).mkdir()
    (project_dir/'media'/'source.mp4').write_bytes(b'legacy-media-fingerprint')
    language='vi-VN' if later else 'English';workflow='translate' if later else 'video'
    metadata={'version':1,'id':project_id,'title':'គម្រោង Legacy' if not later else 'Dự án ภาษาไทย','workflow':workflow,'language':language,'aspect_ratio':'16:9','fps':30,'created_at':NOW,'updated_at':NOW,'status':'draft','unknown_future_field':{'keep':True}}
    (project_dir/'project.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    db_path=root/'app.db';c=sqlite3.connect(db_path);c.executescript(SCHEMA)
    c.execute('INSERT INTO projects VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(project_id,metadata['title'],workflow,language,'16:9',30,NOW,NOW,None,None,'draft',str(project_dir),1,1))
    c.execute('INSERT INTO media_assets VALUES(?,?,?,?)',('media-1',project_id,str(project_dir/'media'/'source.mp4'),'{}'))
    c.execute('INSERT INTO scripts VALUES(?,?,?,?,?,?,?,?,?,?,?)',('script-1',project_id,'Script',language,'draft','normal',1,None,'{}',NOW,NOW))
    content='សួស្តី ព័ត៌មានសំខាន់' if not later else 'Xin chào — ภาษาไทย — green screen'
    c.execute('INSERT INTO script_sections VALUES(?,?,?,?,?,?,?,?,?,?,?)',('section-1','script-1',0,'body','Body',content,None,1,'{}',NOW,NOW))
    c.execute('INSERT INTO scenes VALUES(?,?,?,?)',('scene-1',project_id,'Scene','{}'))
    c.execute('INSERT INTO scene_layers VALUES(?,?,?,?)',('layer-1','scene-1','media-1',json.dumps({'chromaKey':{'enabled':later,'color':'#00ff00'}})))
    c.execute('INSERT INTO subtitle_tracks VALUES(?,?,?,?)',('sub-1',project_id,'Main',language))
    c.execute('INSERT INTO subtitle_cues VALUES(?,?,?,?,?)',('cue-1','sub-1',content,0,1500))
    c.execute('INSERT INTO timeline_clips VALUES(?,?,?,?,?)',('clip-1',project_id,'scene-1','media-1','{}'))
    c.execute('INSERT INTO asset_library_items VALUES(?,?,?,?,?)',('asset-1','Logo',1,'assets/logo.png',json.dumps({'rights':'owned'})))
    c.execute('INSERT INTO batches VALUES(?,?,?,?,?)',('batch-1','Legacy Batch','paused',json.dumps({'version':'1.0'}),json.dumps({'checkpoint':'translate'})))
    if later:
        c.execute('INSERT INTO speakers VALUES(?,?,?,?,?,?,?,?,?,?,?)',('speaker-1',project_id,'Reporter','speaker','voice-1','Thai','','','{}',NOW,NOW))
        c.execute('INSERT INTO speech_blocks VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',('speech-existing','section-1',0,'speaker-1',content,'vi-VN','','tts',0,180,'scene-1',0,'','{}',NOW,NOW))
        c.execute('INSERT INTO dubbing_projects VALUES(?,?,?,?)',(project_id,'English','Vietnamese','{}'))
        c.execute('INSERT INTO dub_mix_settings VALUES(?,?,?,?,?,?,?,?,?)',(project_id,'duck',.35,.9,.3,.12,120,'{}',NOW))
    c.commit();c.close()
    return FixtureDatabase(db_path),FixtureRepository(db_path,project_id),project_dir,project_id


def content_fingerprint(db_path:Path,project_id:str)->dict[str,object]:
    c=sqlite3.connect(db_path)
    try:
        ids={}
        for table in ('media_assets','scripts','script_sections','scenes','scene_layers','subtitle_tracks','subtitle_cues','timeline_clips'):
            ids[table]=[str(r[0]) for r in c.execute(f'SELECT id FROM {table} ORDER BY id')]
        texts=[str(r[0]) for r in c.execute('SELECT content FROM script_sections ORDER BY id')]+[str(r[0]) for r in c.execute('SELECT text FROM subtitle_cues ORDER BY id')]
        return {'ids':ids,'textHash':hashlib.sha256('\n'.join(texts).encode()).hexdigest(),'mediaHash':hashlib.sha256((Path(c.execute('SELECT file_path FROM media_assets WHERE project_id=?',(project_id,)).fetchone()[0])).read_bytes()).hexdigest()}
    finally:c.close()
