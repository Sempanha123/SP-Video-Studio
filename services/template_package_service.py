from __future__ import annotations

import json
import os
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from uuid import uuid4

from domain.template import Template
from domain.template_asset import TemplateAsset
from domain.template_errors import TemplateChecksumError, TemplatePackageError, TemplatePackageUnsafe, TemplateVersionTooNew
from domain.template_manifest import TEMPLATE_SCHEMA_VERSION, TemplateManifest
from services.archive_security_service import (
    DEFAULT_TEMPLATE_LIMITS,
    UnsafeArchive,
    extract_member_limited,
    is_sensitive_template_asset,
    read_member_limited,
    sha256_bytes,
    validate_zip_layout,
)
from services.safe_path_service import UnsafeManagedPath, safe_copy_destination, safe_delete
from services.template_schema_migrator import TemplateSchemaMigrator
from services.template_validation_service import TemplateValidationService

MAX_PACKAGE_BYTES = DEFAULT_TEMPLATE_LIMITS.max_archive_bytes
MAX_MEMBER_BYTES = DEFAULT_TEMPLATE_LIMITS.max_member_bytes
MAX_MEMBERS = DEFAULT_TEMPLATE_LIMITS.max_members
MAX_UNCOMPRESSED_BYTES = DEFAULT_TEMPLATE_LIMITS.max_uncompressed_bytes
MAX_COMPRESSION_RATIO = DEFAULT_TEMPLATE_LIMITS.max_compression_ratio


def _sha256(data: bytes) -> str:
    return sha256_bytes(data)


