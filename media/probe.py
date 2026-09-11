from __future__ import annotations

import copy
import json
import subprocess
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


class MediaProbeError(RuntimeError): pass
class FFprobeUnavailableError(MediaProbeError): pass
class MediaProbeTimeoutError(MediaProbeError): pass
class InvalidMediaError(MediaProbeError): pass


@dataclass(slots=True)
class MediaProbeResult:
    duration_ms: int | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    codec: str | None = None
    audio_codec: str | None = None
    sample_rate: int | None = None
    channels: int | None = None
    container: str | None = None
    bit_rate: int | None = None
    rotation: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    def metadata(self) -> dict[str, Any]:
        return {"container":self.container,"bit_rate":self.bit_rate,"rotation":self.rotation,"ffprobe":self.raw}


def parse_rational_fps(value: object) -> float | None:
    if value is None:return None
    text=str(value).strip()
    if not text or text in {"0/0","N/A"}:return None
    try:
        if "/" in text:
            n,d=text.split("/",1); dv=float(d)
            if dv==0:return None
            out=float(n)/dv
        else:out=float(text)
        return out if out>=0 else None
    except (TypeError,ValueError,ZeroDivisionError):return None


def parse_duration_ms(value: object) -> int | None:
    if value in (None,"","N/A"):return None
    try:
        seconds=float(str(value));return int(round(seconds*1000.0)) if seconds>=0 else None
    except (TypeError,ValueError):return None


