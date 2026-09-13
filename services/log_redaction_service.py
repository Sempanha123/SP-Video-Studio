from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


_REDACTED = "[REDACTED]"
_SENSITIVE_KEY = re.compile(
    r"^(authorization|proxy-authorization|x[-_]?api[-_]?key|api[-_]?key|apikey|key|access[-_]?key|secret[-_]?key|private[-_]?key|password|passwd|cookie|set-cookie|"
    r"session(?:[-_]?token)?|token|access[-_]?token|refresh[-_]?token|auth[-_]?token|secret|client[-_]?secret)$",
    re.IGNORECASE,
)


class LogRedactionService:
    """Defense-in-depth sanitizer for diagnostics and local support artifacts."""

    def __init__(self, home: str | Path | None = None) -> None:
        self.home = Path(home).expanduser() if home else Path.home()
        self._patterns = (
            re.compile(r"(?im)((?:Authorization|Proxy-Authorization|X-Auth-Token)\s*:\s*)(?:Bearer\s+)?[^\s,;]+"),
            re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+\-/=]+"),
            re.compile(
                r"(?i)(\b(?:x[-_]?api[-_]?key|api[-_]?key|apikey|access[-_]?key|secret[-_]?key|private[-_]?key|password|passwd|client[-_]?secret|"
                r"access[-_]?token|refresh[-_]?token|session[-_]?token|auth[-_]?token|credential|signature|secret)\b"
                r"\s*[=:]\s*)([^\s,;&]+|\"[^\"]*\"|'[^']*')"
            ),
            re.compile(
                r'(?i)("(?:api[-_]?key|password|token|secret|cookie|authorization)"\s*:\s*)"[^"]*"'
            ),
            re.compile(r"(?i)(\b(?:Cookie|Set-Cookie)\s*:\s*)[^\r\n]+"),
        )

    def redact_text(self, text: str) -> str:
        value = str(text or "")
        value = self.sanitize_paths(value)
        value = self._redact_urls_in_text(value)
        for index, pattern in enumerate(self._patterns):
            if index == 1:
                value = pattern.sub("Bearer " + _REDACTED, value)
            else:
                value = pattern.sub(lambda m: m.group(1) + _REDACTED, value)
        return value

    def redact_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            result: dict[str, Any] = {}
            for key, item in value.items():
                key_text = str(key)
                result[key_text] = _REDACTED if _SENSITIVE_KEY.match(key_text) else self.redact_value(item)
            return result
        if isinstance(value, list):
            return [self.redact_value(item) for item in value]
        if isinstance(value, tuple):
            return [self.redact_value(item) for item in value]
        if isinstance(value, Path):
            return self.sanitize_paths(str(value))
        if isinstance(value, str):
            return self.redact_text(value)
        return value

    def sanitize_paths(self, text: str) -> str:
        value = str(text or "")
        home = str(self.home)
        if home:
            value = value.replace(home, "%USERPROFILE%" if re.match(r"^[A-Za-z]:", home) else "$HOME")
            value = value.replace(home.replace("\\", "/"), "%USERPROFILE%" if re.match(r"^[A-Za-z]:", home) else "$HOME")
        value = re.sub(r"(?i)\b[A-Z]:\\Users\\[^\\\s]+", r"%USERPROFILE%", value)
        value = re.sub(r"(?i)\b[A-Z]:/Users/[^/\s]+", r"%USERPROFILE%", value)
        value = re.sub(r"(?<![\w])/(?:home|Users)/[^/\s]+", "$HOME", value)
        return value

    def sanitize_url(self, url: str) -> str:
        try:
            parts = urlsplit(url)
            if not parts.scheme or not parts.netloc:
                return self.redact_text(url)
            safe_query = []
            for key, value in parse_qsl(parts.query, keep_blank_values=True):
                safe_query.append((key, _REDACTED if _SENSITIVE_KEY.match(key) else value))
            return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(safe_query), ""))
        except Exception:
            return self.redact_text(url)

    def _redact_urls_in_text(self, text: str) -> str:
        url_pattern = re.compile(r"https?://[^\s<>\"]+", re.IGNORECASE)
        return url_pattern.sub(lambda m: self.sanitize_url(m.group(0)), text)
