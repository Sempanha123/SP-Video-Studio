from __future__ import annotations


class CacheError(RuntimeError):
    """Base error for Phase 29 cache/storage operations."""


class CachePathUnsafe(CacheError):
    pass


class CacheCleanupFailed(CacheError):
    pass


class CacheMigrationFailed(CacheError):
    pass


class CacheEntryProtected(CacheError):
    pass


class CacheEntryActive(CacheError):
    pass


class StorageScanFailed(CacheError):
    pass


class DiskSpaceCritical(CacheError):
    pass
