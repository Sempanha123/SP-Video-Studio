from __future__ import annotations
import json, os, tempfile
from pathlib import Path
from typing import Any, Callable


def _sync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    try:
        fd=os.open(str(path), os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)
    except OSError:
        pass


def atomic_write_bytes(path: str|Path, data: bytes, *, replace: Callable[[str,str],None]=os.replace) -> Path:
    target=Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=f".{target.name}.",suffix=".tmp",dir=target.parent)
    tmp_path=Path(tmp)
    try:
        with os.fdopen(fd,"wb",closefd=True) as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno())
        replace(str(tmp_path),str(target)); _sync_directory(target.parent); return target
    except Exception:
        try: tmp_path.unlink(missing_ok=True)
        except OSError: pass
        raise


def atomic_write_text(path: str|Path, text: str, *, encoding="utf-8", replace=os.replace) -> Path:
    return atomic_write_bytes(path, text.encode(encoding), replace=replace)


def atomic_write_json(path: str|Path, value: Any, *, replace=os.replace) -> Path:
    text=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"))
    return atomic_write_text(path,text,replace=replace)