class TemplatePackageService:
    """Portable .mmovtemplate packages with pre-extraction hostile-ZIP checks."""

    def __init__(
        self,
        validation: TemplateValidationService,
        migrator: TemplateSchemaMigrator | None = None,
        filename_service=None,
        *,
        security_events=None,
    ) -> None:
        self.validation = validation
        self.migrator = migrator or TemplateSchemaMigrator()
        self.filename_service = filename_service
        self.security_events = security_events

    def export(self, item: Template, destination: Path, *, asset_root: Path | None = None) -> Path:
        self.validation.validate(item)
        destination = Path(destination)
        if destination.suffix.lower() != ".mmovtemplate":
            destination = destination.with_suffix(".mmovtemplate")
        destination.parent.mkdir(parents=True, exist_ok=True)
        package_data = item.to_dict()
        package_data.pop("manifestPath", None)
        preview_source = None
        checksums: dict[str, str] = {}
        if item.preview_image:
            candidate = Path(item.preview_image)
            if not candidate.is_absolute() and item.manifest_path:
                candidate = Path(item.manifest_path).parent / candidate
            if candidate.is_file() and candidate.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                preview_source = candidate
                package_data["previewImage"] = "preview" + candidate.suffix.lower()
            else:
                package_data["previewImage"] = ""
        template_bytes = json.dumps(package_data, ensure_ascii=False, indent=2).encode("utf-8")
        checksums["template.json"] = _sha256(template_bytes)
        payload_assets: list[TemplateAsset] = []
        asset_root = Path(asset_root) if asset_root else None
        asset_bytes: dict[str, bytes] = {}
        for asset in item.assets:
            asset.validate()
            if is_sensitive_template_asset(asset.asset_type, asset.metadata):
                self._security("template_rejected", reason="sensitive_reference_asset")
                raise TemplatePackageUnsafe("Sensitive reference voice/audio cannot be exported in a template package.")
            path = (asset_root / asset.relative_path) if asset_root else None
            if path is None or not path.is_file():
                if asset.optional:
                    continue
                raise TemplatePackageError(f"Template asset is missing: {asset.relative_path}")
            data = path.read_bytes()
            if len(data) > MAX_MEMBER_BYTES:
                raise TemplatePackageError("Template asset is too large.")
            digest = _sha256(data)
            if asset.sha256 and digest.lower() != asset.sha256.lower():
                self._security("checksum_failure", scope="template_export")
                raise TemplateChecksumError(f"Asset checksum changed: {asset.relative_path}")
            arc = f"assets/{PurePosixPath(asset.relative_path).as_posix()}"
            checksums[arc] = digest
            asset_bytes[arc] = data
            payload_assets.append(TemplateAsset(PurePosixPath(asset.relative_path).as_posix(), digest, len(data), asset.asset_type, asset.optional, dict(asset.metadata)))
        preview_bytes = None
        preview_name = ""
        if preview_source is not None:
            preview_bytes = preview_source.read_bytes()
            if len(preview_bytes) <= MAX_MEMBER_BYTES:
                preview_name = f"preview{preview_source.suffix.lower()}"
                checksums[preview_name] = _sha256(preview_bytes)
            else:
                preview_bytes = None
        manifest = item.manifest()
        manifest.assets = payload_assets
        manifest.checksums = checksums
        manifest_bytes = json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2).encode("utf-8")
        temp = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
        try:
            with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("manifest.json", manifest_bytes)
                archive.writestr("template.json", template_bytes)
                if preview_bytes is not None and preview_name:
                    archive.writestr(preview_name, preview_bytes)
                for arc, data in asset_bytes.items():
                    archive.writestr(arc, data)
            if temp.stat().st_size > MAX_PACKAGE_BYTES:
                raise TemplatePackageError("Template package is too large.")
            os.replace(temp, destination)
            return destination
        finally:
            temp.unlink(missing_ok=True)

    def inspect(self, package: Path) -> tuple[TemplateManifest, Template]:
        package = Path(package)
        if not package.is_file():
            raise TemplatePackageError("Template package could not be found.")
        if package.suffix.lower() != ".mmovtemplate":
            raise TemplatePackageError("Template package must use the .mmovtemplate extension.")
        if package.stat().st_size > MAX_PACKAGE_BYTES:
            raise TemplatePackageError("Template package is too large.")
        try:
            with zipfile.ZipFile(package, "r") as archive:
                names = validate_zip_layout(
                    archive,
                    allowed_roots=("manifest.json", "template.json", "assets", "docs", "preview.png", "preview.jpg", "preview.jpeg", "preview.webp"),
                )
                if "manifest.json" not in names or "template.json" not in names:
                    raise TemplatePackageError("Template package is missing manifest.json or template.json.")
                manifest = self._parse_manifest(read_member_limited(archive, "manifest.json"))
                if manifest.schema_version > TEMPLATE_SCHEMA_VERSION:
                    raise TemplateVersionTooNew()
                template_raw = self._parse_json_object(read_member_limited(archive, "template.json"), "template.json")
                template_raw = self.migrator.migrate(template_raw)
                item = Template.from_dict(template_raw, builtin=False)
                if item.id != manifest.template_id:
                    raise TemplatePackageError("Template ID does not match its manifest.")
                signed = set(manifest.checksums)
                # Preserve compatibility with older cosmetic preview images while
                # requiring integrity coverage for every semantic template/docs/asset payload.
                for name in names:
                    if not name or name == "manifest.json" or name.endswith("/"):
                        continue
                    requires_checksum = name == "template.json" or name.startswith("assets/") or name.startswith("docs/")
                    if requires_checksum and name not in signed:
                        raise TemplateChecksumError(f"Package payload is not checksummed: {name}")
                for name, expected in manifest.checksums.items():
                    if name not in names:
                        raise TemplateChecksumError(f"Checksum target is missing: {name}")
                    actual = _sha256(read_member_limited(archive, name))
                    if actual.lower() != str(expected).lower():
                        self._security("checksum_failure", scope="template_import")
                        raise TemplateChecksumError(f"Checksum verification failed: {name}")
                self.validation.validate(item)
                return manifest, item
        except (zipfile.BadZipFile, UnsafeArchive, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            if isinstance(exc, (TemplatePackageError, TemplatePackageUnsafe, TemplateChecksumError, TemplateVersionTooNew)):
                raise
            self._security("template_rejected", reason=type(exc).__name__)
            if isinstance(exc, UnsafeArchive):
                raise TemplatePackageUnsafe(str(exc)) from exc
            raise TemplatePackageError("Template package is malformed or unsafe.") from exc

    def import_package(
        self,
        package: Path,
        user_root: Path,
        *,
        conflict: str = "keep_both",
        existing_ids: set[str] | None = None,
        builtin_ids: set[str] | None = None,
    ) -> tuple[Template, Path]:
        manifest, item = self.inspect(package)
        existing_ids = existing_ids or set()
        builtin_ids = builtin_ids or set()
        root = Path(user_root).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        if item.id in builtin_ids:
            raise TemplatePackageError("Imported templates cannot overwrite a built-in template.")
        if item.id in existing_ids:
            if conflict == "cancel":
                raise TemplatePackageError("Template import cancelled because the ID already exists.")
            if conflict == "keep_both":
                item.template_id = str(uuid4())
                item.name = f"{item.name} Copy"
            elif conflict != "replace":
                raise TemplatePackageError("Unsupported template conflict policy.")
        try:
            target = safe_copy_destination(root, item.id)
            staging = safe_copy_destination(root, f".import-{uuid4().hex}")
        except UnsafeManagedPath as exc:
            self._security("unsafe_path_blocked", scope="template_import")
            raise TemplatePackageUnsafe("Template destination is unsafe.") from exc
        backup: Path | None = None
        staging.mkdir(parents=False, exist_ok=False)
        try:
            actual_total = 0
            with zipfile.ZipFile(package, "r") as archive:
                validate_zip_layout(
                    archive,
                    allowed_roots=("manifest.json", "template.json", "assets", "docs", "preview.png", "preview.jpg", "preview.jpeg", "preview.webp"),
                )
                for info in archive.infolist():
                    if info.is_dir():
                        continue
                    _, written = extract_member_limited(archive, info, staging)
                    actual_total += written
                    if actual_total > MAX_UNCOMPRESSED_BYTES:
                        raise TemplatePackageUnsafe("Template package expanded beyond the safe streaming limit.")
            rewritten = json.dumps(item.to_dict(), ensure_ascii=False, indent=2).encode("utf-8")
            (staging / "template.json").write_bytes(rewritten)
            local_manifest = item.manifest()
            local_manifest.assets = list(manifest.assets)
            local_manifest.checksums = dict(manifest.checksums)
            local_manifest.checksums["template.json"] = _sha256(rewritten)
            (staging / "manifest.json").write_text(json.dumps(local_manifest.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
            if conflict == "replace" and target.exists():
                backup = safe_copy_destination(root, f".replace-backup-{uuid4().hex}")
                os.replace(target, backup)
            try:
                os.replace(staging, target)
            except Exception:
                if backup is not None and backup.exists() and not target.exists():
                    os.replace(backup, target)
                raise
            if backup is not None:
                safe_delete(backup, root, recursive=True)
            item.manifest_path = str(target / "manifest.json")
            return item, target
        except UnsafeArchive as exc:
            self._security("template_rejected", reason="archive_limit")
            raise TemplatePackageUnsafe(str(exc)) from exc
        finally:
            if staging.exists():
                try:
                    safe_delete(staging, root, recursive=True)
                except Exception:
                    pass
            if backup is not None and backup.exists() and target.exists():
                try:
                    safe_delete(backup, root, recursive=True)
                except Exception:
                    pass

    @staticmethod
    def _parse_json_object(data: bytes, label: str) -> dict:
        try:
            raw = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TemplatePackageError(f"{label} is invalid JSON.") from exc
        if not isinstance(raw, dict):
            raise TemplatePackageError(f"{label} must contain a JSON object.")
        return raw

    def _parse_manifest(self, data: bytes) -> TemplateManifest:
        return TemplateManifest.from_dict(self._parse_json_object(data, "manifest.json"))

    def _security(self, event: str, **metadata) -> None:
        if self.security_events is not None:
            try:
                self.security_events.record(event, **metadata)
            except Exception:
                pass
