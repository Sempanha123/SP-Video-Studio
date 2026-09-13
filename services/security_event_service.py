from __future__ import annotations

import json
import logging
from typing import Any

from services.log_redaction_service import LogRedactionService


class SecurityEventService:
    """Small safe-event logger. It records event type and redacted metadata, never secrets."""

    ALLOWED_EVENTS = frozenset({
        "template_rejected", "unsafe_path_blocked", "ssrf_blocked",
        "checksum_failure", "secret_redaction_error", "model_download_rejected",
    })

    def __init__(self, logger: logging.Logger | None = None, redaction: LogRedactionService | None = None) -> None:
        self.logger = logger or logging.getLogger("sp_video_studio.security")
        self.redaction = redaction or LogRedactionService()

    def record(self, event: str, **metadata: Any) -> None:
        code = str(event or "").strip().lower()
        if code not in self.ALLOWED_EVENTS:
            code = "unsafe_path_blocked"
        try:
            safe = self.redaction.redact_value(metadata)
            text = json.dumps(safe, ensure_ascii=False, sort_keys=True, default=str)
            self.logger.warning("Security event: %s %s", code, text[:1200])
        except Exception:
            # Never fall back to raw metadata when redaction itself fails.
            self.logger.warning("Security event: secret_redaction_error metadata=[REDACTED]")
