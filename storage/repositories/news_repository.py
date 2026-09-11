from __future__ import annotations

import json
from collections.abc import Iterable
from uuid import uuid4

from domain.news_brief import NewsBrief, NewsBriefItem
from domain.news_claim import NewsClaim, NewsEvidence
from domain.news_project import NewsProjectMetadata
from domain.news_script_mapping import NewsScriptMapping
from domain.news_source import NewsSource, NewsSourceSnapshot
from domain.project import utc_now_iso
from storage.database import SQLiteDatabase


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


class NewsRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    # Project metadata -------------------------------------------------
    def upsert_project(self, item: NewsProjectMetadata) -> NewsProjectMetadata:
        item.validate(); item.updated_at = utc_now_iso()
        with self.database.connect() as c, c:
            c.execute(
                """INSERT INTO news_projects(project_id,topic,angle,region,language,target_audience,target_duration_ms,platform,status,source_fingerprint,metadata_json,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(project_id) DO UPDATE SET topic=excluded.topic,angle=excluded.angle,region=excluded.region,language=excluded.language,
                target_audience=excluded.target_audience,target_duration_ms=excluded.target_duration_ms,platform=excluded.platform,status=excluded.status,
                source_fingerprint=excluded.source_fingerprint,metadata_json=excluded.metadata_json,updated_at=excluded.updated_at""",
                (item.project_id,item.topic,item.angle,item.region,item.language,item.target_audience,item.target_duration_ms,item.platform,item.status_code,item.source_fingerprint,_json(item.metadata),item.created_at,item.updated_at),
            )
        return item

    def get_project(self, project_id: str) -> NewsProjectMetadata | None:
        with self.database.connect() as c:
            row=c.execute("SELECT * FROM news_projects WHERE project_id=?",(project_id,)).fetchone()
        return NewsProjectMetadata.from_record(row) if row else None

    # Sources / snapshots ---------------------------------------------
    def create_source(self, source: NewsSource) -> NewsSource:
        source.validate()
        with self.database.connect() as c, c:
            self._insert_source(c, source)
        return source

    def update_source(self, source: NewsSource) -> NewsSource:
        source.validate(); source.updated_at=utc_now_iso()
        with self.database.connect() as c, c:
            cur=c.execute("""UPDATE news_sources SET title=?,url=?,publisher=?,author=?,published_at=?,accessed_at=?,language=?,status=?,source_path=?,category=?,notes=?,latest_snapshot_id=?,source_updated=?,metadata_json=?,updated_at=? WHERE id=? AND project_id=?""",
                          (source.title,source.url,source.publisher,source.author,source.published_at,source.accessed_at,source.language,source.status_code,source.source_path,source.category,source.notes,source.latest_snapshot_id,int(source.source_updated),_json(source.metadata),source.updated_at,source.source_id,source.project_id))
            if cur.rowcount==0: raise KeyError("News source ownership mismatch.")
        return source

    def source(self, project_id:str, source_id:str)->NewsSource|None:
        with self.database.connect() as c:
            row=c.execute("SELECT * FROM news_sources WHERE id=? AND project_id=?",(source_id,project_id)).fetchone()
        return NewsSource.from_record(row) if row else None

    def list_sources(self, project_id:str, *, include_removed:bool=False)->list[NewsSource]:
        sql="SELECT * FROM news_sources WHERE project_id=?" + ("" if include_removed else " AND status<>'removed'") + " ORDER BY created_at ASC"
        with self.database.connect() as c: rows=c.execute(sql,(project_id,)).fetchall()
        return [NewsSource.from_record(r) for r in rows]

    def create_snapshot(self, snapshot:NewsSourceSnapshot, source:NewsSource)->NewsSourceSnapshot:
        with self.database.connect() as c, c:
            c.execute("""INSERT INTO news_source_snapshots(id,source_id,retrieved_at,content_text,content_hash,title,author,published_at,metadata_json) VALUES(?,?,?,?,?,?,?,?,?)""",
                      (snapshot.snapshot_id,snapshot.source_id,snapshot.retrieved_at,snapshot.content_text,snapshot.content_hash,snapshot.title,snapshot.author,snapshot.published_at,_json(snapshot.metadata)))
            source.latest_snapshot_id=snapshot.snapshot_id; source.updated_at=utc_now_iso()
            c.execute("UPDATE news_sources SET latest_snapshot_id=?,source_updated=?,title=?,author=?,published_at=?,accessed_at=?,status=?,metadata_json=?,updated_at=? WHERE id=? AND project_id=?",
                      (source.latest_snapshot_id,int(source.source_updated),source.title,source.author,source.published_at,source.accessed_at,source.status_code,_json(source.metadata),source.updated_at,source.source_id,source.project_id))
        return snapshot

    def snapshot(self, snapshot_id:str)->NewsSourceSnapshot|None:
        with self.database.connect() as c: row=c.execute("SELECT * FROM news_source_snapshots WHERE id=?",(snapshot_id,)).fetchone()
        return NewsSourceSnapshot.from_record(row) if row else None

    def snapshots(self, source_id:str)->list[NewsSourceSnapshot]:
        with self.database.connect() as c: rows=c.execute("SELECT * FROM news_source_snapshots WHERE source_id=? ORDER BY retrieved_at ASC",(source_id,)).fetchall()
        return [NewsSourceSnapshot.from_record(r) for r in rows]

    def latest_snapshot(self, project_id:str,source_id:str)->NewsSourceSnapshot|None:
        src=self.source(project_id,source_id)
        return self.snapshot(src.latest_snapshot_id) if src and src.latest_snapshot_id else None

    def mark_source_removed(self, project_id:str,source_id:str)->None:
        with self.database.connect() as c, c:
            c.execute("UPDATE news_sources SET status='removed',updated_at=? WHERE id=? AND project_id=?",(utc_now_iso(),source_id,project_id))
            claim_rows=c.execute("SELECT DISTINCT claim_id FROM news_evidence WHERE source_id=?",(source_id,)).fetchall()
            for row in claim_rows:
                claim_id=str(row["claim_id"])
                remaining=c.execute("""SELECT COUNT(*) AS n FROM news_evidence e JOIN news_sources s ON s.id=e.source_id WHERE e.claim_id=? AND s.status<>'removed'""",(claim_id,)).fetchone()["n"]
                if int(remaining or 0)==0:
                    c.execute("UPDATE news_claims SET status='unsupported',updated_at=? WHERE id=? AND project_id=? AND status<>'rejected'",(utc_now_iso(),claim_id,project_id))
            c.execute("UPDATE news_briefs SET status='outdated',updated_at=? WHERE project_id=? AND status<>'draft'",(utc_now_iso(),project_id))
            c.execute("UPDATE news_script_mappings SET status='needs_review',updated_at=? WHERE project_id=? AND mapping_type='factual'",(utc_now_iso(),project_id))

    # Claims / evidence ------------------------------------------------
    def create_claim(self, claim:NewsClaim)->NewsClaim:
        claim.validate()
        with self.database.connect() as c,c: self._insert_claim(c,claim)
        return claim

    def update_claim(self, claim:NewsClaim)->NewsClaim:
        claim.validate(); claim.updated_at=utc_now_iso()
        with self.database.connect() as c,c:
            cur=c.execute("""UPDATE news_claims SET text=?,claim_type=?,status=?,importance=?,uncertainty=?,user_modified=?,locked=?,notes=?,quote_text=?,speaker=?,quote_kind=?,original_quote=?,metadata_json=?,updated_at=? WHERE id=? AND project_id=?""",
                          (claim.text,claim.claim_type,claim.status_code,claim.importance,claim.uncertainty,int(claim.user_modified),int(claim.locked),claim.notes,claim.quote_text,claim.speaker,claim.quote_kind,claim.original_quote,_json(claim.metadata),claim.updated_at,claim.claim_id,claim.project_id))
            if cur.rowcount==0: raise KeyError("Claim ownership mismatch.")
        return claim

    def claim(self, project_id:str,claim_id:str)->NewsClaim|None:
        with self.database.connect() as c: row=c.execute("SELECT * FROM news_claims WHERE id=? AND project_id=?",(claim_id,project_id)).fetchone()
        return NewsClaim.from_record(row) if row else None

    def list_claims(self, project_id:str)->list[NewsClaim]:
        with self.database.connect() as c: rows=c.execute("SELECT * FROM news_claims WHERE project_id=? ORDER BY created_at ASC",(project_id,)).fetchall()
        return [NewsClaim.from_record(r) for r in rows]

    def create_evidence(self,e:NewsEvidence)->NewsEvidence:
        with self.database.connect() as c,c:
            c.execute("""INSERT INTO news_evidence(id,claim_id,source_id,snapshot_id,evidence_text,source_start_offset,source_end_offset,evidence_type,metadata_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                      (e.evidence_id,e.claim_id,e.source_id,e.snapshot_id,e.evidence_text,e.source_start_offset,e.source_end_offset,e.evidence_type,_json(e.metadata),e.created_at))
        return e

    def evidence_for_claim(self,claim_id:str)->list[NewsEvidence]:
        with self.database.connect() as c: rows=c.execute("SELECT * FROM news_evidence WHERE claim_id=? ORDER BY created_at ASC",(claim_id,)).fetchall()
        return [NewsEvidence.from_record(r) for r in rows]

    def evidence_for_source(self,source_id:str)->list[NewsEvidence]:
        with self.database.connect() as c: rows=c.execute("SELECT * FROM news_evidence WHERE source_id=? ORDER BY created_at ASC",(source_id,)).fetchall()
        return [NewsEvidence.from_record(r) for r in rows]

    def merge_claims(self,project_id:str,target_id:str,source_id:str)->NewsClaim:
        with self.database.connect() as c,c:
            target=c.execute("SELECT * FROM news_claims WHERE id=? AND project_id=?",(target_id,project_id)).fetchone()
            source=c.execute("SELECT * FROM news_claims WHERE id=? AND project_id=?",(source_id,project_id)).fetchone()
            if not target or not source: raise KeyError("Claim not found.")
            c.execute("UPDATE news_evidence SET claim_id=? WHERE claim_id=?",(target_id,source_id))
            rows=c.execute("SELECT id,claim_ids_json FROM news_script_mappings WHERE project_id=?",(project_id,)).fetchall()
            for row in rows:
                ids=json.loads(str(row["claim_ids_json"] or "[]")); changed=False
                ids2=[]
                for cid in ids:
                    new=target_id if cid==source_id else cid
                    if new not in ids2: ids2.append(new)
                    changed |= new!=cid
                if changed: c.execute("UPDATE news_script_mappings SET claim_ids_json=?,updated_at=? WHERE id=?",(_json(ids2),utc_now_iso(),row["id"]))
            md=json.loads(str(source["metadata_json"] or "{}")); md["merged_into"]=target_id
            c.execute("UPDATE news_claims SET status='rejected',metadata_json=?,updated_at=? WHERE id=?",(_json(md),utc_now_iso(),source_id))
        result=self.claim(project_id,target_id)
        assert result is not None
        return result

    # Briefs -----------------------------------------------------------
    def create_brief(self,brief:NewsBrief,items:Iterable[NewsBriefItem])->NewsBrief:
        brief.validate(); values=list(items)
        with self.database.connect() as c,c:
            c.execute("""INSERT INTO news_briefs(id,project_id,title,summary,status,source_fingerprint,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)""",
                      (brief.brief_id,brief.project_id,brief.title,brief.summary,brief.status,brief.source_fingerprint,_json(brief.metadata),brief.created_at,brief.updated_at))
            for item in values:self._insert_brief_item(c,item)
        return brief

    def update_brief(self,brief:NewsBrief)->NewsBrief:
        brief.validate(); brief.updated_at=utc_now_iso()
        with self.database.connect() as c,c:
            c.execute("UPDATE news_briefs SET title=?,summary=?,status=?,source_fingerprint=?,metadata_json=?,updated_at=? WHERE id=? AND project_id=?",
                      (brief.title,brief.summary,brief.status,brief.source_fingerprint,_json(brief.metadata),brief.updated_at,brief.brief_id,brief.project_id))
        return brief

    def list_briefs(self,project_id:str)->list[NewsBrief]:
        with self.database.connect() as c: rows=c.execute("SELECT * FROM news_briefs WHERE project_id=? ORDER BY updated_at DESC",(project_id,)).fetchall()
        return [NewsBrief.from_record(r) for r in rows]

    def brief(self,project_id:str,brief_id:str)->NewsBrief|None:
        with self.database.connect() as c: row=c.execute("SELECT * FROM news_briefs WHERE id=? AND project_id=?",(brief_id,project_id)).fetchone()
        return NewsBrief.from_record(row) if row else None

    def brief_items(self,brief_id:str)->list[NewsBriefItem]:
        with self.database.connect() as c: rows=c.execute("SELECT * FROM news_brief_items WHERE brief_id=? ORDER BY section_key,item_order",(brief_id,)).fetchall()
        return [NewsBriefItem.from_record(r) for r in rows]

    def update_brief_item_section(self,brief_id:str,item_id:str,section_key:str,order:int=0)->NewsBriefItem:
        with self.database.connect() as c,c:
            c.execute("UPDATE news_brief_items SET section_key=?,item_order=? WHERE id=? AND brief_id=?",(section_key,int(order),item_id,brief_id))
            row=c.execute("SELECT * FROM news_brief_items WHERE id=? AND brief_id=?",(item_id,brief_id)).fetchone()
        if row is None: raise KeyError("Brief item not found.")
        return NewsBriefItem.from_record(row)

    # Script grounding ------------------------------------------------
    def replace_script_mappings(self,project_id:str,script_id:str,mappings:Iterable[NewsScriptMapping])->None:
        values=list(mappings)
        with self.database.connect() as c,c:
            c.execute("DELETE FROM news_script_mappings WHERE project_id=? AND script_id=?",(project_id,script_id))
            for m in values:self._insert_mapping(c,m)

    def mappings(self,project_id:str,script_id:str|None=None)->list[NewsScriptMapping]:
        sql="SELECT * FROM news_script_mappings WHERE project_id=?"; params=[project_id]
        if script_id: sql+=" AND script_id=?"; params.append(script_id)
        sql+=" ORDER BY created_at ASC"
        with self.database.connect() as c: rows=c.execute(sql,tuple(params)).fetchall()
        return [NewsScriptMapping.from_record(r) for r in rows]

    def update_mapping(self,m:NewsScriptMapping)->NewsScriptMapping:
        m.updated_at=utc_now_iso()
        with self.database.connect() as c,c:
            c.execute("UPDATE news_script_mappings SET text_snapshot=?,claim_ids_json=?,mapping_type=?,status=?,metadata_json=?,updated_at=? WHERE id=? AND project_id=?",
                      (m.text_snapshot,_json(m.claim_ids),m.mapping_type,m.status,_json(m.metadata),m.updated_at,m.mapping_id,m.project_id))
        return m

    # Duplication ------------------------------------------------------
    def duplicate_project(self,source_project_id:str,target_project_id:str,*,script_map:dict[str,str]|None=None,section_map:dict[str,str]|None=None)->dict[str,dict[str,str]]:
        script_map=script_map or {}; section_map=section_map or {}
        maps={"source":{},"snapshot":{},"claim":{},"evidence":{},"brief":{},"brief_item":{},"mapping":{}}
        src_meta=self.get_project(source_project_id)
        if src_meta:
            meta=NewsProjectMetadata(target_project_id,src_meta.topic,src_meta.angle,src_meta.region,src_meta.language,src_meta.target_audience,src_meta.target_duration_ms,src_meta.platform,src_meta.status,src_meta.source_fingerprint,metadata=dict(src_meta.metadata))
            self.upsert_project(meta)
        with self.database.connect() as c,c:
            for r in c.execute("SELECT * FROM news_sources WHERE project_id=? ORDER BY created_at",(source_project_id,)).fetchall():
                new=str(uuid4()); maps["source"][str(r["id"])]=new
                vals=list(r); vals[0]=new; vals[1]=target_project_id; vals[14]=None
                c.execute("""INSERT INTO news_sources(id,project_id,source_type,title,url,publisher,author,published_at,accessed_at,language,status,source_path,category,notes,latest_snapshot_id,source_updated,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",tuple(vals))
            for r in c.execute("SELECT ss.* FROM news_source_snapshots ss JOIN news_sources s ON s.id=ss.source_id WHERE s.project_id=? ORDER BY ss.retrieved_at",(source_project_id,)).fetchall():
                new=str(uuid4()); old=str(r["id"]); maps["snapshot"][old]=new; ns=maps["source"][str(r["source_id"])]
                c.execute("INSERT INTO news_source_snapshots(id,source_id,retrieved_at,content_text,content_hash,title,author,published_at,metadata_json) VALUES(?,?,?,?,?,?,?,?,?)",
                          (new,ns,r["retrieved_at"],r["content_text"],r["content_hash"],r["title"],r["author"],r["published_at"],r["metadata_json"]))
            for old,new in maps["source"].items():
                oldrow=c.execute("SELECT latest_snapshot_id FROM news_sources WHERE id=?",(old,)).fetchone()
                latest=maps["snapshot"].get(str(oldrow["latest_snapshot_id"])) if oldrow and oldrow["latest_snapshot_id"] else None
                c.execute("UPDATE news_sources SET latest_snapshot_id=? WHERE id=?",(latest,new))
            for r in c.execute("SELECT * FROM news_claims WHERE project_id=? ORDER BY created_at",(source_project_id,)).fetchall():
                new=str(uuid4()); maps["claim"][str(r["id"])]=new; vals=list(r); vals[0]=new; vals[1]=target_project_id
                c.execute("INSERT INTO news_claims(id,project_id,text,claim_type,status,importance,uncertainty,user_modified,locked,notes,quote_text,speaker,quote_kind,original_quote,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",tuple(vals))
            for r in c.execute("SELECT e.* FROM news_evidence e JOIN news_claims cl ON cl.id=e.claim_id WHERE cl.project_id=?",(source_project_id,)).fetchall():
                new=str(uuid4()); maps["evidence"][str(r["id"])]=new
                c.execute("INSERT INTO news_evidence(id,claim_id,source_id,snapshot_id,evidence_text,source_start_offset,source_end_offset,evidence_type,metadata_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                          (new,maps["claim"][str(r["claim_id"])],maps["source"][str(r["source_id"])],maps["snapshot"][str(r["snapshot_id"])],r["evidence_text"],r["source_start_offset"],r["source_end_offset"],r["evidence_type"],r["metadata_json"],r["created_at"]))
            for r in c.execute("SELECT * FROM news_briefs WHERE project_id=?",(source_project_id,)).fetchall():
                new=str(uuid4()); maps["brief"][str(r["id"])]=new
                c.execute("INSERT INTO news_briefs(id,project_id,title,summary,status,source_fingerprint,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                          (new,target_project_id,r["title"],r["summary"],r["status"],r["source_fingerprint"],r["metadata_json"],r["created_at"],r["updated_at"]))
            for r in c.execute("SELECT bi.* FROM news_brief_items bi JOIN news_briefs b ON b.id=bi.brief_id WHERE b.project_id=?",(source_project_id,)).fetchall():
                new=str(uuid4()); maps["brief_item"][str(r["id"])]=new; claim=maps["claim"].get(str(r["claim_id"])) if r["claim_id"] else None
                c.execute("INSERT INTO news_brief_items(id,brief_id,section_key,claim_id,editor_note,item_order,metadata_json) VALUES(?,?,?,?,?,?,?)",
                          (new,maps["brief"][str(r["brief_id"])],r["section_key"],claim,r["editor_note"],r["item_order"],r["metadata_json"]))
            for r in c.execute("SELECT * FROM news_script_mappings WHERE project_id=?",(source_project_id,)).fetchall():
                old_script=str(r["script_id"]); old_section=str(r["script_section_id"])
                if old_script not in script_map or old_section not in section_map: continue
                new=str(uuid4()); maps["mapping"][str(r["id"])]=new
                ids=[maps["claim"].get(cid,cid) for cid in json.loads(str(r["claim_ids_json"] or "[]"))]
                c.execute("INSERT INTO news_script_mappings(id,project_id,script_id,script_section_id,sentence_key,text_snapshot,claim_ids_json,mapping_type,status,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                          (new,target_project_id,script_map[old_script],section_map[old_section],r["sentence_key"],r["text_snapshot"],_json(ids),r["mapping_type"],r["status"],r["metadata_json"],r["created_at"],r["updated_at"]))
        return maps

    # Internals --------------------------------------------------------
    def _insert_source(self,c,s:NewsSource)->None:
        c.execute("INSERT INTO news_sources(id,project_id,source_type,title,url,publisher,author,published_at,accessed_at,language,status,source_path,category,notes,latest_snapshot_id,source_updated,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (s.source_id,s.project_id,s.type_code,s.title,s.url,s.publisher,s.author,s.published_at,s.accessed_at,s.language,s.status_code,s.source_path,s.category,s.notes,s.latest_snapshot_id,int(s.source_updated),_json(s.metadata),s.created_at,s.updated_at))
    def _insert_claim(self,c,cl:NewsClaim)->None:
        c.execute("INSERT INTO news_claims(id,project_id,text,claim_type,status,importance,uncertainty,user_modified,locked,notes,quote_text,speaker,quote_kind,original_quote,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (cl.claim_id,cl.project_id,cl.text,cl.claim_type,cl.status_code,cl.importance,cl.uncertainty,int(cl.user_modified),int(cl.locked),cl.notes,cl.quote_text,cl.speaker,cl.quote_kind,cl.original_quote,_json(cl.metadata),cl.created_at,cl.updated_at))
    def _insert_brief_item(self,c,i:NewsBriefItem)->None:
        c.execute("INSERT INTO news_brief_items(id,brief_id,section_key,claim_id,editor_note,item_order,metadata_json) VALUES(?,?,?,?,?,?,?)",(i.item_id,i.brief_id,i.section_key,i.claim_id,i.editor_note,i.order,_json(i.metadata)))
    def _insert_mapping(self,c,m:NewsScriptMapping)->None:
        c.execute("INSERT INTO news_script_mappings(id,project_id,script_id,script_section_id,sentence_key,text_snapshot,claim_ids_json,mapping_type,status,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                  (m.mapping_id,m.project_id,m.script_id,m.script_section_id,m.sentence_key,m.text_snapshot,_json(m.claim_ids),m.mapping_type,m.status,_json(m.metadata),m.created_at,m.updated_at))
