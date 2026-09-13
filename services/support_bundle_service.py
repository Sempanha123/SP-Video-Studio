from __future__ import annotations

import json
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from domain.diagnostic_result import DiagnosticResult
from domain.support_bundle import SupportBundle
from services.environment_report_service import EnvironmentReportService
from services.log_redaction_service import LogRedactionService


class SupportBundleError(RuntimeError):
    pass


class SupportBundleService:
    """Creates a local, allow-list-only support ZIP. Nothing is uploaded."""

    SAFE_FILES = (
        "manifest.json",
        "environment.json",
        "settings-summary.json",
        "diagnostics.json",
        "ffmpeg-summary.json",
        "model-status.json",
        "database-summary.json",
        "logs/recent.log",
    )
    EXCLUDED_LABELS = (
        "Projects and project databases",
        "Media, scripts, transcripts, subtitles and News sources",
        "Voice/reference recordings",
        "Recovery snapshots",
        "API keys, tokens, passwords, cookies and provider headers",
    )

    def __init__(
        self,
        paths,
        environment: EnvironmentReportService,
        diagnostics_service,
        redaction: LogRedactionService,
        *,
        logger=None,
    ) -> None:
        self.paths = paths
        self.environment = environment
        self.diagnostics = diagnostics_service
        self.redaction = redaction
        self.logger = logger

    def review(self) -> dict[str, list[str]]:
        return {
            "included": ["System information", "Diagnostic results", "FFmpeg/version/filter diagnostics when collected", "Recent sanitized logs", "Model status", "Database schema version"],
            "notIncluded": list(self.EXCLUDED_LABELS),
        }

    def create(
        self,
        results: Iterable[DiagnosticResult],
        *,
        destination_dir: str | Path | None = None,
        log_limit: int = 400,
    ) -> SupportBundle:
        now = datetime.now(timezone.utc)
        destination = Path(destination_dir) if destination_dir else Path(self.paths.root) / "support"
        destination.mkdir(parents=True, exist_ok=True)
        filename = f"MMOVideoStudio-support-{now.astimezone().strftime('%Y%m%d-%H%M%S')}.zip"
        target = destination / filename
        environment = self.environment.build()
        result_rows = [self.redaction.redact_value(item.to_dict(include_technical=True)) for item in results]
        logs = self.diagnostics.recent_logs("all", max(50, min(2000, int(log_limit))))
        log_text = "\n".join(f"[{row['severity'].upper()}] {row['message']}" for row in logs)
        documents = {
            "manifest.json": {
                "bundleFormat": 1,
                "createdAt": now.isoformat(),
                "privacy": "Local only. No automatic upload.",
                "includedFiles": list(self.SAFE_FILES),
                "excluded": list(self.EXCLUDED_LABELS),
            },
            "environment.json": environment.get("system", {}),
            "settings-summary.json": environment.get("settings", {}),
            "diagnostics.json": result_rows,
            "ffmpeg-summary.json": [row for row in result_rows if str(row.get("category", "")) == "FFmpeg"] or [{"status": "not_collected", "summary": "Run Full Diagnostics to collect filter/encoder smoke details."}],
            "model-status.json": environment.get("models", []),
            "database-summary.json": environment.get("database", {}),
        }
        with tempfile.TemporaryDirectory(prefix="mmo-video-support-") as temp_root:
            root = Path(temp_root)
            for relative, payload in documents.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                clean = self.redaction.redact_value(payload)
                path.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
            log_path = root / "logs" / "recent.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(self.redaction.redact_text(log_text), encoding="utf-8")
            self._privacy_gate(root)
            with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                for relative in self.SAFE_FILES:
                    source = root / relative
                    if source.is_file():
                        archive.write(source, arcname=relative)
        self._validate_zip(target)
        files = self.list_files(target)
        return SupportBundle(path=target, files=files, created_at=now.isoformat(), size_bytes=target.stat().st_size)

    @staticmethod
    def list_files(bundle_path: str | Path) -> list[str]:
        with zipfile.ZipFile(bundle_path, "r") as archive:
            return sorted(info.filename for info in archive.infolist())

    def _privacy_gate(self, root: Path) -> None:
        # Defense in depth: reject suspicious credential forms even after redaction.
        forbidden_markers = (
            "authorization: bearer ", "api_key=", "api-key=", "password=", "passwd=",
            '"password": "', '"api_key": "', "session_token=", "access_token=",
        )
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            for marker in forbidden_markers:
                if marker in text and "[redacted]" not in text[text.find(marker):text.find(marker) + 180]:
                    raise SupportBundleError("Support bundle privacy check rejected an unredacted secret field.")

    @staticmethod
    def _validate_zip(path: Path) -> None:
        with zipfile.ZipFile(path, "r") as archive:
            for info in archive.infolist():
                name = info.filename.replace("\\", "/")
                candidate = Path(name)
                if candidate.is_absolute() or ".." in candidate.parts:
                    raise SupportBundleError("Unsafe path detected in support bundle.")
            bad = archive.testzip()
            if bad:
                raise SupportBundleError(f"Support bundle CRC failed: {bad}")
