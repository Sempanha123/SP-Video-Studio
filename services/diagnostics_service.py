from __future__ import annotations

import json
import os
import platform
import secrets
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from domain.diagnostic_result import DiagnosticResult, DiagnosticStatus
from services.log_redaction_service import LogRedactionService

try:
    from storage.migrations import MIGRATIONS
except Exception:  # focused tests can run without reconstructing the historical migration package
    MIGRATIONS = ()


class DiagnosticCancelled(RuntimeError):
    pass


class DiagnosticsService:
    """Read-only/best-effort diagnostics orchestrator.

    Quick checks never load AI engines. Full checks may hash installed model files and run
    tiny FFmpeg/database probes, and therefore must be dispatched through the shared worker pool.
    """

    REQUIRED_VIDEO_FILTERS = ("scale", "crop", "overlay", "chromakey", "colorkey")
    REQUIRED_AUDIO_FILTERS = ("volume", "afade", "amix")
    SUBTITLE_FILTERS = ("subtitles", "ass")
    ENCODERS = ("libx264", "h264_nvenc", "h264_qsv", "h264_amf")

    def __init__(
        self,
        paths,
        settings_service,
        *,
        readiness_service=None,
        ffmpeg_locator=None,
        database=None,
        model_service=None,
        disk_monitor=None,
        project_service=None,
        project_integrity_service=None,
        asset_service=None,
        template_service=None,
        batch_service=None,
        recovery_service=None,
        redaction: LogRedactionService | None = None,
        logger=None,
    ) -> None:
        self.paths = paths
        self.settings_service = settings_service
        self.readiness_service = readiness_service
        self.ffmpeg_locator = ffmpeg_locator
        self.database = database
        self.model_service = model_service
        self.disk_monitor = disk_monitor
        self.project_service = project_service
        self.project_integrity_service = project_integrity_service
        self.asset_service = asset_service
        self.template_service = template_service
        self.batch_service = batch_service
        self.recovery_service = recovery_service
        self.redaction = redaction or LogRedactionService()
        self.logger = logger

    def quick_check(self, cancellation=None) -> list[DiagnosticResult]:
        results: list[DiagnosticResult] = []
        self._check_cancelled(cancellation)
        readiness = self._readiness()
        checks: tuple[Callable[[], DiagnosticResult], ...] = (
            self._application_check,
            lambda: self._system_check(readiness),
            self._storage_check,
            lambda: self._ffmpeg_quick_check(readiness),
            self._database_quick_check,
            self._model_registry_check,
        )
        for check in checks:
            self._check_cancelled(cancellation)
            results.append(self._safe_run(check))
        self._check_cancelled(cancellation)
        results.extend(self._engine_configuration_checks())
        return results

    def full_diagnostics(self, cancellation=None, project_id: str = "") -> list[DiagnosticResult]:
        results = self.quick_check(cancellation)
        full_checks: list[Callable[[], DiagnosticResult | list[DiagnosticResult]]] = [
            self._ffmpeg_full_check,
            self._rendering_check,
            self._media_check,
            self._database_full_check,
            lambda: self._model_full_checks(cancellation),
            self._storage_full_check,
            self._assets_check,
            self._templates_check,
            self._batch_check,
            self._recovery_check,
            self._network_provider_check,
        ]
        if project_id:
            full_checks.append(lambda: self.diagnose_project(project_id))
        else:
            results.append(self._result(
                "project.selection", "Projects", "Current Project", DiagnosticStatus.NOT_CONFIGURED,
                "No project is currently selected.",
                "Open a project to inspect media, Timeline, subtitle, speaker/voice and render-readiness references.",
                "Use Diagnose Current Project after opening the project.", start=time.perf_counter(),
            ))
        for check in full_checks:
            self._check_cancelled(cancellation)
            value = self._safe_run_any(check)
            if isinstance(value, list):
                results.extend(value)
            else:
                results.append(value)
        return results

    def diagnose_project(self, project_id: str) -> list[DiagnosticResult]:
        start = time.perf_counter()
        project = None
        if self.project_service is not None:
            try:
                project = next((item for item in self.project_service.list_projects() if str(item.project_id) == str(project_id)), None)
            except Exception:
                project = None
        if project is None:
            return [self._result(
                "project.record", "Projects", "Current Project", DiagnosticStatus.FAILED,
                "Project record was not found.", "The selected project is not present in the project library.",
                "Open Projects and choose an existing project.", metadata={"action": "open_projects"}, start=start,
            )]

        root = Path(project.project_path)
        results: list[DiagnosticResult] = []
        if not root.is_dir():
            results.append(self._result(
                "project.folder", "Projects", "Project Folder", DiagnosticStatus.FAILED,
                "Project folder is missing.", self.redaction.sanitize_paths(str(root)),
                "Locate the project folder or remove the stale library entry.",
                metadata={"action": "open_projects"}, start=start,
            ))
            return results

        metadata_path = root / "project.json"
        metadata_status = DiagnosticStatus.READY
        metadata_summary = "Project record and folder agree."
        technical = ""
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata_id = str(payload.get("project_id") or payload.get("id") or "")
            if metadata_id and metadata_id != str(project.project_id):
                metadata_status = DiagnosticStatus.FAILED
                metadata_summary = "Project metadata belongs to a different project."
            technical = f"schema/version={payload.get('version', getattr(project, 'version', 'unknown'))}"
        except Exception as exc:
            metadata_status = DiagnosticStatus.FAILED
            metadata_summary = "project.json is missing or invalid."
            technical = str(exc)
        results.append(self._result(
            "project.metadata", "Projects", "Project Metadata", metadata_status, metadata_summary,
            "Portable project metadata was checked without modifying it.",
            "Restore a valid project.json from a trusted backup if this remains failed.",
            technical=technical, start=start,
        ))

        missing = self._scan_project_path_references(str(project.project_id), root)
        results.append(self._result(
            "project.media_refs", "Media", "Project File References",
            DiagnosticStatus.WARNING if missing else DiagnosticStatus.READY,
            f"{len(missing)} referenced file(s) are missing." if missing else "Referenced project files that could be inspected are present.",
            "\n".join(missing[:20]) if missing else "No missing file paths were detected in project-scoped database rows.",
            "Use relink/locate actions; diagnostics never deletes or replaces user media.",
            technical="\n".join(missing[:50]), metadata={"missingCount": len(missing), "action": "locate_media" if missing else ""}, start=start,
        ))

        if self.project_integrity_service is not None:
            try:
                integrity = self.project_integrity_service.lightweight_check()
                ok = bool(integrity.get("ok"))
                results.append(self._result(
                    "project.references", "Projects", "Database References",
                    DiagnosticStatus.READY if ok else DiagnosticStatus.FAILED,
                    "Project reference database is consistent." if ok else "Database reference issues were detected.",
                    f"Foreign-key issues: {int(integrity.get('foreignKeyIssues', 0))}",
                    "Run Full Diagnostics and preserve recovery data before attempting repair.",
                    technical=json.dumps(integrity, ensure_ascii=False), start=start,
                ))
            except Exception as exc:
                results.append(self._failed("project.references", "Projects", "Database References", exc, start))
        return results

    def diagnose_render_failure(self, technical_text: str) -> DiagnosticResult:
        text = str(technical_text or "")
        lower = text.lower()
        category = "Unknown FFmpeg Failure"
        recommendation = "Run Full Diagnostics and review the collapsed technical details."
        if any(x in lower for x in ("no such file", "file not found", "cannot find", "missing media", "does not exist")):
            category, recommendation = "Missing Media", "Locate or relink the missing media, then recheck the project."
        elif any(x in lower for x in ("no such filter", "filter not found", "error initializing filter", "unknown filter")):
            category, recommendation = "Unsupported Filter", "Check FFmpeg filter support or choose a compatible FFmpeg build."
        elif any(x in lower for x in ("no space left", "disk full", "not enough space")):
            category, recommendation = "Disk Full", "Free storage space or choose another output/cache location."
        elif any(x in lower for x in ("libass", "fontconfig", "unable to load font", "subtitle font", "subtitles filter")):
            category, recommendation = "Subtitle/Font Problem", "Check subtitle/libass support and installed fonts."
        elif any(x in lower for x in ("filtergraph", "audio graph", "amix", "amerge", "invalid audio")):
            category, recommendation = "Invalid Audio Graph", "Check Audio Mixer routing and retry after validating the project."
        elif any(x in lower for x in ("unknown encoder", "error while opening encoder", "encoder not found", "cannot load nvenc")):
            category, recommendation = "Encoder Failure", "Choose an available encoder or test the selected encoder in Full Diagnostics."
        ref = self.reference_id("RND")
        safe_technical = self.redaction.redact_text(text)[:24000]
        if self.logger:
            self.logger.error("Diagnostic reference %s render failure: %s", ref, safe_technical[:2000])
        return DiagnosticResult(
            id="render.failure",
            category="Rendering",
            name="Render Failure",
            status=DiagnosticStatus.FAILED.value,
            summary=category,
            details=f"Reference: {ref}. This reference is local to this computer/session.",
            recommendation=recommendation,
            technical_details=safe_technical,
            metadata={"rootCategory": category, "referenceId": ref, "action": "recheck"},
        )

    def recent_logs(self, severity: str = "error", limit: int = 400) -> list[dict[str, str]]:
        severity = str(severity or "all").lower()
        limit = max(1, min(2000, int(limit)))
        log_root = Path(self.paths.logs)
        if not log_root.is_dir():
            return []
        rows: list[dict[str, str]] = []
        files = sorted(
            (p for p in log_root.glob("*.log*") if p.is_file()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:5]
        for path in files:
            for line in reversed(self._tail_lines(path, min(limit * 2, 2500))):
                level = self._line_severity(line)
                if severity != "all" and level != severity:
                    continue
                rows.append({
                    "severity": level,
                    "message": self.redaction.redact_text(line)[:4000],
                    "source": self.redaction.sanitize_paths(path.name),
                })
                if len(rows) >= limit:
                    return rows
        return rows

    def short_report(self, results: Iterable[DiagnosticResult]) -> str:
        lines = ["MMO Video Studio — Sanitized Diagnostic Summary"]
        for result in results:
            lines.append(f"[{result.status.upper()}] {result.category} / {result.name}: {result.summary}")
            if result.recommendation:
                lines.append(f"  Recommendation: {result.recommendation}")
        return self.redaction.redact_text("\n".join(lines))

    def rebuild_app_owned_directories(self) -> None:
        # Safe self-repair: AppPaths.ensure only recreates app-owned roots.
        self.paths.ensure()

    @staticmethod
    def reference_id(prefix: str) -> str:
        now = datetime.now(timezone.utc).strftime("%Y%m%d")
        return f"{prefix}-{now}-{secrets.token_hex(2).upper()}"

    def _readiness(self):
        if self.readiness_service is None:
            return None
        try:
            return self.readiness_service.detect()
        except Exception as exc:
            if self.logger:
                self.logger.info("Diagnostics readiness detector unavailable", exc_info=True)
            return exc

    def _application_check(self) -> DiagnosticResult:
        import importlib.metadata
        start = time.perf_counter()
        try:
            version = importlib.metadata.version("sp-video-studio")
        except importlib.metadata.PackageNotFoundError:
            version = "0.1.0"
        return self._result(
            "application.version", "Application", "Application", DiagnosticStatus.READY,
            f"MMO Video Studio {version}", "Application package metadata is readable.", "", start=start,
        )

    def _system_check(self, readiness) -> DiagnosticResult:
        start = time.perf_counter()
        if isinstance(readiness, Exception):
            return self._failed("system.platform", "System", "System", readiness, start)
        if readiness is None:
            details = f"{platform.system()} {platform.release()} · {platform.machine()}"
            return self._result("system.platform", "System", "System", DiagnosticStatus.READY, "Platform detected.", details, "", start=start)
        gpu = getattr(readiness, "gpu_name", None) or "No GPU detected"
        cuda = getattr(readiness, "cuda_status", "unknown")
        summary = f"CPU/RAM detected; GPU: {gpu}; CUDA: {cuda}."
        status = DiagnosticStatus.READY if getattr(readiness, "cpu_name", "Unknown") != "Unknown" else DiagnosticStatus.WARNING
        details = (
            f"CPU: {getattr(readiness, 'cpu_name', 'Unknown')}\n"
            f"RAM total: {getattr(readiness, 'ram_total', None)}\n"
            f"GPU: {gpu}\nCUDA: {cuda}\n"
            "Selected device mode: engine-managed/automatic\n"
            "A missing GPU or nvidia-smi is not fatal; CPU workflows remain supported."
        )
        return self._result("system.platform", "System", "System / GPU", status, summary, details, "", start=start)

    def _storage_check(self) -> DiagnosticResult:
        start = time.perf_counter()
        s = self.settings_service.current
        roots = [
            ("Application Data", Path(self.paths.root)),
            ("Projects", Path(getattr(s, "default_projects_folder", ""))),
            ("Cache", Path(self.paths.cache)),
        ]
        failures: list[str] = []
        warnings: list[str] = []
        for label, path in roots:
            if not path.is_dir():
                failures.append(f"{label}: missing ({self.redaction.sanitize_paths(str(path))})")
                continue
            if not self._writable_directory(path):
                failures.append(f"{label}: not writable")
            try:
                if self.disk_monitor is not None:
                    disk = self.disk_monitor.check(path, label=label)
                    state = str(getattr(disk.state, "value", disk.state))
                    if state in {"low", "critical"}:
                        warnings.append(f"{label}: {state} disk space ({getattr(disk, 'free_bytes', 0)} bytes free)")
                else:
                    usage = shutil.disk_usage(path)
                    if usage.free < 10 * 1024**3:
                        warnings.append(f"{label}: low disk space ({usage.free} bytes free)")
            except OSError:
                warnings.append(f"{label}: disk usage unavailable")
        status = DiagnosticStatus.FAILED if failures else (DiagnosticStatus.WARNING if warnings else DiagnosticStatus.READY)
        summary = "Storage paths are writable." if status == DiagnosticStatus.READY else "Storage needs attention."
        return self._result(
            "storage.quick", "Storage", "Storage", status, summary,
            "\n".join(failures + warnings) or "App-data, project and cache roots are available.",
            "Open Storage settings before heavy renders if warnings remain.",
            metadata={"action": "open_storage" if status != DiagnosticStatus.READY else ""}, start=start,
        )

    def _storage_full_check(self) -> DiagnosticResult:
        start = time.perf_counter()
        roots = [
            ("Models", Path(self.paths.models)), ("Assets", Path(self.paths.assets)),
            ("Recovery", Path(self.paths.recovery)), ("Exports", Path(self.paths.exports)),
            ("Temporary", Path(self.paths.temp)),
        ]
        problems: list[str] = []
        for label, path in roots:
            if not path.is_dir():
                problems.append(f"{label}: missing")
            elif not self._writable_directory(path):
                problems.append(f"{label}: not writable")
            else:
                try:
                    usage = self.disk_monitor.check(path, label=label) if self.disk_monitor is not None else None
                    if usage is not None and str(getattr(usage.state, "value", usage.state)) in {"low", "critical"}:
                        problems.append(f"{label}: {getattr(usage.state, 'value', usage.state)} disk space")
                except OSError:
                    problems.append(f"{label}: disk state unavailable")
        return self._result(
            "storage.full", "Storage", "Managed Storage Roots",
            DiagnosticStatus.WARNING if problems else DiagnosticStatus.READY,
            "Managed storage roots need attention." if problems else "Managed storage roots are ready.",
            "\n".join(problems) or "Models, Assets, Recovery, Exports and Temporary roots are writable.",
            "Rebuild only missing app-owned folders; never overwrite user media.",
            metadata={"action": "rebuild_app_dirs" if problems else ""}, start=start,
        )

    def _ffmpeg_quick_check(self, readiness) -> DiagnosticResult:
        start = time.perf_counter()
        ffmpeg_available = bool(getattr(readiness, "ffmpeg_available", False)) if readiness and not isinstance(readiness, Exception) else False
        ffprobe_available = bool(getattr(readiness, "ffprobe_available", False)) if readiness and not isinstance(readiness, Exception) else False
        ffmpeg_path = getattr(readiness, "ffmpeg_path", "") if readiness and not isinstance(readiness, Exception) else ""
        ffprobe_path = getattr(readiness, "ffprobe_path", "") if readiness and not isinstance(readiness, Exception) else ""
        if readiness is None and self.ffmpeg_locator is not None:
            s = self.settings_service.current
            custom_ffmpeg = getattr(s, "ffmpeg_path", "") if getattr(s, "ffmpeg_mode", "auto") == "custom" else None
            custom_ffprobe = getattr(s, "ffprobe_path", "") if getattr(s, "ffmpeg_mode", "auto") == "custom" else None
            ffmpeg, ffprobe = self.ffmpeg_locator.discover(custom_ffmpeg, custom_ffprobe)
            ffmpeg_available, ffprobe_available = ffmpeg.available, ffprobe.available
            ffmpeg_path, ffprobe_path = ffmpeg.path or "", ffprobe.path or ""
        if ffmpeg_available and ffprobe_available:
            status, summary = DiagnosticStatus.READY, "FFmpeg and FFprobe are available."
        elif ffmpeg_available or ffprobe_available:
            status, summary = DiagnosticStatus.WARNING, "Only one required media tool is available."
        else:
            status, summary = DiagnosticStatus.NOT_CONFIGURED, "FFmpeg and FFprobe are not available."
        return self._result(
            "ffmpeg.availability", "FFmpeg", "FFmpeg / FFprobe", status, summary,
            f"FFmpeg: {self.redaction.sanitize_paths(str(ffmpeg_path or 'missing'))}\nFFprobe: {self.redaction.sanitize_paths(str(ffprobe_path or 'missing'))}",
            "Choose FFmpeg in Settings or install a compatible build.",
            metadata={"action": "choose_ffmpeg" if status != DiagnosticStatus.READY else ""}, start=start,
        )

    def _ffmpeg_full_check(self) -> DiagnosticResult:
        start = time.perf_counter()
        if self.ffmpeg_locator is None:
            return self._result("ffmpeg.capabilities", "FFmpeg", "FFmpeg Capabilities", DiagnosticStatus.NOT_AVAILABLE, "FFmpeg detector is unavailable.", "", "Recheck after restarting the app.", start=start)
        s = self.settings_service.current
        custom_ffmpeg = getattr(s, "ffmpeg_path", "") if getattr(s, "ffmpeg_mode", "auto") == "custom" else None
        custom_ffprobe = getattr(s, "ffprobe_path", "") if getattr(s, "ffmpeg_mode", "auto") == "custom" else None
        ffmpeg, ffprobe = self.ffmpeg_locator.discover(custom_ffmpeg, custom_ffprobe)
        if not ffmpeg.available or not ffmpeg.path:
            return self._result("ffmpeg.capabilities", "FFmpeg", "FFmpeg Capabilities", DiagnosticStatus.NOT_CONFIGURED, "FFmpeg is unavailable.", ffmpeg.error or "", "Choose FFmpeg in Settings.", metadata={"action": "choose_ffmpeg"}, start=start)
        filters = self._ffmpeg_listing(ffmpeg.path, "-filters")
        encoders = self._ffmpeg_listing(ffmpeg.path, "-encoders")
        decoders = self._ffmpeg_listing(ffmpeg.path, "-decoders")
        missing_filters = [x for x in (*self.REQUIRED_VIDEO_FILTERS, *self.REQUIRED_AUDIO_FILTERS) if not self._has_listing_name(filters, x)]
        subtitle_ok = any(self._has_listing_name(filters, x) for x in self.SUBTITLE_FILTERS)
        encoder_rows: list[str] = []
        required_encoder_problem = ""
        for encoder in self.ENCODERS:
            listed = self._has_listing_name(encoders, encoder)
            if not listed:
                encoder_rows.append(f"{encoder}: not listed")
                if encoder == "libx264":
                    required_encoder_problem = "encoder:libx264-not-listed"
                continue
            smoke = self._ffmpeg_encoder_smoke(ffmpeg.path, encoder)
            encoder_rows.append(f"{encoder}: listed; tiny smoke {'passed' if smoke else 'failed/unavailable'}")
            if encoder == "libx264" and not smoke:
                required_encoder_problem = "encoder:libx264-smoke-failed"
        generic_smoke = self._ffmpeg_source_smoke(ffmpeg.path)
        decoder_basics = [name for name in ("h264", "aac") if not self._has_listing_name(decoders, name)]
        warnings = list(missing_filters)
        if required_encoder_problem:
            warnings.append(required_encoder_problem)
        if not subtitle_ok:
            warnings.append("subtitles/libass")
        warnings.extend(f"decoder:{name}" for name in decoder_basics)
        if not generic_smoke:
            warnings.append("generated-source smoke")
        status = DiagnosticStatus.WARNING if warnings else DiagnosticStatus.READY
        details = (
            f"FFmpeg {ffmpeg.version or 'Unknown'}\nFFprobe {ffprobe.version if ffprobe.available else 'missing'}\n"
            f"Missing capabilities: {', '.join(warnings) if warnings else 'none'}\n"
            + "\n".join(encoder_rows)
            + "\nHardware encoders are considered usable only when their tiny smoke probe succeeds; listing alone is not treated as hardware availability."
        )
        technical = f"filters={filters[-12000:]}\nencoders={encoders[-12000:]}\ndecoders={decoders[-8000:]}"
        return self._result(
            "ffmpeg.capabilities", "FFmpeg", "FFmpeg Capabilities", status,
            "FFmpeg capability smoke test passed." if status == DiagnosticStatus.READY else "FFmpeg is present but some capabilities need attention.",
            details, "Use a compatible FFmpeg build or choose a different encoder.", technical=technical, start=start,
        )

    def _database_quick_check(self) -> DiagnosticResult:
        start = time.perf_counter()
        if self.database is None:
            return self._result("database.quick", "Database", "Database", DiagnosticStatus.NOT_AVAILABLE, "Database service is unavailable.", "", "Restart the application and recheck.", start=start)
        try:
            with self.database.connect() as conn:
                value = conn.execute("SELECT 1").fetchone()[0]
                applied = int(self.database.current_version())
            expected = max((int(getattr(m, "version", 0)) for m in MIGRATIONS), default=applied)
            pending = sum(1 for m in MIGRATIONS if int(getattr(m, "version", 0)) > applied)
            status = DiagnosticStatus.WARNING if pending else DiagnosticStatus.READY
            return self._result(
                "database.quick", "Database", "Database", status,
                "Database connection is healthy." if not pending else "Database is readable but migrations are pending.",
                f"Basic query={value}; schema version={applied}; pending migrations={pending}",
                "Restart normally to apply migrations, then recheck." if pending else "", metadata={"schemaVersion": applied, "pendingMigrations": pending}, start=start,
            )
        except Exception as exc:
            return self._failed("database.quick", "Database", "Database", exc, start)

    def _database_full_check(self) -> DiagnosticResult:
        start = time.perf_counter()
        if self.database is None:
            return self._result("database.integrity", "Database", "Database Integrity", DiagnosticStatus.NOT_AVAILABLE, "Database service is unavailable.", "", "Restart the application and recheck.", start=start)
        try:
            with self.database.connect() as conn:
                integrity_rows = conn.execute("PRAGMA integrity_check").fetchmany(50)
                integrity = [str(row[0]) for row in integrity_rows]
                fk_rows = conn.execute("PRAGMA foreign_key_check").fetchmany(50)
                # Safe transactional probe: no application table is touched and the transaction is rolled back.
                conn.execute("BEGIN")
                conn.execute("CREATE TEMP TABLE IF NOT EXISTS phase36_diagnostic_probe(value INTEGER)")
                conn.execute("INSERT INTO phase36_diagnostic_probe(value) VALUES (1)")
                probe = conn.execute("SELECT COUNT(*) FROM phase36_diagnostic_probe").fetchone()[0]
                conn.rollback()
            ok = integrity == ["ok"] and not fk_rows and probe >= 1
            return self._result(
                "database.integrity", "Database", "Database Integrity",
                DiagnosticStatus.READY if ok else DiagnosticStatus.FAILED,
                "SQLite integrity checks passed." if ok else "SQLite integrity/reference issues were detected.",
                f"integrity={integrity[:10]}; foreignKeyIssues={len(fk_rows)}; transactionProbe={probe}",
                "Preserve recovery data and seek repair guidance before modifying the database." if not ok else "",
                technical=f"integrity={integrity}; foreign_keys={len(fk_rows)}", start=start,
            )
        except Exception as exc:
            return self._failed("database.integrity", "Database", "Database Integrity", exc, start)

    def _model_registry_check(self) -> DiagnosticResult:
        start = time.perf_counter()
        if self.model_service is None:
            return self._result("models.registry", "Models", "Model Registry", DiagnosticStatus.NOT_AVAILABLE, "Model Manager is unavailable.", "", "Open Models after restarting the app.", start=start)
        models = list(self.model_service.registry.list_all())
        installed = 0
        states: list[str] = []
        for model in models:
            installation = self.model_service.repository.get(model.model_id)
            is_installed = bool(getattr(installation, "installed", False))
            installed += int(is_installed)
            states.append(f"{model.model_id}: {'installed' if is_installed else 'not installed'}")
        status = DiagnosticStatus.READY if models else DiagnosticStatus.WARNING
        return self._result(
            "models.registry", "Models", "Model Registry", status,
            f"{len(models)} managed model(s); {installed} installed.",
            "\n".join(states) or "No managed models are registered.",
            "Open Models to install/repair optional AI features.", metadata={"action": "open_models"}, start=start,
        )

    def _model_full_checks(self, cancellation=None) -> list[DiagnosticResult]:
        if self.model_service is None:
            return [self._result("models.verify", "Models", "Model Verification", DiagnosticStatus.NOT_AVAILABLE, "Model Manager is unavailable.", "", "", start=time.perf_counter())]
        results: list[DiagnosticResult] = []
        readiness = self._readiness()
        if isinstance(readiness, Exception):
            readiness = None
        for model in self.model_service.registry.list_all():
            self._check_cancelled(cancellation)
            start = time.perf_counter()
            path = self.model_service.install_path(model)
            compatibility = "unknown"
            compatibility_summary = "Hardware compatibility not checked."
            compatibility_service = getattr(self.model_service, "compatibility_service", None)
            if compatibility_service is not None:
                try:
                    assessment = compatibility_service.assess(model, readiness)
                    compatibility = str(getattr(assessment, "status", "unknown"))
                    compatibility_summary = str(getattr(assessment, "summary", compatibility_summary))
                except Exception:
                    pass
            installation = self.model_service.repository.get(model.model_id)
            if not path.exists():
                results.append(self._result(
                    f"model.{model.model_id}", "Models", model.name, DiagnosticStatus.NOT_CONFIGURED,
                    "Model is not installed.", f"Expected location: {self.redaction.sanitize_paths(str(path))}",
                    "Install it only if this AI feature is needed.", metadata={"modelId": model.model_id, "installed": False, "verified": False, "loadTested": False, "action": "open_models"}, start=start,
                ))
                continue
            try:
                verification = self.model_service.verification_service.verify(model, path)
                valid = bool(verification.valid)
                status = DiagnosticStatus.READY if valid else DiagnosticStatus.FAILED
                size = self._directory_size(path)
                results.append(self._result(
                    f"model.{model.model_id}", "Models", model.name, status,
                    "Installed and verified." if valid else "Installed files need repair.",
                    f"Registry: yes\nPath exists: yes\nManifest/expected files/checksums: {'verified' if valid else 'failed'}\nVersion: {model.version}\nEngine compatibility: {compatibility} — {compatibility_summary}\nDisk size: {size} bytes\nLoad tested: no (not automatic)",
                    "Use the existing Model Manager Repair action." if not valid else "",
                    technical="\n".join(getattr(verification, "errors", [])),
                    metadata={"modelId": model.model_id, "installed": bool(getattr(installation, "installed", False)), "verified": valid, "loadTested": False, "action": "repair_model" if not valid else ""}, start=start,
                ))
            except Exception as exc:
                results.append(self._failed(f"model.{model.model_id}", "Models", model.name, exc, start))
        return results

    def _engine_configuration_checks(self) -> list[DiagnosticResult]:
        start = time.perf_counter()
        if self.model_service is None:
            return [
                self._result(f"engine.{key}", category, name, DiagnosticStatus.NOT_AVAILABLE,
                             f"{name} configuration could not be inspected.",
                             "Manual/offline editing remains available.", "", start=start)
                for key, category, name in (
                    ("tts", "TTS", "Voice / TTS"),
                    ("stt", "STT", "Speech Recognition"),
                    ("translation", "Translation", "Translation"),
                )
            ]
        mapping = {
            "voice": ("tts", "TTS", "Voice / TTS"),
            "speech-to-text": ("stt", "STT", "Speech Recognition"),
            "translation": ("translation", "Translation", "Translation"),
        }
        counts = {purpose: [0, 0] for purpose in mapping}
        for model in self.model_service.registry.list_all():
            purpose = str(getattr(model, "purpose_code", getattr(model, "purpose", "")))
            if purpose not in counts:
                continue
            counts[purpose][0] += 1
            item = self.model_service.repository.get(model.model_id)
            counts[purpose][1] += int(bool(getattr(item, "installed", False)))
        results: list[DiagnosticResult] = []
        for purpose, (key, category, name) in mapping.items():
            total, installed = counts[purpose]
            status = DiagnosticStatus.READY if installed else (DiagnosticStatus.NOT_CONFIGURED if total else DiagnosticStatus.NOT_AVAILABLE)
            results.append(self._result(
                f"engine.{key}", category, name, status,
                f"{installed}/{total} managed model(s) installed." if total else "No managed model is registered for this engine family.",
                "Quick Check inspected registry/install state only; no AI model was loaded.",
                "Open Models if this optional AI feature is needed.",
                metadata={"action": "open_models" if installed == 0 and total else ""}, start=start,
            ))
        return results

    def _rendering_check(self) -> DiagnosticResult:
        start = time.perf_counter()
        if self.ffmpeg_locator is None:
            return self._result("rendering.environment", "Rendering", "Rendering", DiagnosticStatus.NOT_AVAILABLE, "Rendering capability could not be inspected.", "FFmpeg locator is unavailable.", "Restart and recheck.", start=start)
        s = self.settings_service.current
        custom = getattr(s, "ffmpeg_path", "") if getattr(s, "ffmpeg_mode", "auto") == "custom" else None
        ffmpeg, _ = self.ffmpeg_locator.discover(custom, None)
        status = DiagnosticStatus.READY if ffmpeg.available else DiagnosticStatus.NOT_CONFIGURED
        return self._result(
            "rendering.environment", "Rendering", "Rendering", status,
            "Rendering prerequisites are available." if ffmpeg.available else "Rendering needs FFmpeg setup.",
            "Final render quality is not changed by diagnostics. Encoder-specific capability is reported by the FFmpeg check.",
            "Choose FFmpeg or inspect the FFmpeg capability result." if not ffmpeg.available else "",
            metadata={"action": "choose_ffmpeg" if not ffmpeg.available else ""}, start=start,
        )

    def _media_check(self) -> DiagnosticResult:
        start = time.perf_counter()
        status = DiagnosticStatus.READY if self.project_service is not None else DiagnosticStatus.NOT_AVAILABLE
        return self._result(
            "media.environment", "Media", "Media References", status,
            "Media/project services are available for project diagnosis." if status == DiagnosticStatus.READY else "Media project diagnostics are unavailable.",
            "Open a project and choose Diagnose Current Project to inspect missing referenced media.",
            "No private media is opened or bundled by this environment check.", start=start,
        )

    def _assets_check(self) -> DiagnosticResult:
        start = time.perf_counter()
        root = Path(self.paths.assets)
        if self.asset_service is None:
            return self._root_feature_check("assets.root", "Assets", "Asset Library", root, None, "Open Assets to relink missing library files.")
        try:
            assets = list(self.asset_service.list_assets())
            missing = []
            library_root = Path(self.asset_service.library_root)
            for asset in assets[:5000]:
                try:
                    resolved = asset.resolved_path(library_root)
                    if not resolved.exists():
                        missing.append(getattr(asset, "name", getattr(asset, "id", "asset")))
                except Exception:
                    continue
            return self._result(
                "assets.root", "Assets", "Asset Library",
                DiagnosticStatus.WARNING if missing else DiagnosticStatus.READY,
                f"{len(missing)} Asset Library file(s) are missing." if missing else f"Asset Library is ready ({len(assets)} asset(s) inspected).",
                "Missing: " + ", ".join(str(x) for x in missing[:20]) if missing else self.redaction.sanitize_paths(str(library_root)),
                "Use the existing Asset Library relink workflow; diagnostics never deletes assets.",
                metadata={"missingCount": len(missing)}, start=start,
            )
        except Exception as exc:
            return self._failed("assets.root", "Assets", "Asset Library", exc, start)

    def _templates_check(self) -> DiagnosticResult:
        start = time.perf_counter()
        if self.template_service is None:
            return self._root_feature_check("templates.root", "Templates", "Templates", Path(self.paths.templates), None, "Re-import or repair only the affected template package.")
        try:
            templates = list(self.template_service.list_templates())
            invalid = []
            for item in templates:
                try:
                    self.template_service.validation.validate(item)
                except Exception as exc:
                    invalid.append(f"{getattr(item, 'name', getattr(item, 'id', 'template'))}: {exc}")
            return self._result(
                "templates.root", "Templates", "Templates",
                DiagnosticStatus.WARNING if invalid else DiagnosticStatus.READY,
                f"{len(invalid)} template(s) need attention." if invalid else f"Templates are valid ({len(templates)} inspected).",
                "\n".join(invalid[:20]) if invalid else "Template manifests passed the existing validation service.",
                "Re-import or repair only the affected template package.", start=start,
            )
        except Exception as exc:
            return self._failed("templates.root", "Templates", "Templates", exc, start)

    def _batch_check(self) -> DiagnosticResult:
        start = time.perf_counter()
        if self.batch_service is None:
            return self._result("batch.service", "Batch", "Batch Factory", DiagnosticStatus.NOT_AVAILABLE, "Batch Factory diagnostic adapter is unavailable.", "No batch job is started by diagnostics.", "Open Batch Factory and validate the affected batch.", start=start)
        try:
            history = list(self.batch_service.history())
            failed = [row for row in history if str(row.get("status", "")).lower() in {"failed", "completed_with_errors", "interrupted"}]
            return self._result(
                "batch.service", "Batch", "Batch Factory", DiagnosticStatus.WARNING if failed else DiagnosticStatus.READY,
                f"{len(failed)} recent batch(es) report errors." if failed else f"Batch Factory is ready ({len(history)} batch record(s)).",
                "No batch is started or modified by diagnostics.", "Open Batch Factory to inspect/retry affected items.", start=start,
            )
        except Exception as exc:
            return self._failed("batch.service", "Batch", "Batch Factory", exc, start)

    def _recovery_check(self) -> DiagnosticResult:
        start = time.perf_counter()
        root = Path(self.paths.recovery)
        if not root.is_dir() or not self._writable_directory(root):
            return self._result("recovery.root", "Recovery", "Recovery State", DiagnosticStatus.WARNING, "Recovery storage needs attention.", self.redaction.sanitize_paths(str(root)), "Do not delete recovery snapshots during diagnostics.", start=start)
        recoverable = []
        if self.recovery_service is not None:
            try:
                recoverable = list(self.recovery_service.recoverable())
            except Exception:
                recoverable = []
        return self._result(
            "recovery.root", "Recovery", "Recovery State", DiagnosticStatus.READY,
            f"Recovery storage is available; {len(recoverable)} recoverable snapshot(s) detected.",
            self.redaction.sanitize_paths(str(root)), "Recovery snapshots are never bundled or deleted by diagnostics.", start=start,
        )

    def _network_provider_check(self) -> DiagnosticResult:
        start = time.perf_counter()
        return self._result(
            "network.providers", "Network Providers", "Network / Providers", DiagnosticStatus.NOT_CONFIGURED,
            "No external provider probe is configured for diagnostics.",
            "Offline diagnostics remain fully available. No project content or provider request is sent.",
            "Configure a provider only inside the feature that needs it.", start=start,
        )

    def _root_feature_check(self, ident: str, category: str, name: str, root: Path, service, recommendation: str) -> DiagnosticResult:
        start = time.perf_counter()
        if not root.is_dir():
            return self._result(ident, category, name, DiagnosticStatus.WARNING, f"{name} root is missing.", self.redaction.sanitize_paths(str(root)), "Use safe app-folder repair or reopen the feature.", metadata={"action": "rebuild_app_dirs"}, start=start)
        status = DiagnosticStatus.READY if self._writable_directory(root) else DiagnosticStatus.FAILED
        details = f"Root: {self.redaction.sanitize_paths(str(root))}\nService: {'available' if service is not None else 'not registered for deep diagnostics'}"
        return self._result(ident, category, name, status, f"{name} storage is ready." if status == DiagnosticStatus.READY else f"{name} storage is not writable.", details, recommendation, start=start)

    def _scan_project_path_references(self, project_id: str, project_root: Path) -> list[str]:
        if self.database is None:
            return []
        missing: list[str] = []
        try:
            with self.database.connect() as conn:
                tables = [str(row[0]) for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
                for table in tables:
                    if not table.replace("_", "").isalnum():
                        continue
                    columns = [str(row[1]) for row in conn.execute(f'PRAGMA table_info("{table}")')]
                    if "project_id" not in columns:
                        continue
                    path_columns = [c for c in columns if c.lower() in {"path", "file_path", "media_path", "audio_path", "output_path", "thumbnail_path", "source_path"} or c.lower().endswith("_path")]
                    for column in path_columns:
                        rows = conn.execute(f'SELECT "{column}" FROM "{table}" WHERE project_id=? AND "{column}" IS NOT NULL LIMIT 500', (project_id,)).fetchall()
                        for row in rows:
                            raw = str(row[0] or "").strip()
                            if not raw:
                                continue
                            candidate = Path(raw).expanduser()
                            if not candidate.is_absolute():
                                candidate = project_root / candidate
                            if not candidate.exists():
                                missing.append(f"{table}.{column}: {self.redaction.sanitize_paths(str(candidate))}")
        except Exception as exc:
            if self.logger:
                self.logger.info("Project path reference scan unavailable", exc_info=True)
        return list(dict.fromkeys(missing))

    def _ffmpeg_listing(self, executable: str, argument: str) -> str:
        try:
            completed = subprocess.run([executable, "-hide_banner", argument], capture_output=True, text=True, timeout=8, shell=False, check=False)
            return ((completed.stdout or "") + "\n" + (completed.stderr or ""))[-200000:]
        except (OSError, subprocess.SubprocessError) as exc:
            return f"ERROR: {exc}"

    @staticmethod
    def _has_listing_name(listing: str, name: str) -> bool:
        token = str(name).lower()
        for line in listing.lower().splitlines():
            words = line.replace("=", " ").replace(",", " ").split()
            if token in words:
                return True
        return False

    @staticmethod
    def _ffmpeg_source_smoke(executable: str) -> bool:
        try:
            completed = subprocess.run(
                [executable, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black:s=16x16:d=0.08", "-frames:v", "1", "-f", "null", "-"],
                capture_output=True, text=True, timeout=10, shell=False, check=False,
            )
            return completed.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    @staticmethod
    def _ffmpeg_encoder_smoke(executable: str, encoder: str) -> bool:
        try:
            completed = subprocess.run(
                [executable, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=0.08", "-frames:v", "1", "-c:v", encoder, "-f", "null", "-"],
                capture_output=True, text=True, timeout=12, shell=False, check=False,
            )
            return completed.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    @staticmethod
    def _directory_size(path: Path) -> int:
        total = 0
        try:
            for item in path.rglob("*"):
                if item.is_file():
                    try:
                        total += item.stat().st_size
                    except OSError:
                        pass
        except OSError:
            pass
        return total

    @staticmethod
    def _writable_directory(path: Path) -> bool:
        if not path.is_dir() or not os.access(path, os.W_OK):
            return False
        probe = path / f".phase36-write-probe-{secrets.token_hex(4)}"
        try:
            probe.write_bytes(b"ok")
            probe.unlink(missing_ok=True)
            return True
        except OSError:
            try:
                probe.unlink(missing_ok=True)
            except OSError:
                pass
            return False

    def _safe_run(self, fn: Callable[[], DiagnosticResult]) -> DiagnosticResult:
        try:
            return fn()
        except DiagnosticCancelled:
            raise
        except Exception as exc:
            return self._failed("diagnostics.internal", "Application", "Diagnostic Check", exc, time.perf_counter())

    def _safe_run_any(self, fn):
        try:
            return fn()
        except DiagnosticCancelled:
            raise
        except Exception as exc:
            return self._failed("diagnostics.internal", "Application", "Diagnostic Check", exc, time.perf_counter())

    def _failed(self, ident: str, category: str, name: str, exc: Exception, start: float) -> DiagnosticResult:
        detail = self.redaction.redact_text(str(exc) or exc.__class__.__name__)
        return self._result(ident, category, name, DiagnosticStatus.FAILED, "The diagnostic check could not complete.", detail, "Recheck or open Logs for more detail.", technical=detail, start=start)

    def _result(
        self,
        ident: str,
        category: str,
        name: str,
        status: DiagnosticStatus | str,
        summary: str,
        details: str,
        recommendation: str,
        *,
        technical: str = "",
        metadata: dict[str, Any] | None = None,
        start: float | None = None,
    ) -> DiagnosticResult:
        return DiagnosticResult(
            id=ident,
            category=category,
            name=name,
            status=str(status.value if isinstance(status, DiagnosticStatus) else status),
            summary=self.redaction.redact_text(summary),
            details=self.redaction.redact_text(details),
            recommendation=self.redaction.redact_text(recommendation),
            technical_details=self.redaction.redact_text(technical),
            duration_ms=max(0, int((time.perf_counter() - start) * 1000)) if start else 0,
            metadata=self.redaction.redact_value(metadata or {}),
        )

    @staticmethod
    def _line_severity(line: str) -> str:
        upper = line.upper()
        if "CRITICAL" in upper or "ERROR" in upper or "EXCEPTION" in upper or "TRACEBACK" in upper:
            return "error"
        if "WARNING" in upper or " WARN " in upper:
            return "warning"
        if "DEBUG" in upper:
            return "debug"
        return "info"

    @staticmethod
    def _tail_lines(path: Path, limit: int) -> list[str]:
        try:
            with path.open("rb") as handle:
                handle.seek(0, os.SEEK_END)
                size = handle.tell()
                read_size = min(size, 1024 * 1024)
                handle.seek(max(0, size - read_size))
                text = handle.read(read_size).decode("utf-8", errors="replace")
            return text.splitlines()[-limit:]
        except OSError:
            return []

    @staticmethod
    def _check_cancelled(token) -> None:
        if token is None:
            return
        cancelled = False
        if hasattr(token, "is_set"):
            cancelled = bool(token.is_set())
        elif hasattr(token, "cancelled"):
            attr = token.cancelled
            cancelled = bool(attr() if callable(attr) else attr)
        elif hasattr(token, "is_cancelled"):
            attr = token.is_cancelled
            cancelled = bool(attr() if callable(attr) else attr)
        if cancelled:
            raise DiagnosticCancelled("Diagnostics cancelled by user.")