class FFprobeService:
    """FFprobe wrapper with bounded fingerprint cache and in-flight deduplication."""
    def __init__(self, executable_provider:Callable[[],str|Path|None], *, timeout_seconds:float=15.0, runner:Callable[...,subprocess.CompletedProcess[str]]=subprocess.run, cache_entries:int=256) -> None:
        self._executable_provider=executable_provider;self.timeout_seconds=timeout_seconds;self._runner=runner
        self.cache_entries=max(8,int(cache_entries));self._cache:OrderedDict[tuple,MediaProbeResult]=OrderedDict();self._lock=threading.RLock();self._inflight:dict[tuple,threading.Event]={}

    def probe(self,path:str|Path,expected_type:str|None=None)->MediaProbeResult:
        source=Path(path); executable=self._executable_provider()
        if not executable:raise FFprobeUnavailableError("FFprobe is required to inspect video and audio files. Configure it in Settings.")
        key=self._cache_key(source,expected_type,str(executable))
        owner=False
        while True:
            with self._lock:
                cached=self._cache.get(key)
                if cached is not None:
                    self._cache.move_to_end(key);return copy.deepcopy(cached)
                event=self._inflight.get(key)
                if event is None:
                    event=threading.Event();self._inflight[key]=event;owner=True;break
            event.wait(timeout=self.timeout_seconds+1.0)
        if not owner:
            # Defensive; loop above only breaks for owner.
            return self.probe(source,expected_type)
        try:
            result=self._probe_uncached(source,expected_type,executable)
            with self._lock:
                self._cache[key]=copy.deepcopy(result);self._cache.move_to_end(key)
                while len(self._cache)>self.cache_entries:self._cache.popitem(last=False)
            return result
        finally:
            with self._lock:
                done=self._inflight.pop(key,None)
                if done:done.set()

    def invalidate(self,path:str|Path|None=None)->None:
        with self._lock:
            if path is None:self._cache.clear();return
            target=str(Path(path).expanduser().resolve(strict=False))
            for key in [k for k in self._cache if k[0]==target]:self._cache.pop(key,None)

    def cache_info(self)->dict[str,int]:
        with self._lock:return {"entries":len(self._cache),"capacity":self.cache_entries,"inflight":len(self._inflight)}

    def _cache_key(self,source:Path,expected_type:str|None,executable:str)->tuple:
        resolved=source.expanduser().resolve(strict=False)
        try:s=resolved.stat();size=int(s.st_size);mtime=int(s.st_mtime_ns)
        except OSError:size=-1;mtime=-1
        return (str(resolved),size,mtime,str(expected_type or ""),str(executable))

    def _probe_uncached(self,source:Path,expected_type:str|None,executable:str|Path)->MediaProbeResult:
        command=[str(executable),"-v","error","-print_format","json","-show_format","-show_streams",str(source)]
        try:completed=self._runner(command,check=False,capture_output=True,text=True,timeout=self.timeout_seconds,shell=False)
        except subprocess.TimeoutExpired as exc:raise MediaProbeTimeoutError(f"FFprobe timed out while inspecting {source.name}.") from exc
        except OSError as exc:raise FFprobeUnavailableError("FFprobe could not be started.") from exc
        except subprocess.SubprocessError as exc:raise MediaProbeError("FFprobe could not inspect this media file.") from exc
        if completed.returncode!=0:
            detail=(completed.stderr or "").strip();raise InvalidMediaError(detail or "The media file is invalid or unsupported.")
        try:payload=json.loads(completed.stdout or "{}")
        except json.JSONDecodeError as exc:raise InvalidMediaError("FFprobe returned invalid metadata.") from exc
        return self.parse_payload(payload,expected_type=expected_type)

    @staticmethod
    def parse_payload(payload:dict[str,Any],expected_type:str|None=None)->MediaProbeResult:
        streams=payload.get("streams") if isinstance(payload.get("streams"),list) else []
        video=next((x for x in streams if isinstance(x,dict) and x.get("codec_type")=="video"),None)
        audio=next((x for x in streams if isinstance(x,dict) and x.get("codec_type")=="audio"),None)
        if expected_type=="video" and video is None:raise InvalidMediaError("The selected file does not contain a usable video stream.")
        if expected_type=="audio" and audio is None:raise InvalidMediaError("The selected file does not contain a usable audio stream.")
        if expected_type in {"video","audio"} and not streams:raise InvalidMediaError("The selected file does not contain readable media streams.")
        fmt=payload.get("format") if isinstance(payload.get("format"),dict) else {};duration=fmt.get("duration")
        if duration in (None,"N/A"):
            primary=video if expected_type=="video" else audio
            if isinstance(primary,dict):duration=primary.get("duration")
        return MediaProbeResult(duration_ms=parse_duration_ms(duration),width=FFprobeService._int_or_none(video.get("width")) if video else None,height=FFprobeService._int_or_none(video.get("height")) if video else None,fps=parse_rational_fps(video.get("avg_frame_rate") or video.get("r_frame_rate")) if video else None,codec=str(video.get("codec_name")) if video and video.get("codec_name") else None,audio_codec=str(audio.get("codec_name")) if audio and audio.get("codec_name") else None,sample_rate=FFprobeService._int_or_none(audio.get("sample_rate")) if audio else None,channels=FFprobeService._int_or_none(audio.get("channels")) if audio else None,container=str(fmt.get("format_name")) if fmt.get("format_name") else None,bit_rate=FFprobeService._int_or_none(fmt.get("bit_rate")),rotation=FFprobeService._rotation(video),raw=payload)

    @staticmethod
    def _rotation(video:dict[str,Any]|None)->int|None:
        if not video:return None
        tags=video.get("tags")
        if isinstance(tags,dict) and tags.get("rotate") is not None:
            try:return int(round(float(tags["rotate"])))
            except (TypeError,ValueError):pass
        side=video.get("side_data_list")
        if isinstance(side,list):
            for item in side:
                if isinstance(item,dict) and item.get("rotation") is not None:
                    try:return int(round(float(item["rotation"])))
                    except (TypeError,ValueError):continue
        return None

    @staticmethod
    def _int_or_none(value:object)->int|None:
        if value in (None,"","N/A"):return None
        try:return int(float(str(value)))
        except (TypeError,ValueError):return None
