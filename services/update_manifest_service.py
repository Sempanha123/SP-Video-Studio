from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.constants import APP_VERSION
from domain.update_manifest import UpdateManifest, UpdateManifestError


class UpdateCheckError(RuntimeError):
    pass


class _SafeRedirectHandler(HTTPRedirectHandler):
    def __init__(self, allow_local_http: bool = False) -> None:
        super().__init__()
        self.allow_local_http = allow_local_http

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        old_scheme = urlparse(req.full_url).scheme.lower()
        parsed = urlparse(newurl)
        host = (parsed.hostname or "").lower()
        local = self.allow_local_http and parsed.scheme == "http" and host in {"127.0.0.1", "localhost", "::1"}
        if parsed.scheme != "https" and not local:
            raise UpdateCheckError("Update redirect was rejected because it is not HTTPS")
        if old_scheme == "https" and parsed.scheme != "https":
            raise UpdateCheckError("HTTPS update redirect downgrade was rejected")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def validate_source_url(url: str, *, allow_local_http: bool = False) -> str:
    parsed = urlparse(str(url or "").strip())
    host = (parsed.hostname or "").lower()
    local = allow_local_http and parsed.scheme == "http" and host in {"127.0.0.1", "localhost", "::1"}
    if parsed.scheme != "https" and not local:
        raise UpdateCheckError("Update source must use HTTPS")
    if not parsed.netloc or parsed.username or parsed.password:
        raise UpdateCheckError("Update source URL is invalid")
    return parsed.geturl()


class UpdateManifestService:
    def __init__(self, manifest_url: str, *, timeout: float = 12.0, max_bytes: int = 256 * 1024, allow_test_http: bool = False) -> None:
        self.manifest_url = str(manifest_url or "").strip()
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.allow_test_http = allow_test_http
        self._opener = build_opener(_SafeRedirectHandler(allow_test_http))

    def fetch(self) -> UpdateManifest:
        if not self.manifest_url:
            raise UpdateCheckError("Update service is not configured for this build")
        url = validate_source_url(self.manifest_url, allow_local_http=self.allow_test_http)
        request = Request(url, headers={"Accept": "application/json", "User-Agent": f"MMO-Video-Studio/{APP_VERSION}"}, method="GET")
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                final_url = validate_source_url(response.geturl(), allow_local_http=self.allow_test_http)
                if urlparse(url).scheme == "https" and urlparse(final_url).scheme != "https":
                    raise UpdateCheckError("HTTPS update redirect downgrade was rejected")
                raw = response.read(self.max_bytes + 1)
        except UpdateCheckError:
            raise
        except (HTTPError, URLError, OSError) as exc:
            raise UpdateCheckError("Could not check for updates.") from exc
        if len(raw) > self.max_bytes:
            raise UpdateCheckError("Update manifest is too large")
        try:
            payload = json.loads(raw.decode("utf-8"))
            return UpdateManifest.from_dict(payload, allow_local_http=self.allow_test_http)
        except (UnicodeDecodeError, json.JSONDecodeError, UpdateManifestError) as exc:
            raise UpdateCheckError(str(exc)) from exc
