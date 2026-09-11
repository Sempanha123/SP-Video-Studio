from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from domain.ai_model import AIModel
from domain.model_installation import MODEL_MANIFEST_SCHEMA_VERSION


@dataclass(slots=True)
class VerificationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    checked_files: int = 0


class ModelVerificationService:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("sp_video_studio.models.verify")

    def verify(self, model: AIModel, install_path: Path) -> VerificationResult:
        if not install_path.is_dir():
            return VerificationResult(False, ["Model directory is missing."])
        manifest_path = install_path / "model_manifest.json"
        if not manifest_path.is_file():
            return VerificationResult(False, ["Model manifest is missing."])
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return VerificationResult(False, ["Model manifest is invalid."])
        if not isinstance(manifest, dict):
            return VerificationResult(False, ["Model manifest is invalid."])
        if manifest.get("model_id") != model.model_id:
            return VerificationResult(False, ["Model manifest belongs to another model."])
        if int(manifest.get("app_model_schema_version") or 0) != MODEL_MANIFEST_SCHEMA_VERSION:
            return VerificationResult(False, ["Model manifest version is unsupported."])
        file_entries = manifest.get("files")
        if not isinstance(file_entries, list):
            return VerificationResult(False, ["Model manifest file list is invalid."])

        errors: list[str] = []
        known_paths: set[str] = set()
        checked = 0
        for entry in file_entries:
            if not isinstance(entry, dict):
                errors.append("Model manifest contains an invalid file entry.")
                continue
            relative = str(entry.get("path") or "")
            try:
                file_path = _safe_manifest_file(install_path, relative)
            except ValueError:
                errors.append(f"Unsafe manifest path: {relative or '<empty>'}")
                continue
            known_paths.add(relative.replace("\\", "/"))
            if not file_path.is_file():
                errors.append(f"Missing file: {relative}")
                continue
            checked += 1
            actual_size = file_path.stat().st_size
            if actual_size <= 0:
                errors.append(f"Empty file: {relative}")
                continue
            expected_size = entry.get("size")
            if expected_size is not None and int(expected_size) != actual_size:
                errors.append(f"File size mismatch: {relative}")
                continue
            expected_sha = str(entry.get("sha256") or "").lower()
            if expected_sha:
                actual_sha = _sha256(file_path)
                if actual_sha != expected_sha:
                    errors.append(f"Hash mismatch: {relative}")

        for required in model.required_files:
            normalized = required.replace("\\", "/")
            if normalized not in known_paths or not (install_path / required).is_file():
                errors.append(f"Required file is missing: {required}")
        return VerificationResult(not errors, errors, checked)


def _safe_manifest_file(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if not relative or candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        raise ValueError("Unsafe model manifest path")
    root_resolved = root.resolve()
    target = (root / candidate).resolve()
    if target == root_resolved or root_resolved not in target.parents:
        raise ValueError("Model manifest path escapes installation root")
    return target


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
