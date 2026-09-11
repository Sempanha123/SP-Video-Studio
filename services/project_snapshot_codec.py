from __future__ import annotations
import base64, hashlib, os
from pathlib import Path
from typing import Any
from storage.atomic_write import atomic_write_json
from domain.recovery_errors import RecoveryRestoreFailed

GLOBAL_EXACT={
 'schema_migrations','autosave_state','recovery_sessions','recovery_snapshots','interrupted_jobs',
 'templates','template_usage','template_assets','assets','asset_collections','asset_collection_items','asset_tags','asset_tag_items','asset_licenses','asset_library_settings',
 'batches','batch_items','batch_mappings','batch_variants','batch_stage_state','model_installations'
}
GLOBAL_PREFIXES=('sqlite_','recovery_','batch_','asset_','template_')

def _pack(v):
    if isinstance(v,(bytes,bytearray,memoryview)): return {'__bytes__':base64.b64encode(bytes(v)).decode('ascii')}
    return v

def _unpack(v):
    if isinstance(v,dict) and set(v)=={'__bytes__'}: return base64.b64decode(v['__bytes__'])
    return v

class ProjectSnapshotCodec:
    """Capture/restore structured project rows without copying source media."""
    def __init__(self,database,logger=None): self.database=database; self.logger=logger
    def capture(self,project_id:str)->dict[str,Any]:
        with self.database.connect() as c:
            tables=self._tables(c); rows=self._capture_rows(c,project_id,tables); schema=int(c.execute('PRAGMA user_version').fetchone()[0] or 0)
        project_row=(rows.get('projects') or [{}])[0]
        project_path=str(project_row.get('project_path') or project_row.get('path') or '')
        project_json=None
        if project_path:
            pj=Path(project_path)/'project.json'
            if pj.is_file():
                try:
                    import json; project_json=json.loads(pj.read_text(encoding='utf-8'))
                except Exception: project_json=None
        return {'schemaVersion':schema,'tables':rows,'projectJson':project_json,'mediaReferences':self._media_refs(rows.get('media_assets',[]))}
    def restore(self,project_id:str,payload:dict[str,Any])->dict[str,int]:
        snapshot_tables=payload.get('tables') or {}
        if not isinstance(snapshot_tables,dict) or 'projects' not in snapshot_tables: raise RecoveryRestoreFailed('Recovery snapshot is missing project state.')
        with self.database.connect() as c:
            current=self._capture_rows(c,project_id,self._tables(c))
            if not current.get('projects'): raise RecoveryRestoreFailed('The saved project no longer exists. Use Restore as New Project instead.')
            order=self._topological(c,set(current)|set(snapshot_tables))
            c.execute('BEGIN IMMEDIATE')
            try:
                c.execute('PRAGMA defer_foreign_keys=ON')
                for table in reversed(order):
                    if table=='projects': continue
                    rows=current.get(table,[])
                    self._delete_exact(c,table,rows)
                for table in order:
                    rows=snapshot_tables.get(table,[])
                    if table=='projects':
                        if rows:self._update_project(c,project_id,rows[0])
                        continue
                    for row in rows:self._insert(c,table,row)
                c.commit()
            except Exception as exc:
                c.rollback(); raise RecoveryRestoreFailed('Recovery could not be applied safely.') from exc
        self._restore_project_json(snapshot_tables,payload.get('projectJson'))
        return {table:len(rows) for table,rows in snapshot_tables.items()}
    def compare(self,project_id:str,payload:dict[str,Any])->dict[str,Any]:
        current=self.capture(project_id); before=current.get('tables',{}); after=payload.get('tables',{})
        categories={
            'Script':('scripts','script_sections'),'Scenes':('scenes','scene_overlays','scene_layers'),'Timeline':('timeline_tracks','timeline_items','manual_audio_clips'),
            'Subtitles':('subtitle_tracks','subtitle_cues'),'Translation':('translations','translation_segments'),'Speakers':('speakers','speech_blocks'),
            'News':('news_projects','news_sources','news_claims','news_briefs'),'Story':('story_projects','story_beats'),'Shorts':('shorts_projects','short_candidates','short_segments')}
        result={}
        for label,tables in categories.items():
            old=sum(len(before.get(t,[])) for t in tables); new=sum(len(after.get(t,[])) for t in tables)
            changed=any(before.get(t,[])!=after.get(t,[]) for t in tables)
            result[label]={'changed':changed,'savedCount':old,'recoveredCount':new,'delta':new-old}
        return result
    def media_warnings(self,payload:dict[str,Any])->list[dict[str,Any]]:
        warnings=[]
        for item in payload.get('mediaReferences') or []:
            p=Path(str(item.get('path') or ''))
            if not p.is_file(): warnings.append({**item,'status':'missing'}); continue
            fp=self._quick_fingerprint(p)
            if item.get('fingerprint') and fp!=item.get('fingerprint'): warnings.append({**item,'status':'changed'})
        return warnings
    def _capture_rows(self,c,project_id,tables):
        captured={}
        if 'projects' in tables:
            r=c.execute('SELECT * FROM projects WHERE id=?',(project_id,)).fetchone()
            if r: captured['projects']=[self._row(r)]
        for table in tables:
            if table=='projects' or self._excluded(table): continue
            cols=self._columns(c,table)
            if 'project_id' in cols:
                rs=c.execute(f'SELECT * FROM "{table}" WHERE project_id=?',(project_id,)).fetchall()
                if rs:captured[table]=[self._row(r) for r in rs]
        changed=True
        while changed:
            changed=False
            for table in tables:
                if table in captured or self._excluded(table): continue
                for fk in c.execute(f'PRAGMA foreign_key_list("{table}")').fetchall():
                    parent=str(fk[2]); child_col=str(fk[3]); parent_col=str(fk[4] or 'id')
                    parent_rows=captured.get(parent,[])
                    values=[r.get(parent_col) for r in parent_rows if r.get(parent_col) is not None]
                    if not values: continue
                    qs=','.join('?' for _ in values)
                    rs=c.execute(f'SELECT * FROM "{table}" WHERE "{child_col}" IN ({qs})',values).fetchall()
                    if rs: captured[table]=[self._row(r) for r in rs]; changed=True; break
        return captured
    @staticmethod
    def _excluded(table): return table in GLOBAL_EXACT or any(table.startswith(x) for x in GLOBAL_PREFIXES)
    @staticmethod
    def _row(r): return {k:_pack(r[k]) for k in r.keys()}
    @staticmethod
    def _tables(c): return [str(r[0]) for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()]
    @staticmethod
    def _columns(c,table): return {str(r[1]) for r in c.execute(f'PRAGMA table_info("{table}")').fetchall()}
    def _pk(self,c,table):
        rows=c.execute(f'PRAGMA table_info("{table}")').fetchall(); pks=[(int(r[5]),str(r[1])) for r in rows if int(r[5])>0]
        return [name for _,name in sorted(pks)] or (['id'] if any(str(r[1])=='id' for r in rows) else [])
    def _delete_exact(self,c,table,rows):
        if not rows:return
        pk=self._pk(c,table)
        if pk:
            for row in rows:
                vals=[_unpack(row.get(k)) for k in pk]
                if all(v is not None for v in vals): c.execute(f'DELETE FROM "{table}" WHERE '+ ' AND '.join(f'"{k}"=?' for k in pk),vals)
        elif 'project_id' in self._columns(c,table):
            ids={row.get('project_id') for row in rows}
            for pid in ids:c.execute(f'DELETE FROM "{table}" WHERE project_id=?',(pid,))
    @staticmethod
    def _insert(c,table,row):
        cols=list(row);vals=[_unpack(row[k]) for k in cols];q=','.join('?' for _ in cols);names=','.join(f'"{x}"' for x in cols)
        c.execute(f'INSERT OR REPLACE INTO "{table}" ({names}) VALUES ({q})',vals)
    @staticmethod
    def _update_project(c,project_id,row):
        cols=[k for k in row if k!='id']
        if cols:c.execute('UPDATE projects SET '+','.join(f'"{k}"=?' for k in cols)+' WHERE id=?',[_unpack(row[k]) for k in cols]+[project_id])
    def _topological(self,c,tables):
        deps={t:set() for t in tables}
        for t in tables:
            try:
                for fk in c.execute(f'PRAGMA foreign_key_list("{t}")').fetchall():
                    p=str(fk[2])
                    if p in tables and p!=t: deps[t].add(p)
            except Exception:pass
        out=[];remaining=set(tables)
        while remaining:
            ready=sorted(t for t in remaining if not (deps[t]&remaining))
            if not ready: ready=[sorted(remaining)[0]]
            for t in ready: out.append(t);remaining.remove(t)
        return out
    def _restore_project_json(self,tables,value):
        if not isinstance(value,dict):return
        rows=tables.get('projects') or []
        if not rows:return
        root=str(rows[0].get('project_path') or rows[0].get('path') or '')
        if root: atomic_write_json(Path(root)/'project.json',value)
    def _media_refs(self,rows):
        out=[]
        for r in rows:
            path=str(r.get('project_path') or r.get('path') or '')
            if not path:continue
            p=Path(path);out.append({'id':str(r.get('id') or r.get('asset_id') or ''),'path':path,'fingerprint':self._quick_fingerprint(p) if p.is_file() else '','size':p.stat().st_size if p.is_file() else 0})
        return out
    @staticmethod
    def _quick_fingerprint(path:Path)->str:
        try:
            st=path.stat();h=hashlib.sha256();h.update(f'{st.st_size}:{int(st.st_mtime_ns)}'.encode())
            with path.open('rb') as f:
                h.update(f.read(65536))
                if st.st_size>65536:f.seek(max(0,st.st_size-65536));h.update(f.read(65536))
            return h.hexdigest()
        except OSError:return ''
