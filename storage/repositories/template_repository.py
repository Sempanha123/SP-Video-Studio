from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from domain.project import utc_now_iso
from domain.template import Template
from domain.template_asset import TemplateAsset
from storage.database import SQLiteDatabase


def _dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _load(value: object, fallback):
    try:
        parsed=json.loads(str(value or ""))
        return parsed
    except Exception:
        return fallback


class TemplateRepository:
    """SQLite metadata/index for user templates. Builtins remain resource-backed and read-only."""

    def __init__(self, database: SQLiteDatabase, user_root: Path) -> None:
        self.database=database; self.user_root=Path(user_root)
        self.user_root.mkdir(parents=True,exist_ok=True)

    def save(self, item: Template, template_json_path: Path, manifest_path: Path | None=None) -> Template:
        item.validate(); item.updated_at=utc_now_iso(); template_json_path=Path(template_json_path)
        manifest_path=Path(manifest_path) if manifest_path else template_json_path.with_name("manifest.json")
        with self.database.connect() as c,c:
            c.execute("""INSERT INTO templates(id,name,template_type,category,description,workflow,version,schema_version,author_label,preview_image,tags_json,aspects_json,languages_json,features_json,manifest_path,template_json_path,metadata_json,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET name=excluded.name,template_type=excluded.template_type,category=excluded.category,description=excluded.description,workflow=excluded.workflow,version=excluded.version,schema_version=excluded.schema_version,author_label=excluded.author_label,preview_image=excluded.preview_image,tags_json=excluded.tags_json,aspects_json=excluded.aspects_json,languages_json=excluded.languages_json,features_json=excluded.features_json,manifest_path=excluded.manifest_path,template_json_path=excluded.template_json_path,metadata_json=excluded.metadata_json,updated_at=excluded.updated_at""",
                (item.id,item.name,item.type_code,item.category,item.description,item.workflow,item.version,item.schema_version,item.author_label,item.preview_image,_dump(item.tags),_dump(item.supported_aspect_ratios),_dump(item.supported_languages),_dump(item.required_features),str(manifest_path),str(template_json_path),_dump(item.metadata),item.created_at,item.updated_at))
            c.execute("DELETE FROM template_assets WHERE template_id=?",(item.id,))
            for asset in item.assets:
                c.execute("INSERT INTO template_assets(template_id,relative_path,sha256,size_bytes,asset_type,metadata_json) VALUES(?,?,?,?,?,?)",(item.id,asset.relative_path,asset.sha256,asset.size,asset.asset_type,_dump(asset.metadata)))
        return item

    def get(self, template_id: str) -> Template | None:
        with self.database.connect() as c:
            row=c.execute("SELECT * FROM templates WHERE id=?",(template_id,)).fetchone()
        return self._from_row(row) if row else None

    def list_all(self) -> list[Template]:
        with self.database.connect() as c:
            rows=c.execute("SELECT * FROM templates ORDER BY updated_at DESC,name COLLATE NOCASE").fetchall()
        return [item for row in rows if (item:=self._from_row(row)) is not None]

    def delete(self, template_id: str) -> None:
        with self.database.connect() as c,c:
            row=c.execute("SELECT template_json_path FROM templates WHERE id=?",(template_id,)).fetchone()
            if row is None: raise KeyError("Template not found.")
            c.execute("DELETE FROM templates WHERE id=?",(template_id,))
            c.execute("DELETE FROM template_usage WHERE template_id=?",(template_id,))
        path=Path(str(row["template_json_path"]))
        try:
            folder=path.parent.resolve(); root=self.user_root.resolve()
            if folder==root or root not in folder.parents: return
            import shutil; shutil.rmtree(folder,ignore_errors=True)
        except OSError:
            pass

    def record_usage(self, template_id: str, *, project_id: str="", template_version: str="", metadata: dict[str,Any]|None=None) -> None:
        now=utc_now_iso()
        with self.database.connect() as c,c:
            c.execute("""INSERT INTO template_usage(template_id,project_id,last_used_at,use_count,template_version,metadata_json)
                VALUES(?,?,?,1,?,?) ON CONFLICT(template_id,project_id) DO UPDATE SET last_used_at=excluded.last_used_at,use_count=template_usage.use_count+1,template_version=excluded.template_version,metadata_json=excluded.metadata_json""",
                (template_id,project_id,now,template_version,_dump(metadata or {})))

    def usage(self, template_id: str, project_id: str="") -> dict[str,Any]:
        with self.database.connect() as c:
            row=c.execute("SELECT * FROM template_usage WHERE template_id=? AND project_id=?",(template_id,project_id)).fetchone()
        if not row: return {"lastUsedAt":"","useCount":0,"metadata":{}}
        return {"lastUsedAt":str(row["last_used_at"]),"useCount":int(row["use_count"]),"templateVersion":str(row["template_version"]),"metadata":_load(row["metadata_json"],{})}

    def recent(self, limit: int=12) -> list[str]:
        with self.database.connect() as c:
            rows=c.execute("SELECT template_id,MAX(last_used_at) AS last_used FROM template_usage GROUP BY template_id ORDER BY last_used DESC LIMIT ?",(max(1,int(limit)),)).fetchall()
        return [str(row["template_id"]) for row in rows]

    def rebuild_index(self) -> int:
        count=0
        for folder in self.user_root.iterdir() if self.user_root.exists() else ():
            if not folder.is_dir(): continue
            path=folder/"template.json"
            if not path.is_file(): continue
            try:
                item=Template.from_dict(json.loads(path.read_text(encoding="utf-8")),builtin=False)
                self.save(item,path,folder/"manifest.json"); count+=1
            except Exception:
                continue
        return count

    def _from_row(self,row) -> Template | None:
        path=Path(str(row["template_json_path"]))
        if not path.is_file(): return None
        try:
            raw=json.loads(path.read_text(encoding="utf-8")); item=Template.from_dict(raw,builtin=False)
            # DB index remains authoritative for mutable metadata without reparsing package assets.
            item.name=str(row["name"]); item.category=str(row["category"]); item.description=str(row["description"]); item.version=str(row["version"])
            item.preview_image=str(row["preview_image"] or ""); item.manifest_path=str(row["manifest_path"] or "")
            item.tags=tuple(str(x) for x in _load(row["tags_json"],[])); item.supported_aspect_ratios=tuple(str(x) for x in _load(row["aspects_json"],[])); item.supported_languages=tuple(str(x) for x in _load(row["languages_json"],[])); item.required_features=tuple(str(x) for x in _load(row["features_json"],[])); item.metadata=dict(_load(row["metadata_json"],{})); item.updated_at=str(row["updated_at"]); return item
        except Exception:
            return None
