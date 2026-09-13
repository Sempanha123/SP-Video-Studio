from __future__ import annotations

import os
import shutil
import stat
from dataclasses import dataclass
from pathlib import Path


class UnsafeManagedPath(ValueError):
    """Raised when an app-owned filesystem operation would escape its managed root."""


_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL", "CLOCK$",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


@dataclass(frozen=True, slots=True)
class ManagedRoot:
    path: Path
    category: str = "managed"

    def canonical(self) -> Path:
        return canonicalize_path(self.path)


def canonicalize_path(path: str | Path, *, strict: bool = False) -> Path:
    """Return a canonical absolute path while rejecting NUL-like input.

    Pathlib/Win32 APIs handle long paths where the host supports them. No manual
    MAX_PATH truncation is performed because truncating can change containment.
    """
    raw = str(path)
    if "\x00" in raw:
        raise UnsafeManagedPath("Path contains an invalid NUL character.")
    try:
        return Path(raw).expanduser().resolve(strict=strict)
    except (OSError, RuntimeError, ValueError) as exc:
        raise UnsafeManagedPath("Path could not be canonicalized safely.") from exc


def _norm(value: Path) -> str:
    text = os.path.normpath(str(value))
    return os.path.normcase(text) if os.name == "nt" else text


def is_within_managed_root(path: str | Path, root: str | Path, *, allow_root: bool = False) -> bool:
    try:
        target = canonicalize_path(path)
        base = canonicalize_path(root)
    except UnsafeManagedPath:
        return False
    target_text = _norm(target)
    base_text = _norm(base)
    if target_text == base_text:
        return bool(allow_root)
    try:
        common = os.path.commonpath([base_text, target_text])
    except ValueError:
        return False
    return common == base_text


def _looks_windows_absolute_or_unc(value: str) -> bool:
    text = value.replace("/", "\\")
    if text.startswith("\\\\") or text.startswith("\\?\\") or text.startswith("\\.\\"):
        return True
    return len(text) >= 2 and text[0].isalpha() and text[1] == ":"


def _validate_relative_component(part: str) -> None:
    if part in {"", ".", ".."}:
        raise UnsafeManagedPath("Path traversal is not allowed.")
    if "\x00" in part:
        raise UnsafeManagedPath("Path contains an invalid NUL character.")
    trimmed = part.rstrip(" .")
    if not trimmed:
        raise UnsafeManagedPath("Path contains an invalid Windows filename.")
    # Alternate data streams and drive-like segments are unsafe for managed names.
    if ":" in trimmed:
        raise UnsafeManagedPath("Colon/alternate data stream syntax is not allowed.")
    stem = trimmed.split(".", 1)[0].upper()
    if stem in _WINDOWS_RESERVED:
        raise UnsafeManagedPath("Windows reserved device names are not allowed.")


def safe_copy_destination(root: str | Path, relative: str | Path) -> Path:
    """Resolve a user-derived relative destination under a managed root."""
    raw = str(relative)
    if not raw or _looks_windows_absolute_or_unc(raw):
        raise UnsafeManagedPath("Absolute or UNC destinations are not allowed.")
    candidate = Path(raw)
    if candidate.is_absolute():
        raise UnsafeManagedPath("Absolute destinations are not allowed.")
    for part in candidate.parts:
        _validate_relative_component(str(part))
    base = canonicalize_path(root)
    target = canonicalize_path(base / candidate)
    if not is_within_managed_root(target, base):
        raise UnsafeManagedPath("Destination escapes the managed root.")
    return target


def is_reparse_or_symlink(path: str | Path) -> bool:
    item = Path(path)
    try:
        if item.is_symlink():
            return True
        attrs = int(getattr(item.lstat(), "st_file_attributes", 0) or 0)
        return bool(attrs & _REPARSE_POINT)
    except OSError:
        return False


def safe_delete(
    path: str | Path,
    managed_root: str | Path | ManagedRoot,
    *,
    recursive: bool = False,
    missing_ok: bool = True,
) -> bool:
    """Delete only a validated app-owned descendant; never follow links/junctions."""
    root = managed_root.path if isinstance(managed_root, ManagedRoot) else Path(managed_root)
    base = canonicalize_path(root)
    raw_target = Path(path).expanduser()
    if not raw_target.is_absolute():
        raw_target = base / raw_target
    # Check lexical location first so an outside symlink cannot be normalized away.
    lexical = Path(os.path.abspath(str(raw_target)))
    if not is_within_managed_root(lexical, base):
        raise UnsafeManagedPath("Refusing to delete outside the managed root.")
    if not raw_target.exists() and not raw_target.is_symlink():
        if missing_ok:
            return False
        raise FileNotFoundError(str(raw_target))
    if is_reparse_or_symlink(raw_target):
        raise UnsafeManagedPath("Refusing to delete a symlink or junction as managed content.")
    target = canonicalize_path(raw_target, strict=True)
    if not is_within_managed_root(target, base):
        raise UnsafeManagedPath("Resolved delete target escapes the managed root.")
    if target.is_dir():
        if not recursive:
            target.rmdir()
        else:
            shutil.rmtree(target)
    else:
        target.unlink()
    return True
