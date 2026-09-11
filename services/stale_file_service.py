from __future__ import annotations
from datetime import datetime, timezone
from domain.cleanup_policy import CleanupPolicy, CleanupPlan, CleanupResult
from domain.storage_category import StorageCategory


class StaleFileService:
    SAFE_STARTUP = (
        StorageCategory.RENDER_TEMP,
        StorageCategory.TRANSCRIPTION_TEMP,
        StorageCategory.BATCH_INTERMEDIATE,
        StorageCategory.TEMPLATE_CACHE,
    )

    def __init__(self, cleanup_service, cache_service, *, logger=None) -> None:
        self.cleanup = cleanup_service; self.cache = cache_service; self.logger = logger

    def startup_cleanup(self, policy: CleanupPolicy | None = None) -> CleanupResult:
        policy = policy or self.policy_from_preferences()
        if policy.automatic_cleanup == "off" or not policy.cleanup_stale_temp:
            return CleanupResult()
        merged = CleanupPlan(reason="startup_stale")
        now = datetime.now(timezone.utc).timestamp()
        for category in self.SAFE_STARTUP:
            plan = self.cleanup.preview_cleanup([category], stale_before=now - policy.stale_seconds(category), reason="startup_stale")
            self._merge(merged, plan)
        result = self.cleanup.execute(merged)
        # Conservative mode stops after obvious stale temp. Balanced also enforces cap.
        if policy.automatic_cleanup == "balanced" and policy.maximum_cache_bytes > 0:
            limit_plan = self.cleanup.lru_plan(maximum_bytes=policy.maximum_cache_bytes)
            extra = self.cleanup.execute(limit_plan)
            self._merge_result(result, extra)
        return result

    def enforce_limit(self, maximum_bytes: int) -> CleanupResult:
        return self.cleanup.execute(self.cleanup.lru_plan(maximum_bytes=maximum_bytes))

    def policy_from_preferences(self) -> CleanupPolicy:
        prefs = self.cache.preferences
        return CleanupPolicy(
            maximum_cache_bytes=int(prefs.get("maximumCacheBytes") or 25 * 1024**3),
            automatic_cleanup=str(prefs.get("automaticCleanup") or "balanced"),
            cleanup_stale_temp=bool(prefs.get("cleanupStaleTemp", True)),
            log_retention_days=int(prefs.get("logRetentionDays") or 14),
        )

    @staticmethod
    def _merge(target: CleanupPlan, source: CleanupPlan) -> None:
        for entry in source.entries: target.add(entry)
        target.skipped_active.extend(source.skipped_active); target.skipped_protected.extend(source.skipped_protected); target.skipped_unsafe.extend(source.skipped_unsafe)

    @staticmethod
    def _merge_result(target: CleanupResult, source: CleanupResult) -> None:
        target.freed_bytes += source.freed_bytes; target.deleted.extend(source.deleted); target.skipped_active.extend(source.skipped_active); target.skipped_protected.extend(source.skipped_protected); target.skipped_unsafe.extend(source.skipped_unsafe); target.failed.extend(source.failed)
