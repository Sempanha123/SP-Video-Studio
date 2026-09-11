from __future__ import annotations
import json,unicodedata
from pathlib import Path
from typing import Any
from domain.asset import Asset
from domain.asset_collection import AssetCollection
from domain.asset_usage import AssetUsage
from domain.asset_license import AssetLicense
from domain.project import utc_now_iso
from storage.database import SQLiteDatabase

def _dump(x): return json.dumps(x,ensure_ascii=False,separators=(",",":"))
def _load(x,default):
    try:return json.loads(str(x or ""))
    except Exception:return default

def normalize_tag(value:str)->str:return unicodedata.normalize("NFKC",value.strip()).casefold()

class AssetRepository:
    def __init__(self,database:SQLiteDatabase,default_root:Path):
        self.database=database; self.default_root=Path(default_root).expanduser().resolve(); self.default_root.mkdir(parents=True,exist_ok=True)
        with self.database.connect() as c,c:
            row=c.execute("SELECT value FROM asset_library_settings WHERE key='root'").fetchone()
            if row is None:c.execute("INSERT INTO asset_library_settings(key,value) VALUES('root',?)",(str(self.default_root),)); self._root=self.default_root
            else:self._root=Path(str(row["value"])).expanduser().resolve(); self._root.mkdir(parents=True,exist_ok=True)
    @property
    def library_root(self)->Path:return self._root
    def set_library_root(self,path:Path)->None:
        root=Path(path).expanduser().resolve(); root.mkdir(parents=True,exist_ok=True)
        with self.database.connect() as c,c:c.execute("INSERT INTO asset_library_settings(key,value) VALUES('root',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(str(root),))
        self._root=root
    def create(self,a:Asset)->Asset:
        a.validate()
        with self.database.connect() as c,c:c.execute("""INSERT INTO assets(id,name,type,subtype,file_path,managed,relative_path,thumbnail_path,duration_ms,width,height,fps,video_codec,audio_codec,sample_rate,channels,file_size,mime_type,extension,fingerprint,fingerprint_kind,source_mtime_ns,original_filename,created_at,updated_at,last_used_at,favorite,status,notes,spoken_language,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",self._values(a))
        return a
    def update(self,a:Asset)->Asset:
        a.validate(); a.updated_at=utc_now_iso()
        vals=self._values(a)
        with self.database.connect() as c,c:
            cur=c.execute("""UPDATE assets SET name=?,type=?,subtype=?,file_path=?,managed=?,relative_path=?,thumbnail_path=?,duration_ms=?,width=?,height=?,fps=?,video_codec=?,audio_codec=?,sample_rate=?,channels=?,file_size=?,mime_type=?,extension=?,fingerprint=?,fingerprint_kind=?,source_mtime_ns=?,original_filename=?,created_at=?,updated_at=?,last_used_at=?,favorite=?,status=?,notes=?,spoken_language=?,metadata_json=? WHERE id=?""",vals[1:]+(a.id,))
            if not cur.rowcount:raise KeyError("Asset not found.")
        return a
    def get(self,asset_id:str)->Asset|None:
        with self.database.connect() as c:r=c.execute("SELECT * FROM assets WHERE id=?",(asset_id,)).fetchone()
        return Asset.from_record(r) if r else None
    def list_all(self)->list[Asset]:
        with self.database.connect() as c:rows=c.execute("SELECT * FROM assets ORDER BY created_at DESC").fetchall()
        return [Asset.from_record(x) for x in rows]
    def list_with_metadata(self)->list[dict[str,Any]]:
        """Bulk Asset Library read used by large virtualized views.

        Phase 25 originally loaded tags/collections/usage one asset at a time.
        This keeps the same domain objects while collapsing the N+1 pattern to
        four SQLite queries regardless of library size.
        """
        with self.database.connect() as c:
            assets=c.execute("SELECT * FROM assets ORDER BY created_at DESC").fetchall()
            tag_rows=c.execute("SELECT i.asset_id,t.name FROM asset_tag_items i JOIN asset_tags t ON t.id=i.tag_id ORDER BY t.name COLLATE NOCASE").fetchall()
            collection_rows=c.execute("SELECT i.asset_id,c.id,c.name FROM asset_collection_items i JOIN asset_collections c ON c.id=i.collection_id ORDER BY c.name COLLATE NOCASE").fetchall()
            usage_rows=c.execute("SELECT asset_id,COUNT(DISTINCT project_id) n FROM asset_usage GROUP BY asset_id").fetchall()
        tags:dict[str,list[str]]={};collections:dict[str,list[dict[str,str]]]={};usage={str(r["asset_id"]):int(r["n"]) for r in usage_rows}
        for r in tag_rows:tags.setdefault(str(r["asset_id"]),[]).append(str(r["name"]))
        for r in collection_rows:collections.setdefault(str(r["asset_id"]),[]).append({"id":str(r["id"]),"name":str(r["name"])})
        return [{"asset":Asset.from_record(r),"tags":tags.get(str(r["id"]),[]),"collections":collections.get(str(r["id"]),[]),"usageCount":usage.get(str(r["id"]),0)} for r in assets]

    def find_fingerprint(self,fingerprint:str,size:int)->list[Asset]:
        with self.database.connect() as c:rows=c.execute("SELECT * FROM assets WHERE fingerprint=? AND file_size=?",(fingerprint,int(size))).fetchall()
        return [Asset.from_record(x) for x in rows]
    def delete(self,asset_id:str)->None:
        with self.database.connect() as c,c:
            cur=c.execute("DELETE FROM assets WHERE id=?",(asset_id,))
            if not cur.rowcount:raise KeyError("Asset not found.")
    def touch_used(self,asset_id:str)->None:
        now=utc_now_iso()
        with self.database.connect() as c,c:c.execute("UPDATE assets SET last_used_at=?,updated_at=? WHERE id=?",(now,now,asset_id))
    def set_status(self,asset_id:str,status:str)->None:
        with self.database.connect() as c,c:c.execute("UPDATE assets SET status=?,updated_at=? WHERE id=?",(status,utc_now_iso(),asset_id))
    def count(self)->int:
        with self.database.connect() as c:r=c.execute("SELECT COUNT(*) n FROM assets").fetchone()
        return int(r["n"])

    def create_collection(self,item:AssetCollection)->AssetCollection:
        item.validate()
        with self.database.connect() as c,c:c.execute("INSERT INTO asset_collections(id,name,description,created_at,updated_at,metadata_json) VALUES(?,?,?,?,?,?)",(item.id,item.name,item.description,item.created_at,item.updated_at,_dump(item.metadata)))
        return item
    def collections(self)->list[dict[str,Any]]:
        with self.database.connect() as c:rows=c.execute("SELECT c.*,COUNT(i.asset_id) item_count FROM asset_collections c LEFT JOIN asset_collection_items i ON i.collection_id=c.id GROUP BY c.id ORDER BY c.name COLLATE NOCASE").fetchall()
        return [{"id":str(r["id"]),"name":str(r["name"]),"description":str(r["description"]),"itemCount":int(r["item_count"]),"metadata":_load(r["metadata_json"],{})} for r in rows]
    def rename_collection(self,cid:str,name:str)->None:
        with self.database.connect() as c,c:c.execute("UPDATE asset_collections SET name=?,updated_at=? WHERE id=?",(name.strip(),utc_now_iso(),cid))
    def delete_collection(self,cid:str)->None:
        with self.database.connect() as c,c:c.execute("DELETE FROM asset_collections WHERE id=?",(cid,))
    def set_collection_membership(self,asset_id:str,cid:str,enabled:bool)->None:
        with self.database.connect() as c,c:
            if enabled:c.execute("INSERT OR IGNORE INTO asset_collection_items(collection_id,asset_id) VALUES(?,?)",(cid,asset_id))
            else:c.execute("DELETE FROM asset_collection_items WHERE collection_id=? AND asset_id=?",(cid,asset_id))
    def asset_collections(self,asset_id:str)->list[str]:
        with self.database.connect() as c:rows=c.execute("SELECT collection_id FROM asset_collection_items WHERE asset_id=?",(asset_id,)).fetchall()
        return [str(x["collection_id"]) for x in rows]
    def assets_in_collection(self,cid:str)->set[str]:
        with self.database.connect() as c:rows=c.execute("SELECT asset_id FROM asset_collection_items WHERE collection_id=?",(cid,)).fetchall()
        return {str(x["asset_id"]) for x in rows}

    def set_tags(self,asset_id:str,tags:list[str])->None:
        clean=[]; seen=set()
        for raw in tags:
            name=unicodedata.normalize("NFKC",str(raw).strip())
            norm=normalize_tag(name)
            if name and norm not in seen: clean.append((name,norm));seen.add(norm)
        with self.database.connect() as c,c:
            c.execute("DELETE FROM asset_tag_items WHERE asset_id=?",(asset_id,))
            for name,norm in clean:
                c.execute("INSERT INTO asset_tags(name,normalized_name) VALUES(?,?) ON CONFLICT(normalized_name) DO UPDATE SET name=excluded.name",(name,norm))
                row=c.execute("SELECT id FROM asset_tags WHERE normalized_name=?",(norm,)).fetchone(); c.execute("INSERT OR IGNORE INTO asset_tag_items(tag_id,asset_id) VALUES(?,?)",(int(row["id"]),asset_id))
    def tags(self,asset_id:str)->list[str]:
        with self.database.connect() as c:rows=c.execute("SELECT t.name FROM asset_tags t JOIN asset_tag_items i ON i.tag_id=t.id WHERE i.asset_id=? ORDER BY t.name COLLATE NOCASE",(asset_id,)).fetchall()
        return [str(x["name"]) for x in rows]
    def all_tags(self)->list[str]:
        with self.database.connect() as c:rows=c.execute("SELECT name FROM asset_tags ORDER BY name COLLATE NOCASE").fetchall()
        return [str(x["name"]) for x in rows]

    def record_usage(self,u:AssetUsage)->AssetUsage:
        u.validate()
        with self.database.connect() as c,c:c.execute("INSERT INTO asset_usage(id,asset_id,project_id,project_media_id,used_at,usage_type,metadata_json) VALUES(?,?,?,?,?,?,?) ON CONFLICT(project_media_id) DO UPDATE SET asset_id=excluded.asset_id,project_id=excluded.project_id,used_at=excluded.used_at,usage_type=excluded.usage_type,metadata_json=excluded.metadata_json",(u.id,u.asset_id,u.project_id,u.project_media_id,u.used_at,u.usage_type,_dump(u.metadata)))
        self.touch_used(u.asset_id);return u
    def usages(self,asset_id:str)->list[dict[str,Any]]:
        with self.database.connect() as c:rows=c.execute("SELECT * FROM asset_usage WHERE asset_id=? ORDER BY used_at DESC",(asset_id,)).fetchall()
        return [{"id":str(r["id"]),"assetId":str(r["asset_id"]),"projectId":str(r["project_id"]),"projectMediaId":str(r["project_media_id"]),"usedAt":str(r["used_at"]),"usageType":str(r["usage_type"]),"metadata":_load(r["metadata_json"],{})} for r in rows]
    def project_usages(self,project_id:str)->list[dict[str,Any]]:
        with self.database.connect() as c:rows=c.execute("SELECT * FROM asset_usage WHERE project_id=? ORDER BY used_at DESC",(project_id,)).fetchall()
        return [dict(r) for r in rows]
    def remove_usage_for_media(self,media_id:str)->None:
        with self.database.connect() as c,c:c.execute("DELETE FROM asset_usage WHERE project_media_id=?",(media_id,))
    def remove_usage_for_project(self,project_id:str)->None:
        with self.database.connect() as c,c:c.execute("DELETE FROM asset_usage WHERE project_id=?",(project_id,))
    def usage_count(self,asset_id:str)->int:
        with self.database.connect() as c:r=c.execute("SELECT COUNT(DISTINCT project_id) n FROM asset_usage WHERE asset_id=?",(asset_id,)).fetchone()
        return int(r["n"])

    def set_license(self,item:AssetLicense)->AssetLicense:
        item.validate()
        with self.database.connect() as c,c:c.execute("""INSERT INTO asset_licenses(asset_id,rights_status,source_url,license_name,notes,attribution_required,attribution_text,metadata_json) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(asset_id) DO UPDATE SET rights_status=excluded.rights_status,source_url=excluded.source_url,license_name=excluded.license_name,notes=excluded.notes,attribution_required=excluded.attribution_required,attribution_text=excluded.attribution_text,metadata_json=excluded.metadata_json""",(item.asset_id,item.rights_status,item.source_url,item.license_name,item.notes,int(item.attribution_required),item.attribution_text,_dump(item.metadata)))
        return item
    def license(self,asset_id:str)->AssetLicense:
        with self.database.connect() as c:r=c.execute("SELECT * FROM asset_licenses WHERE asset_id=?",(asset_id,)).fetchone()
        return AssetLicense.from_record(r) if r else AssetLicense(asset_id)
    @staticmethod
    def _values(a:Asset):
        return (a.id,a.name,a.type,a.subtype,a.file_path,int(a.managed),a.relative_path,a.thumbnail_path,a.duration_ms,a.width,a.height,a.fps,a.video_codec,a.audio_codec,a.sample_rate,a.channels,a.file_size,a.mime_type,a.extension,a.fingerprint,a.fingerprint_kind,a.source_mtime_ns,a.original_filename,a.created_at,a.updated_at,a.last_used_at,int(a.favorite),a.status_code,a.notes,a.spoken_language,_dump(a.metadata))
