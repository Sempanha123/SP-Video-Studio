from __future__ import annotations
import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4
from domain.project import utc_now_iso

class AssetType(StrEnum): VIDEO="video"; IMAGE="image"; AUDIO="audio"
class AssetStatus(StrEnum): READY="ready"; PROCESSING="processing"; MISSING="missing"; INVALID="invalid"; FAILED="failed"; CHANGED="changed"
class AssetStorageMode(StrEnum): MANAGED="managed"; REFERENCED="referenced"
VIDEO_SUBTYPES={"broll","presenter","reporter","character","interview","background","intro","outro","green_screen","overlay_video","general"}
IMAGE_SUBTYPES={"logo","background","overlay","lower_third","texture","thumbnail","general"}
AUDIO_SUBTYPES={"music","sfx","voice_clip","intro","outro","ambience","general"}
SUBTYPES={"video":VIDEO_SUBTYPES,"image":IMAGE_SUBTYPES,"audio":AUDIO_SUBTYPES}

@dataclass(slots=True)
class Asset:
    name:str
    asset_type:str|AssetType
    subtype:str="general"
    file_path:str=""
    managed:bool=True
    relative_path:str=""
    thumbnail_path:str=""
    duration_ms:int|None=None
    width:int|None=None
    height:int|None=None
    fps:float|None=None
    video_codec:str=""
    audio_codec:str=""
    sample_rate:int|None=None
    channels:int|None=None
    file_size:int=0
    mime_type:str=""
    extension:str=""
    fingerprint:str=""
    fingerprint_kind:str="sha256"
    source_mtime_ns:int=0
    original_filename:str=""
    created_at:str=field(default_factory=utc_now_iso)
    updated_at:str=field(default_factory=utc_now_iso)
    last_used_at:str=""
    favorite:bool=False
    status:str|AssetStatus=AssetStatus.READY
    notes:str=""
    spoken_language:str=""
    metadata:dict[str,Any]=field(default_factory=dict)
    asset_id:str=field(default_factory=lambda:str(uuid4()))
    @property
    def id(self): return self.asset_id
    @property
    def type(self): return self.asset_type.value if isinstance(self.asset_type,StrEnum) else str(self.asset_type)
    @property
    def status_code(self): return self.status.value if isinstance(self.status,StrEnum) else str(self.status)
    @property
    def storage_mode(self): return AssetStorageMode.MANAGED.value if self.managed else AssetStorageMode.REFERENCED.value
    def resolved_path(self,library_root:Path)->Path:
        return (Path(library_root)/self.relative_path).resolve() if self.managed else Path(self.file_path).expanduser().resolve()
    def resolved_thumbnail(self,library_root:Path)->Path|None:
        if not self.thumbnail_path:return None
        p=Path(self.thumbnail_path)
        return (Path(library_root)/p).resolve() if not p.is_absolute() else p.resolve()
    def validate(self):
        if not self.id or not self.name.strip(): raise ValueError("Asset identity and name are required.")
        if self.type not in SUBTYPES: raise ValueError("Unsupported asset type.")
        if self.subtype not in SUBTYPES[self.type]: raise ValueError("Unsupported asset subtype.")
        if self.status_code not in {x.value for x in AssetStatus}: raise ValueError("Unsupported asset status.")
        if self.managed:
            if not self.relative_path: raise ValueError("Managed assets require a relative library path.")
            rel=Path(self.relative_path)
            if rel.is_absolute() or ".." in rel.parts: raise ValueError("Managed asset path must stay inside the Asset Library.")
        if not self.managed and not self.file_path: raise ValueError("Referenced assets require an external file path.")
        if self.file_size<0: raise ValueError("Asset file size cannot be negative.")
    def to_dict(self):
        return {"id":self.id,"name":self.name,"type":self.type,"subtype":self.subtype,"filePath":self.file_path,"managed":self.managed,"storageMode":self.storage_mode,"relativePath":self.relative_path,"thumbnailPath":self.thumbnail_path,"durationMs":self.duration_ms,"width":self.width,"height":self.height,"fps":self.fps,"videoCodec":self.video_codec,"audioCodec":self.audio_codec,"sampleRate":self.sample_rate,"channels":self.channels,"fileSize":self.file_size,"mimeType":self.mime_type,"extension":self.extension,"fingerprint":self.fingerprint,"fingerprintKind":self.fingerprint_kind,"sourceMtimeNs":self.source_mtime_ns,"originalFilename":self.original_filename,"createdAt":self.created_at,"updatedAt":self.updated_at,"lastUsedAt":self.last_used_at,"favorite":self.favorite,"status":self.status_code,"notes":self.notes,"spokenLanguage":self.spoken_language,"metadata":dict(self.metadata)}
    @classmethod
    def from_record(cls,r:Mapping[str,Any]):
        try:m=json.loads(r["metadata_json"] or "{}")
        except Exception:m={}
        return cls(asset_id=str(r["id"]),name=str(r["name"]),asset_type=str(r["type"]),subtype=str(r["subtype"]),file_path=str(r["file_path"] or ""),managed=bool(r["managed"]),relative_path=str(r["relative_path"] or ""),thumbnail_path=str(r["thumbnail_path"] or ""),duration_ms=int(r["duration_ms"]) if r["duration_ms"] is not None else None,width=int(r["width"]) if r["width"] is not None else None,height=int(r["height"]) if r["height"] is not None else None,fps=float(r["fps"]) if r["fps"] is not None else None,video_codec=str(r["video_codec"] or ""),audio_codec=str(r["audio_codec"] or ""),sample_rate=int(r["sample_rate"]) if r["sample_rate"] is not None else None,channels=int(r["channels"]) if r["channels"] is not None else None,file_size=int(r["file_size"]),mime_type=str(r["mime_type"] or ""),extension=str(r["extension"] or ""),fingerprint=str(r["fingerprint"] or ""),fingerprint_kind=str(r["fingerprint_kind"] or "sha256"),source_mtime_ns=int(r["source_mtime_ns"] or 0),original_filename=str(r["original_filename"] or ""),created_at=str(r["created_at"]),updated_at=str(r["updated_at"]),last_used_at=str(r["last_used_at"] or ""),favorite=bool(r["favorite"]),status=str(r["status"]),notes=str(r["notes"] or ""),spoken_language=str(r["spoken_language"] or ""),metadata=m if isinstance(m,dict) else {})
