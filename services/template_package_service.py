from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from uuid import uuid4

from domain.template import Template
from domain.template_asset import EXECUTABLE_TEMPLATE_EXTENSIONS, TemplateAsset, is_safe_relative_template_path
from domain.template_errors import TemplateChecksumError, TemplatePackageError, TemplatePackageUnsafe, TemplateVersionTooNew
from domain.template_manifest import TEMPLATE_SCHEMA_VERSION, TemplateManifest
from services.template_schema_migrator import TemplateSchemaMigrator
from services.template_validation_service import TemplateValidationService

MAX_PACKAGE_BYTES=256*1024*1024
MAX_MEMBER_BYTES=96*1024*1024
MAX_MEMBERS=512
MAX_UNCOMPRESSED_BYTES=512*1024*1024


def _sha256(data:bytes)->str:return hashlib.sha256(data).hexdigest()


class TemplatePackageService:
    """Portable .mmovtemplate ZIP packages. Reads members individually; never calls extractall()."""
    def __init__(self,validation:TemplateValidationService,migrator:TemplateSchemaMigrator|None=None,filename_service=None)->None:
        self.validation=validation; self.migrator=migrator or TemplateSchemaMigrator(); self.filename_service=filename_service

    def export(self,item:Template,destination:Path,*,asset_root:Path|None=None)->Path:
        self.validation.validate(item)
        destination=Path(destination)
        if destination.suffix.lower()!=".mmovtemplate": destination=destination.with_suffix(".mmovtemplate")
        destination.parent.mkdir(parents=True,exist_ok=True)
        package_data=item.to_dict(); package_data.pop("manifestPath",None)
        preview_source=None
        if item.preview_image:
            candidate=Path(item.preview_image)
            if not candidate.is_absolute() and item.manifest_path: candidate=Path(item.manifest_path).parent/candidate
            if candidate.is_file() and candidate.suffix.lower() in {".png",".jpg",".jpeg",".webp"}:
                preview_source=candidate; package_data["previewImage"]="preview"+candidate.suffix.lower()
            else: package_data["previewImage"]=""
        template_bytes=json.dumps(package_data,ensure_ascii=False,indent=2).encode("utf-8")
        checksums={"template.json":_sha256(template_bytes)}; payload_assets=[]
        asset_root=Path(asset_root) if asset_root else None
        asset_bytes:dict[str,bytes]={}
        for asset in item.assets:
            asset.validate(); path=(asset_root/asset.relative_path) if asset_root else None
            if path is None or not path.is_file():
                if asset.optional: continue
                raise TemplatePackageError(f"Template asset is missing: {asset.relative_path}")
            data=path.read_bytes()
            if len(data)>MAX_MEMBER_BYTES: raise TemplatePackageError("Template asset is too large.")
            expected=asset.sha256 or _sha256(data)
            if asset.sha256 and _sha256(data)!=asset.sha256: raise TemplateChecksumError(f"Asset checksum changed: {asset.relative_path}")
            arc=f"assets/{PurePosixPath(asset.relative_path).as_posix()}"; checksums[arc]=expected; asset_bytes[arc]=data
            payload_assets.append(TemplateAsset(PurePosixPath(asset.relative_path).as_posix(),expected,len(data),asset.asset_type,asset.optional,dict(asset.metadata)))
        manifest=item.manifest(); manifest.assets=payload_assets; manifest.checksums=checksums
        manifest_bytes=json.dumps(manifest.to_dict(),ensure_ascii=False,indent=2).encode("utf-8")
        temp=destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
        try:
            with zipfile.ZipFile(temp,"w",compression=zipfile.ZIP_DEFLATED) as z:
                z.writestr("manifest.json",manifest_bytes); z.writestr("template.json",template_bytes)
                if preview_source is not None:
                    data=preview_source.read_bytes()
                    if len(data)<=MAX_MEMBER_BYTES: z.writestr(f"preview{preview_source.suffix.lower()}",data)
                for arc,data in asset_bytes.items(): z.writestr(arc,data)
            if temp.stat().st_size>MAX_PACKAGE_BYTES: raise TemplatePackageError("Template package is too large.")
            os.replace(temp,destination); return destination
        finally: temp.unlink(missing_ok=True)

    def inspect(self,package:Path)->tuple[TemplateManifest,Template]:
        package=Path(package)
        if not package.is_file(): raise TemplatePackageError("Template package could not be found.")
        if package.stat().st_size>MAX_PACKAGE_BYTES: raise TemplatePackageError("Template package is too large.")
        with zipfile.ZipFile(package,"r") as z:
            infos=z.infolist(); names=[i.filename for i in infos]
            if len(infos)>MAX_MEMBERS: raise TemplatePackageError("Template package contains too many files.")
            if sum(max(0,int(i.file_size)) for i in infos)>MAX_UNCOMPRESSED_BYTES: raise TemplatePackageError("Template package expands beyond the safe size limit.")
            if len(names)!=len(set(names)): raise TemplatePackageUnsafe("Template package contains duplicate file entries.")
            for info in infos:self._validate_info(info)
            if "manifest.json" not in names or "template.json" not in names: raise TemplatePackageError("Template package is missing manifest.json or template.json.")
            manifest=TemplateManifest.from_dict(json.loads(self._read_member(z,"manifest.json").decode("utf-8")))
            if manifest.schema_version>TEMPLATE_SCHEMA_VERSION: raise TemplateVersionTooNew()
            template_raw=json.loads(self._read_member(z,"template.json").decode("utf-8")); template_raw=self.migrator.migrate(template_raw); item=Template.from_dict(template_raw,builtin=False)
            if item.id!=manifest.template_id: raise TemplatePackageError("Template ID does not match its manifest.")
            for name,expected in manifest.checksums.items():
                if name not in names: raise TemplateChecksumError(f"Checksum target is missing: {name}")
                actual=_sha256(self._read_member(z,name))
                if actual.lower()!=expected.lower(): raise TemplateChecksumError(f"Checksum verification failed: {name}")
            self.validation.validate(item); return manifest,item

    def import_package(self,package:Path,user_root:Path,*,conflict:"str"="keep_both",existing_ids:set[str]|None=None,builtin_ids:set[str]|None=None)->tuple[Template,Path]:
        manifest,item=self.inspect(package); existing_ids=existing_ids or set(); builtin_ids=builtin_ids or set(); root=Path(user_root); root.mkdir(parents=True,exist_ok=True)
        if item.id in builtin_ids: raise TemplatePackageError("Imported templates cannot overwrite a built-in template.")
        if item.id in existing_ids:
            if conflict=="cancel": raise TemplatePackageError("Template import cancelled because the ID already exists.")
            if conflict=="keep_both": item.template_id=str(uuid4()); item.name=f"{item.name} Copy"
            elif conflict!="replace": raise TemplatePackageError("Unsupported template conflict policy.")
        target=root/item.id; staging=root/f".import-{uuid4().hex}"; backup=None
        staging.mkdir(parents=True,exist_ok=False)
        try:
            with zipfile.ZipFile(package,"r") as z:
                for info in z.infolist():
                    self._validate_info(info); name=info.filename
                    if name.endswith("/"): continue
                    data=self._read_member(z,name)
                    rel=PurePosixPath(name)
                    out=staging.joinpath(*rel.parts)
                    out.parent.mkdir(parents=True,exist_ok=True); out.write_bytes(data)
            # Persist possibly remapped ID instead of package's original template.json and keep the local manifest consistent.
            rewritten=json.dumps(item.to_dict(),ensure_ascii=False,indent=2).encode("utf-8")
            (staging/"template.json").write_bytes(rewritten)
            local_manifest=item.manifest(); local_manifest.assets=list(manifest.assets); local_manifest.checksums=dict(manifest.checksums); local_manifest.checksums["template.json"]=_sha256(rewritten)
            (staging/"manifest.json").write_text(json.dumps(local_manifest.to_dict(),ensure_ascii=False,indent=2),encoding="utf-8")
            if conflict=="replace" and target.exists():
                backup=root/f".replace-backup-{uuid4().hex}"; os.replace(target,backup)
            try:
                os.replace(staging,target)
            except Exception:
                if backup is not None and backup.exists() and not target.exists(): os.replace(backup,target)
                raise
            if backup is not None: shutil.rmtree(backup,ignore_errors=True)
            item.manifest_path=str(target/"manifest.json"); return item,target
        finally:
            shutil.rmtree(staging,ignore_errors=True)
            if backup is not None and backup.exists() and target.exists(): shutil.rmtree(backup,ignore_errors=True)

    @staticmethod
    def _read_member(z:zipfile.ZipFile,name:str)->bytes:
        info=z.getinfo(name)
        if info.file_size>MAX_MEMBER_BYTES: raise TemplatePackageError("Template member is too large.")
        data=z.read(info)
        if len(data)>MAX_MEMBER_BYTES: raise TemplatePackageError("Template member is too large.")
        return data

    @staticmethod
    def _validate_info(info:zipfile.ZipInfo)->None:
        name=info.filename.replace("\\","/")
        if name.endswith("/"): name=name.rstrip("/")
        if name and not is_safe_relative_template_path(name): raise TemplatePackageUnsafe("Template package contains an unsafe path.")
        suffix=PurePosixPath(name).suffix.lower()
        if suffix in EXECUTABLE_TEMPLATE_EXTENSIONS: raise TemplatePackageUnsafe("Template package contains executable content.")
        mode=(info.external_attr>>16)&0xFFFF
        if mode and stat.S_ISLNK(mode): raise TemplatePackageUnsafe("Template package contains a symbolic link.")
        allowed_root=name in {"manifest.json","template.json","assets","docs"} or name.startswith("preview.") or name.startswith("assets/") or name.startswith("docs/")
        if name and not allowed_root: raise TemplatePackageUnsafe(f"Unexpected template package entry: {name}")
        if info.file_size>MAX_MEMBER_BYTES: raise TemplatePackageError("Template member is too large.")
