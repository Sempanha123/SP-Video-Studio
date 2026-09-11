from __future__ import annotations

import re
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from workers.cancellation import CancellationToken


@dataclass(frozen=True, slots=True)
class FFmpegCapabilities:
    version: str
    encoders: frozenset[str]
    filters: frozenset[str] = frozenset()

    def has_encoder(self, name: str) -> bool: return name in self.encoders
    def has_filter(self, name: str) -> bool: return name in self.filters


@dataclass(frozen=True, slots=True)
class FFmpegProgress:
    frame: int = 0
    out_time_ms: int = 0
    speed: float = 0.0
    progress: str = "continue"


class FFmpegProcessError(RuntimeError):
    def __init__(self, message: str, *, returncode: int = -1, stderr_tail: str = "") -> None:
        super().__init__(message); self.returncode=returncode; self.stderr_tail=stderr_tail


class FFmpegRunner:
    def __init__(self, ffmpeg_path: str | Path) -> None:
        self.ffmpeg_path=str(ffmpeg_path)
        self._active: subprocess.Popen[str] | None=None
        self._lock=threading.Lock()

    def discover_capabilities(self) -> FFmpegCapabilities:
        version_run=subprocess.run([self.ffmpeg_path,"-version"],capture_output=True,text=True,check=False,shell=False,timeout=10)
        first=(version_run.stdout or version_run.stderr or "").splitlines()
        first_line=first[0] if first else ""
        match=re.search(r"ffmpeg version\s+([^\s]+)",first_line,re.I); version=match.group(1) if match else first_line[:80]
        enc=subprocess.run([self.ffmpeg_path,"-hide_banner","-encoders"],capture_output=True,text=True,check=False,shell=False,timeout=15)
        encoders=set()
        for line in (enc.stdout or "").splitlines():
            m=re.match(r"^\s*[A-Z\.]{6}\s+([\w-]+)\s+",line)
            if m: encoders.add(m.group(1))
        fil=subprocess.run([self.ffmpeg_path,"-hide_banner","-filters"],capture_output=True,text=True,check=False,shell=False,timeout=15)
        filters=set()
        for line in (fil.stdout or "").splitlines():
            m=re.match(r"^\s*[\.A-Z]{3}\s+([\w-]+)\s+",line)
            if m: filters.add(m.group(1))
        return FFmpegCapabilities(version,frozenset(encoders),frozenset(filters))

    def validate_encoder(self, encoder: str) -> bool:
        cmd=[self.ffmpeg_path,"-hide_banner","-loglevel","error","-f","lavfi","-i","color=c=black:s=64x64:r=10:d=0.15","-frames:v","1","-c:v",encoder,"-f","null","-"]
        try:
            done=subprocess.run(cmd,capture_output=True,text=True,check=False,shell=False,timeout=15)
            return done.returncode==0
        except (OSError,subprocess.SubprocessError):
            return False

    def run(
        self,
        args: list[str],
        *,
        expected_duration_ms: int=0,
        cancellation: CancellationToken|None=None,
        progress_callback: Callable[[FFmpegProgress,float],None]|None=None,
    ) -> None:
        cmd=[self.ffmpeg_path,"-hide_banner","-y",*args]
        if "-progress" not in args:
            # Machine-readable progress is emitted on stdout; diagnostics stay on stderr.
            cmd[3:3]=["-progress","pipe:1","-nostats"]
        process=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1,shell=False)
        with self._lock: self._active=process
        stderr_lines:list[str]=[]
        def read_err() -> None:
            assert process.stderr is not None
            for line in process.stderr:
                stderr_lines.append(line.rstrip())
                if len(stderr_lines)>120: del stderr_lines[:40]
        err_thread=threading.Thread(target=read_err,daemon=True); err_thread.start()
        values:dict[str,str]={}
        try:
            assert process.stdout is not None
            for raw in process.stdout:
                if cancellation and cancellation.is_cancelled:
                    self._stop_process(process)
                    raise FFmpegProcessError("Render cancelled.",returncode=-15,stderr_tail="\n".join(stderr_lines[-20:]))
                line=raw.strip()
                if "=" not in line: continue
                key,value=line.split("=",1); values[key]=value
                if key=="progress":
                    info=self._progress(values)
                    fraction=min(1.0,max(0.0,info.out_time_ms/max(1,expected_duration_ms))) if expected_duration_ms else 0.0
                    if progress_callback: progress_callback(info,fraction)
                    values={}
            code=process.wait(); err_thread.join(timeout=1)
            if cancellation and cancellation.is_cancelled:
                raise FFmpegProcessError("Render cancelled.",returncode=code,stderr_tail="\n".join(stderr_lines[-20:]))
            if code!=0:
                raise FFmpegProcessError("FFmpeg process failed.",returncode=code,stderr_tail="\n".join(stderr_lines[-30:]))
        finally:
            with self._lock:
                if self._active is process: self._active=None

    def cancel_active(self) -> None:
        with self._lock: process=self._active
        if process is not None: self._stop_process(process)

    @staticmethod
    def _stop_process(process: subprocess.Popen[str]) -> None:
        if process.poll() is not None: return
        try:
            process.terminate(); process.wait(timeout=3)
        except Exception:
            try: process.kill(); process.wait(timeout=2)
            except Exception: pass

    @staticmethod
    def _progress(values: dict[str,str]) -> FFmpegProgress:
        frame=int(values.get("frame","0") or 0)
        raw_us = values.get("out_time_us") or values.get("out_time_ms")
        if raw_us and raw_us not in {"N/A", "NA", "-"}:
            # FFmpeg's historic out_time_ms key is actually microseconds; newer builds may also emit out_time_us.
            try:
                out_ms = max(0, int(int(raw_us) / 1000))
            except (TypeError, ValueError):
                out_ms = _timestamp_to_ms(values.get("out_time", "00:00:00.000000"))
        else:
            out_ms = _timestamp_to_ms(values.get("out_time", "00:00:00.000000"))
        speed_raw=values.get("speed","0x").rstrip("x")
        try: speed=float(speed_raw or 0)
        except ValueError: speed=0.0
        return FFmpegProgress(frame,out_ms,speed,values.get("progress","continue"))


def _timestamp_to_ms(value: str) -> int:
    try:
        hh,mm,ss=value.split(":",2); return round((int(hh)*3600+int(mm)*60+float(ss))*1000)
    except Exception:
        return 0
