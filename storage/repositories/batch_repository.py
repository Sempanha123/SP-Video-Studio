from __future__ import annotations
import json
from datetime import datetime,timezone
from domain.batch import Batch
from domain.batch_mapping import BatchMapping
from domain.batch_variant import BatchVariantConfig
from domain.project import utc_now_iso
from storage.database import SQLiteDatabase


def _dump(v):return json.dumps(v,ensure_ascii=False,separators=(",",":"),sort_keys=True)
def _load(v,fallback):
    try:return json.loads(str(v or ""))
    except Exception:return fallback


class BatchRepository:
    def __init__(self,database:SQLiteDatabase):self.database=database
    def create(self,b:Batch)->Batch:
        b.validate()
        with self.database.connect() as c,c:
            c.execute("""INSERT INTO batches(id,name,template_id,status,created_at,updated_at,started_at,completed_at,input_source_type,input_source_path,settings_json,output_directory,total_items,completed_items,failed_items,cancelled_items,template_snapshot_json,input_snapshot_json,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",self._values(b))
        return b
    def create_definition(self,b:Batch,mappings:list[BatchMapping],config:BatchVariantConfig)->Batch:
        """Persist Batch + mappings + variant atomically before any execution work starts."""
        b.validate()
        for mapping in mappings:mapping.validate()
        now=utc_now_iso();payload=_dump(config.to_dict())
        with self.database.connect() as c,c:
            c.execute("""INSERT INTO batches(id,name,template_id,status,created_at,updated_at,started_at,completed_at,input_source_type,input_source_path,settings_json,output_directory,total_items,completed_items,failed_items,cancelled_items,template_snapshot_json,input_snapshot_json,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",self._values(b))
            for m in mappings:
                c.execute("INSERT INTO batch_mappings(id,batch_id,target,kind,source,value_json,required,default_json,transforms_json,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?)",(m.id,b.id,m.target,m.kind_code,m.source,_dump(m.value),int(m.required),_dump(m.default_value),_dump(m.transforms),_dump(m.metadata)))
            c.execute("INSERT INTO batch_variants(id,batch_id,config_json,created_at,updated_at) VALUES(?,?,?,?,?)",(config.id,b.id,payload,now,now))
        return b
    def save(self,b:Batch)->Batch:
        b.validate();b.updated_at=utc_now_iso()
        v=self._values(b)
        with self.database.connect() as c,c:
            cur=c.execute("""UPDATE batches SET name=?,template_id=?,status=?,created_at=?,updated_at=?,started_at=?,completed_at=?,input_source_type=?,input_source_path=?,settings_json=?,output_directory=?,total_items=?,completed_items=?,failed_items=?,cancelled_items=?,template_snapshot_json=?,input_snapshot_json=?,metadata_json=? WHERE id=?""",v[1:]+(b.id,))
            if not cur.rowcount:raise KeyError("Batch not found.")
        return b
    def get(self,batch_id:str)->Batch|None:
        with self.database.connect() as c:r=c.execute("SELECT * FROM batches WHERE id=?",(batch_id,)).fetchone()
        return Batch.from_record(r) if r else None
    def list_all(self)->list[Batch]:
        with self.database.connect() as c:rows=c.execute("SELECT * FROM batches ORDER BY updated_at DESC,name COLLATE NOCASE").fetchall()
        return [Batch.from_record(r) for r in rows]
    def delete(self,batch_id:str)->None:
        with self.database.connect() as c,c:
            cur=c.execute("DELETE FROM batches WHERE id=?",(batch_id,))
            if not cur.rowcount:raise KeyError("Batch not found.")
    def save_mappings(self,batch_id:str,mappings:list[BatchMapping])->None:
        for m in mappings:m.validate()
        with self.database.connect() as c,c:
            c.execute("DELETE FROM batch_mappings WHERE batch_id=?",(batch_id,))
            for m in mappings:
                c.execute("INSERT INTO batch_mappings(id,batch_id,target,kind,source,value_json,required,default_json,transforms_json,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?)",(m.id,batch_id,m.target,m.kind_code,m.source,_dump(m.value),int(m.required),_dump(m.default_value),_dump(m.transforms),_dump(m.metadata)))
    def mappings(self,batch_id:str)->list[BatchMapping]:
        with self.database.connect() as c:rows=c.execute("SELECT * FROM batch_mappings WHERE batch_id=? ORDER BY target COLLATE NOCASE",(batch_id,)).fetchall()
        return [BatchMapping(batch_id=str(r["batch_id"]),mapping_id=str(r["id"]),target=str(r["target"]),kind=str(r["kind"]),source=str(r["source"]),value=_load(r["value_json"],""),required=bool(r["required"]),default_value=_load(r["default_json"],""),transforms=_load(r["transforms_json"],[]),metadata=_load(r["metadata_json"],{})) for r in rows]
    def save_variant(self,config:BatchVariantConfig)->BatchVariantConfig:
        now=utc_now_iso();payload=_dump(config.to_dict())
        with self.database.connect() as c,c:c.execute("""INSERT INTO batch_variants(id,batch_id,config_json,created_at,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(batch_id) DO UPDATE SET id=excluded.id,config_json=excluded.config_json,updated_at=excluded.updated_at""",(config.id,config.batch_id,payload,now,now))
        return config
    def variant(self,batch_id:str)->BatchVariantConfig|None:
        with self.database.connect() as c:r=c.execute("SELECT * FROM batch_variants WHERE batch_id=?",(batch_id,)).fetchone()
        if not r:return None
        raw=_load(r["config_json"],{})
        return BatchVariantConfig(batch_id=batch_id,variant_id=str(raw.get("id") or r["id"]),languages=list(raw.get("languages") or []),voices=list(raw.get("voices") or []),platforms=list(raw.get("platforms") or []),aspect_ratios=list(raw.get("aspectRatios") or []),template_options=list(raw.get("templateOptions") or []),source_language=str(raw.get("sourceLanguage") or ""),seed=int(raw.get("seed") or 0),metadata=dict(raw.get("metadata") or {}))
    def acquire_lock(self,batch_id:str,owner:str)->bool:
        with self.database.connect() as c,c:
            r=c.execute("SELECT scheduler_owner FROM batches WHERE id=?",(batch_id,)).fetchone()
            if not r:raise KeyError("Batch not found.")
            current=str(r["scheduler_owner"] or "")
            if current and current!=owner:return False
            c.execute("UPDATE batches SET scheduler_owner=?,scheduler_heartbeat_at=? WHERE id=?",(owner,utc_now_iso(),batch_id));return True
    def heartbeat(self,batch_id:str,owner:str)->bool:
        with self.database.connect() as c,c:
            cur=c.execute("UPDATE batches SET scheduler_heartbeat_at=? WHERE id=? AND scheduler_owner=?",(utc_now_iso(),batch_id,owner));return bool(cur.rowcount)
    def release_lock(self,batch_id:str,owner:str)->None:
        with self.database.connect() as c,c:c.execute("UPDATE batches SET scheduler_owner='',scheduler_heartbeat_at='' WHERE id=? AND scheduler_owner=?",(batch_id,owner))
    def clear_stale_locks(self)->int:
        # On application startup no in-process scheduler survives, so old ownership is stale by definition.
        with self.database.connect() as c,c:
            cur=c.execute("UPDATE batches SET scheduler_owner='',scheduler_heartbeat_at='' WHERE scheduler_owner<>''")
            return int(cur.rowcount)
    def set_pause_reason(self,batch_id:str,reason:str)->None:
        with self.database.connect() as c,c:c.execute("UPDATE batches SET pause_reason=?,updated_at=? WHERE id=?",(reason,utc_now_iso(),batch_id))
    def pause_reason(self,batch_id:str)->str:
        with self.database.connect() as c:r=c.execute("SELECT pause_reason FROM batches WHERE id=?",(batch_id,)).fetchone()
        return str(r["pause_reason"] or "") if r else ""
    @staticmethod
    def _values(b:Batch):
        return (b.id,b.name,b.template_id,b.status_code,b.created_at,b.updated_at,b.started_at,b.completed_at,b.input_source_type,b.input_source_path,_dump(b.settings),b.output_directory,b.total_items,b.completed_items,b.failed_items,b.cancelled_items,_dump(b.template_snapshot),_dump(b.input_snapshot),_dump(b.metadata))
