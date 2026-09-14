from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from urllib.parse import urlparse

SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$")
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
FORBIDDEN_FIELDS = {"command", "commands", "args", "arguments", "script", "executable", "powershell", "shell"}


class UpdateManifestError(ValueError):
    pass


@dataclass(frozen=True, order=False, slots=True)
class SemanticVersion:
    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...] = ()

    @classmethod
    def parse(cls, value: str) -> "SemanticVersion":
        text = str(value or "").strip()
        match = SEMVER_RE.fullmatch(text)
        if not match:
            raise UpdateManifestError(f"Invalid semantic version: {text!r}")
        pre = tuple((match.group(4) or "").split(".")) if match.group(4) else ()
        return cls(int(match.group(1)), int(match.group(2)), int(match.group(3)), pre)

    def _compare_prerelease(self, other: "SemanticVersion") -> int:
        if not self.prerelease and not other.prerelease:
            return 0
        if not self.prerelease:
            return 1
        if not other.prerelease:
            return -1
        for left, right in zip(self.prerelease, other.prerelease):
            if left == right:
                continue
            ln, rn = left.isdigit(), right.isdigit()
            if ln and rn:
                return -1 if int(left) < int(right) else 1
            if ln != rn:
                return -1 if ln else 1
            return -1 if left < right else 1
        if len(self.prerelease) == len(other.prerelease):
            return 0
        return -1 if len(self.prerelease) < len(other.prerelease) else 1

    def compare(self, other: "SemanticVersion") -> int:
        left = (self.major, self.minor, self.patch)
        right = (other.major, other.minor, other.patch)
        if left != right:
            return -1 if left < right else 1
        return self._compare_prerelease(other)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, SemanticVersion):
            return NotImplemented
        return self.compare(other) < 0

    def __eq__(self, other: object) -> bool:
        return isinstance(other, SemanticVersion) and self.compare(other) == 0

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        return base + ("-" + ".".join(self.prerelease) if self.prerelease else "")


def compare_versions(left: str, right: str) -> int:
    return SemanticVersion.parse(left).compare(SemanticVersion.parse(right))


def _safe_url(value: str, *, field: str, allow_local_http: bool = False) -> str:
    text = str(value or "").strip()
    parsed = urlparse(text)
    host = (parsed.hostname or "").lower()
    local_http = allow_local_http and parsed.scheme == "http" and host in {"127.0.0.1", "localhost", "::1"}
    if parsed.scheme != "https" and not local_http:
        raise UpdateManifestError(f"{field} must use HTTPS")
    if not parsed.netloc or parsed.username or parsed.password:
        raise UpdateManifestError(f"{field} is not a safe URL")
    return text


@dataclass(frozen=True, slots=True)
class UpdateManifest:
    schema_version: int
    channel: str
    version: str
    minimum_supported_version: str
    published_at: str
    installer_url: str
    installer_sha256: str
    installer_size: int
    release_notes: str = ""
    release_notes_url: str = ""
    signature_type: str = ""
    signature_signer: str = ""
    minimum_project_schema: int | None = None

    @classmethod
    def from_dict(
        cls,
        payload: object,
        *,
        supported_schema: int = 1,
        allow_local_http: bool = False,
    ) -> "UpdateManifest":
        if not isinstance(payload, dict):
            raise UpdateManifestError("Update manifest must be a JSON object")
        forbidden = FORBIDDEN_FIELDS.intersection({str(key).lower() for key in payload})
        if forbidden:
            raise UpdateManifestError("Update manifest contains forbidden executable fields")
        try:
            schema_version = int(payload["schema_version"])
            channel = str(payload["channel"]).strip().lower()
            version = str(payload["version"]).strip()
            minimum = str(payload.get("minimum_supported_version") or "0.0.0").strip()
            published = str(payload["published_at"]).strip()
            installer_url = _safe_url(str(payload["installer_url"]), field="installer_url", allow_local_http=allow_local_http)
            digest = str(payload["installer_sha256"]).strip().lower()
            size = int(payload["installer_size"])
        except UpdateManifestError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise UpdateManifestError("Update manifest is missing or has invalid required fields") from exc
        if schema_version != supported_schema:
            raise UpdateManifestError(f"Unsupported update manifest schema: {schema_version}")
        if channel != "stable":
            raise UpdateManifestError("Only the Stable update channel is supported")
        SemanticVersion.parse(version)
        SemanticVersion.parse(minimum)
        try:
            datetime.fromisoformat(published.replace("Z", "+00:00"))
        except ValueError as exc:
            raise UpdateManifestError("published_at must be an ISO-8601 timestamp") from exc
        if not SHA256_RE.fullmatch(digest):
            raise UpdateManifestError("installer_sha256 must be a SHA-256 hex digest")
        if size <= 0:
            raise UpdateManifestError("installer_size must be positive")
        notes = str(payload.get("release_notes") or "")
        if len(notes.encode("utf-8")) > 64 * 1024:
            raise UpdateManifestError("release_notes is too large")
        notes_url = str(payload.get("release_notes_url") or "").strip()
        if notes_url:
            notes_url = _safe_url(notes_url, field="release_notes_url", allow_local_http=allow_local_http)
        signature = payload.get("signature") or {}
        if not isinstance(signature, dict):
            raise UpdateManifestError("signature metadata must be an object")
        signature_type = str(signature.get("type") or "").strip().lower()
        signature_signer = str(signature.get("signer") or "").strip()
        if signature_type and signature_type != "authenticode":
            raise UpdateManifestError("Unsupported signature type")
        minimum_project_schema = payload.get("minimum_project_schema")
        if minimum_project_schema is not None:
            try:
                minimum_project_schema = int(minimum_project_schema)
            except (TypeError, ValueError) as exc:
                raise UpdateManifestError("minimum_project_schema must be an integer") from exc
            if minimum_project_schema < 1:
                raise UpdateManifestError("minimum_project_schema must be positive")
        return cls(
            schema_version,
            channel,
            version,
            minimum,
            published,
            installer_url,
            digest,
            size,
            notes,
            notes_url,
            signature_type,
            signature_signer,
            minimum_project_schema,
        )
