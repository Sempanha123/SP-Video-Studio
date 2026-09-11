from __future__ import annotations
import json
from domain.batch_item import BatchItem
from domain.batch_stage import BatchStageState,BatchStageStatus,STAGE_INDEX
from domain.project import utc_now_iso
from storage.database import SQLiteDatabase

def _dump(v):return json.dumps(v,ensure_ascii=False,separators=(",",":"),sort_keys=True)

class BatchItemRepository:
    def __init__(self,database:SQLiteDatabase):self.database=database
    def create_many(self,items:list[BatchItem])->None:
        for item in items:item.validate()
        with self.database.connect() as c,c:
            c.executemany("""INSERT INTO batch_items(id,batch_id,row_index,item_key,status,current_stage,progress,project_id,variant_key,output_path,error_code,error_message,attempt_count,created_at,updated_at,started_at,completed_at,input_data_json,resolved_data_json,metadata_json,fingerprint) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",[self._values(x) for x in items])
    def save(self,item:BatchItem)->BatchItem:
        item.validate();item.updated_at=utc_now_iso();v=self._values(item)
        with self.database.connect() as c,c:
            cur=c.execute("""UPDATE batch_items SET batch_id=?,row_index=?,item_key=?,status=?,current_stage=?,progress=?,project_id=?,variant_key=?,output_path=?,error_code=?,error_message=?,attempt_count=?,created_at=?,updated_at=?,started_at=?,completed_at=?,input_data_json=?,resolved_data_json=?,metadata_json=?,fingerprint=? WHERE id=?""",v[1:]+(item.id,))
            if not cur.rowcount:raise KeyError("Batch item not found.")
        return item
    def get(self,item_id:str)->BatchItem|None:
        with self.database.connect() as c:r=c.execute("SELECT * FROM batch_items WHERE id=?",(item_id,)).fetchone()
        return BatchItem.from_record(r) if r else None
    def get_by_key(self,batch_id:str,key:str)->BatchItem|None:
        with self.database.connect() as c:r=c.execute("SELECT * FROM batch_items WHERE batch_id=? AND item_key=?",(batch_id,key)).fetchone()
        return BatchItem.from_record(r) if r else None
    def list_for_batch(self,batch_id:str,*,status:str="all",search:str="",limit:int=0,offset:int=0)->list[BatchItem]:
        clauses=["batch_id=?"];params:list[object]=[batch_id]
        if status and status!="all":clauses.append("status=?");params.append(status)
        if search.strip():
            clauses.append("(LOWER(item_key) LIKE ? OR LOWER(output_path) LIKE ? OR LOWER(COALESCE(json_extract(resolved_data_json,'$.title'),'')) LIKE ?)");needle=f"%{search.casefold().replace('%','')}%";params.extend([needle,needle,needle])
        sql=f"SELECT * FROM batch_items WHERE {' AND '.join(clauses)} ORDER BY row_index,item_key"
        if limit>0:sql+=" LIMIT ? OFFSET ?";params.extend([int(limit),int(offset)])
        with self.database.connect() as c:rows=c.execute(sql,tuple(params)).fetchall()
        return [BatchItem.from_record(r) for r in rows]
    def count(self,batch_id:str,status:str="")->int:
        sql="SELECT COUNT(*) n FROM batch_items WHERE batch_id=?";params:list[object]=[batch_id]
        if status:sql+=" AND status=?";params.append(status)
        with self.database.connect() as c:r=c.execute(sql,tuple(params)).fetchone()
        return int(r["n"])
    def delete_for_batch(self,batch_id:str)->None:
        with self.database.connect() as c,c:c.execute("DELETE FROM batch_items WHERE batch_id=?",(batch_id,))
    def checkpoint(self,item:BatchItem,state:BatchStageState)->None:
        item.validate();state.validate();item.updated_at=utc_now_iso()
        v=self._values(item)
        with self.database.connect() as c,c:
            cur=c.execute("""UPDATE batch_items SET batch_id=?,row_index=?,item_key=?,status=?,current_stage=?,progress=?,project_id=?,variant_key=?,output_path=?,error_code=?,error_message=?,attempt_count=?,created_at=?,updated_at=?,started_at=?,completed_at=?,input_data_json=?,resolved_data_json=?,metadata_json=?,fingerprint=? WHERE id=?""",v[1:]+(item.id,))
            if not cur.rowcount:raise KeyError("Batch item not found.")
            c.execute("""INSERT INTO batch_stage_state(item_id,stage,status,progress,started_at,completed_at,fingerprint,error_code,error_message,output_reference,attempt_count,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(item_id,stage) DO UPDATE SET status=excluded.status,progress=excluded.progress,started_at=excluded.started_at,completed_at=excluded.completed_at,fingerprint=excluded.fingerprint,error_code=excluded.error_code,error_message=excluded.error_message,output_reference=excluded.output_reference,attempt_count=excluded.attempt_count,metadata_json=excluded.metadata_json""",self._stage_values(state))
    def stage_state(self,item_id:str,stage:str)->BatchStageState|None:
        with self.database.connect() as c:r=c.execute("SELECT * FROM batch_stage_state WHERE item_id=? AND stage=?",(item_id,stage)).fetchone()
        return BatchStageState.from_record(r) if r else None
    def stage_states(self,item_id:str)->list[BatchStageState]:
        with self.database.connect() as c:rows=c.execute("SELECT * FROM batch_stage_state WHERE item_id=?",(item_id,)).fetchall()
        result=[BatchStageState.from_record(r) for r in rows];result.sort(key=lambda x:STAGE_INDEX.get(x.stage_code,999));return result
    def invalidate_from(self,item_id:str,stage:str)->int:
        start=STAGE_INDEX[stage];targets=[s for s,i in STAGE_INDEX.items() if i>=start]
        marks=",".join("?" for _ in targets)
        with self.database.connect() as c,c:
            cur=c.execute(f"UPDATE batch_stage_state SET status=?,progress=0,completed_at='',error_code='',error_message='',output_reference='' WHERE item_id=? AND stage IN ({marks})",(BatchStageStatus.INVALIDATED.value,item_id,*targets))
            c.execute("UPDATE batch_items SET current_stage=?,status='pending',progress=0,error_code='',error_message='',completed_at='',updated_at=? WHERE id=?",(stage,utc_now_iso(),item_id));return int(cur.rowcount)
    def mark_running_interrupted(self,batch_id:str|None=None)->int:
        params:list[object]=[];where="status IN ('validating','project_setup','translation','tts','subtitles','scene_setup','rendering','exporting')"
        if batch_id:where+=" AND batch_id=?";params.append(batch_id)
        with self.database.connect() as c,c:
            rows=c.execute(f"SELECT id,current_stage FROM batch_items WHERE {where}",tuple(params)).fetchall()
            for r in rows:
                c.execute("UPDATE batch_items SET status='interrupted',error_code='interrupted',error_message='The application closed while this stage was running.',updated_at=? WHERE id=?",(utc_now_iso(),r["id"]))
                c.execute("UPDATE batch_stage_state SET status='interrupted',error_code='interrupted',error_message='Stage interrupted by application shutdown.' WHERE item_id=? AND stage=? AND status='running'",(r["id"],r["current_stage"]))
            return len(rows)
    @staticmethod
    def _values(x:BatchItem):
        return (x.id,x.batch_id,x.row_index,x.item_key,x.status_code,x.stage_code,float(x.progress),x.project_id,x.variant_key,x.output_path,x.error_code,x.error_message,int(x.attempt_count),x.created_at,x.updated_at,x.started_at,x.completed_at,_dump(x.input_data),_dump(x.resolved_data),_dump(x.metadata),x.fingerprint)
    @staticmethod
    def _stage_values(x:BatchStageState):
        return (x.item_id,x.stage_code,x.status_code,float(x.progress),x.started_at,x.completed_at,x.fingerprint,x.error_code,x.error_message,x.output_reference,int(x.attempt_count),_dump(x.metadata))
