from __future__ import annotations

import hashlib
import stat
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import BinaryIO, Iterable

from services.safe_path_service import UnsafeManagedPath, safe_copy_destination


class UnsafeArchive(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ArchiveLimits:
    max_archive_bytes: int = 256 * 1024 * 1024
    max_member_bytes: int = 96 * 1024 * 1024
    max_members: int = 512
    max_uncompressed_bytes: int = 512 * 1024 * 1024
    max_compression_ratio: float = 200.0


DEFAULT_TEMPLATE_LIMITS = ArchiveLimits()
EXECUTABLE_EXTENSIONS = frozenset({
    ".exe", ".bat", ".ps1", ".cmd", ".js", ".py", ".pyc", ".pyo", ".com",
    ".scr", ".msi", ".dll", ".sh", ".vbs", ".vbe", ".wsf", ".jar", ".lnk",
    ".hta", ".html", ".htm", ".xhtml", ".svg", ".reg", ".sct",
})


def safe_archive_name(name: str) -> str:
    normalized = str(name or "").replace("\\", "/")
    if normalized.endswith("/"):
        normalized = normalized.rstrip("/")
    if not normalized:
        return ""
    path = PurePosixPath(normalized)
    if normalized.startswith("/") or path.is_absolute():
        raise UnsafeArchive("Archive contains an absolute path.")
    if ":" in path.parts[0] or any(part in {"", ".", ".."} for part in path.parts):
        raise UnsafeArchive("Archive contains an unsafe path.")
    if _looks_windows_absolute(normalized):
        raise UnsafeArchive("Archive contains an absolute Windows path.")
    return path.as_posix()


def _looks_windows_absolute(value: str) -> bool:
    text = value.replace("/", "\\")
    return text.startswith("\\\\") or text.startswith("\\?\\") or (
        len(text) >= 2 and text[0].isalpha() and text[1] == ":"
    )


def validate_zip_info(info: zipfile.ZipInfo, limits: ArchiveLimits = DEFAULT_TEMPLATE_LIMITS) -> str:
    name = safe_archive_name(info.filename)
    if info.flag_bits & 0x1:
        raise UnsafeArchive("Encrypted archive members are not supported.")
    mode = (int(info.external_attr) >> 16) & 0xFFFF
    if mode:
        if stat.S_ISLNK(mode):
            raise UnsafeArchive("Archive contains a symbolic link.")
        # Reject unusual Unix special files; zero mode and normal files/dirs remain valid.
        kind = stat.S_IFMT(mode)
        if kind and not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            raise UnsafeArchive("Archive contains a special filesystem entry.")
    if name and PurePosixPath(name).suffix.lower() in EXECUTABLE_EXTENSIONS:
        raise UnsafeArchive("Archive contains executable or script content.")
    if int(info.file_size) < 0 or int(info.file_size) > limits.max_member_bytes:
        raise UnsafeArchive("Archive member exceeds the safe size limit.")
    compressed = int(info.compress_size)
    uncompressed = int(info.file_size)
    if uncompressed >= 1024 * 1024:
        if compressed <= 0:
            raise UnsafeArchive("Archive member has a suspicious compression ratio.")
        if (uncompressed / compressed) > limits.max_compression_ratio:
            raise UnsafeArchive("Archive member has a suspicious compression ratio.")
    return name


def validate_zip_layout(
    archive: zipfile.ZipFile,
    *,
    limits: ArchiveLimits = DEFAULT_TEMPLATE_LIMITS,
    allowed_roots: Iterable[str] | None = None,
) -> list[str]:
    infos = archive.infolist()
    if len(infos) > limits.max_members:
        raise UnsafeArchive("Archive contains too many files.")
    if sum(max(0, int(info.file_size)) for info in infos) > limits.max_uncompressed_bytes:
        raise UnsafeArchive("Archive expands beyond the safe size limit.")
    names: list[str] = []
    for info in infos:
        name = validate_zip_info(info, limits)
        names.append(name)
        if name and allowed_roots:
            ok = any(name == root or name.startswith(root.rstrip("/") + "/") for root in allowed_roots)
            if not ok:
                raise UnsafeArchive(f"Unexpected archive entry: {name}")
    if len(names) != len(set(names)):
        raise UnsafeArchive("Archive contains duplicate file entries.")
    return names


def read_member_limited(
    archive: zipfile.ZipFile,
    info_or_name: zipfile.ZipInfo | str,
    *,
    limits: ArchiveLimits = DEFAULT_TEMPLATE_LIMITS,
) -> bytes:
    info = archive.getinfo(info_or_name) if isinstance(info_or_name, str) else info_or_name
    validate_zip_info(info, limits)
    chunks: list[bytes] = []
    actual = 0
    with archive.open(info, "r") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            actual += len(chunk)
            if actual > limits.max_member_bytes:
                raise UnsafeArchive("Archive member exceeds the safe streaming limit.")
            chunks.append(chunk)
    if actual != int(info.file_size):
        raise UnsafeArchive("Archive member size did not match its metadata.")
    return b"".join(chunks)


def extract_member_limited(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    destination_root,
    *,
    limits: ArchiveLimits = DEFAULT_TEMPLATE_LIMITS,
) -> tuple[object, int]:
    name = validate_zip_info(info, limits)
    if not name or info.is_dir():
        return destination_root, 0
    try:
        target = safe_copy_destination(destination_root, name)
    except UnsafeManagedPath as exc:
        raise UnsafeArchive("Archive extraction path is unsafe.") from exc
    target.parent.mkdir(parents=True, exist_ok=True)
    actual = 0
    with archive.open(info, "r") as source, target.open("xb") as output:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            actual += len(chunk)
            if actual > limits.max_member_bytes:
                raise UnsafeArchive("Archive member exceeds the safe streaming limit.")
            output.write(chunk)
    if actual != int(info.file_size):
        target.unlink(missing_ok=True)
        raise UnsafeArchive("Archive member size did not match its metadata.")
    return target, actual


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_sha256(data: bytes, expected: str) -> bool:
    text = str(expected or "").strip().lower()
    return len(text) == 64 and hashlib.sha256(data).hexdigest() == text


def is_sensitive_template_asset(asset_type: str, metadata: dict | None = None) -> bool:
    code = str(asset_type or "").strip().lower().replace("-", "_")
    meta = {str(k).lower().replace("-", "_"): v for k, v in dict(metadata or {}).items()}
    if code in {"reference_voice", "voice_reference", "reference_audio", "voice_sample_private"}:
        return True
    return any(bool(meta.get(key)) for key in ("reference_voice", "referencevoice", "sensitive", "private", "biometric_like"))
