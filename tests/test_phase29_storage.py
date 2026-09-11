from __future__ import annotations

import json
import os
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.paths import AppPaths
from domain.cache_entry import CacheEntry
from domain.cache_errors import CacheMigrationFailed, CachePathUnsafe, DiskSpaceCritical
from domain.cleanup_policy import CleanupPlan
from domain.storage_category import StorageCategory, StorageSafety, definition
from services.cache_service import CacheService
from services.storage_usage_service import StorageUsageService
from services.cleanup_service import CleanupService
from services.cache_migration_service import CacheMigrationService
from services.disk_monitor_service import DiskMonitorService, DiskState
from services.stale_file_service import StaleFileService


def make_paths(tmp_path: Path) -> AppPaths:
    root = tmp_path / "MMOVideoStudio"
    paths = AppPaths(
        root=root,
        models=root / "models",
        cache=root / "cache",
        temp=root / "temp",
        logs=root / "logs",
        settings=root / "settings",
        downloads=root / "downloads",
    )
    paths.ensure()
    return paths


def write(path: Path, data: bytes = b"x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def services(tmp_path: Path, **cleanup_kwargs):
    paths = make_paths(tmp_path)
    cache = CacheService(paths)
    cleanup = CleanupService(cache, paths, **cleanup_kwargs)
    usage = StorageUsageService(paths, cache)
    return paths, cache, cleanup, usage


def test_storage_classification_and_safety_levels():
    assert definition(StorageCategory.PREVIEW_CACHE).safety == StorageSafety.SAFE_TO_CLEAR
    assert definition(StorageCategory.GENERATED_AUDIO).safety == StorageSafety.REGENERATABLE
    assert definition(StorageCategory.RECOVERY_DATA).safety == StorageSafety.PROTECTED
    assert definition(StorageCategory.PROJECT_MEDIA).safety == StorageSafety.USER_DATA
    assert definition(StorageCategory.EXTERNAL_REFERENCES).safety == StorageSafety.EXTERNAL
    assert definition(StorageCategory.AI_MODELS).safety == StorageSafety.PROTECTED
    assert definition(StorageCategory.FINAL_EXPORTS).safety == StorageSafety.USER_DATA


def test_cache_manifest_and_scan(tmp_path):
    paths, cache, *_ = services(tmp_path)
    folder = cache.project_category_root(StorageCategory.PREVIEW_CACHE, "p1")
    target = write(folder / "preview.bin", b"abc")
    cache.write_manifest(folder, {"category":"preview_cache","projectId":"p1","ownerId":"job-1","createdAt":"2026-01-01T00:00:00+00:00","lastUsed":"2026-01-02T00:00:00+00:00","safeToDelete":True,"sourceFingerprint":"src","cacheVersion":"29.1"})
    rows = cache.scan_entries([StorageCategory.PREVIEW_CACHE], project_id="p1")
    assert len(rows) == 1 and rows[0].path == target
    assert rows[0].project_id == "p1" and rows[0].owner_id == "job-1" and rows[0].source_fingerprint == "src"


def test_storage_totals_and_external_reference_exclusion(tmp_path):
    paths = make_paths(tmp_path)
    cache = CacheService(paths)
    write(cache.category_root(StorageCategory.PREVIEW_CACHE) / "a.bin", b"a" * 10)
    write(paths.models / "model.bin", b"m" * 20)
    write(paths.recovery / "snap.spvrecovery", b"r" * 30)
    write(paths.exports / "final.mp4", b"e" * 40)
    asset_root = paths.assets
    write(asset_root / "managed.dat", b"z" * 50)
    usage = StorageUsageService(paths, cache, asset_root_provider=lambda:asset_root, external_asset_bytes_provider=lambda:999)
    result = usage.recalculate(force=True)
    assert result["externalReferencedBytes"] == 999
    assert result["totalOwnedBytes"] == 10 + 20 + 30 + 40 + 50
    assert result["totalOwnedBytes"] < result["externalReferencedBytes"] + result["totalOwnedBytes"]


def test_project_storage_breakdown(tmp_path):
    paths = make_paths(tmp_path); cache = CacheService(paths)
    project = tmp_path / "Projects" / "P"; project.mkdir(parents=True)
    write(project / "project.json", b"{}")
    write(project / "media" / "clip.mp4", b"m" * 10)
    write(project / "generated" / "voice.wav", b"a" * 20)
    write(project / "cache" / "preview.bin", b"c" * 30)
    write(project / "thumbnails" / "thumb.jpg", b"t" * 5)
    write(project / "renders" / "final.mp4", b"r" * 40)
    usage = StorageUsageService(paths, cache, project_provider=lambda:[{"project_id":"p1","name":"Thai News Daily","path":str(project)}])
    row = usage.project_usage()[0]
    assert row.media_bytes == 10 and row.generated_audio_bytes == 20
    assert row.cache_bytes == 35 and row.exports_bytes == 40
    assert row.project_data_bytes == 2

@pytest.mark.parametrize("category", [StorageCategory.PREVIEW_CACHE, StorageCategory.THUMBNAIL_CACHE, StorageCategory.RENDER_TEMP])
def test_clear_safe_cache_categories(tmp_path, category):
    paths, cache, cleanup, _ = services(tmp_path)
    target = write(cache.category_root(category) / "item.bin", b"abc")
    result = cleanup.clear_categories([category])
    assert not target.exists() and result.freed_bytes == 3


def test_active_render_temp_is_skipped(tmp_path):
    active = set()
    paths = make_paths(tmp_path); cache = CacheService(paths)
    target = write(cache.category_root(StorageCategory.RENDER_TEMP) / "render.tmp", b"12345")
    active.add(target.resolve())
    cleanup = CleanupService(cache, paths, active_checker=lambda p,e:p.resolve() in active)
    result = cleanup.clear_all_cache()
    assert target.exists() and str(target) in result.skipped_active


def test_active_tts_temp_is_skipped(tmp_path):
    paths = make_paths(tmp_path); cache = CacheService(paths)
    target = write(cache.project_category_root(StorageCategory.GENERATED_AUDIO,"p1") / "tts.wav", b"voice")
    cleanup = CleanupService(cache, paths, active_checker=lambda p,e:e.category == StorageCategory.GENERATED_AUDIO)
    result = cleanup.clear_categories([StorageCategory.GENERATED_AUDIO], project_id="p1")
    assert target.exists() and str(target) in result.skipped_active


def test_generated_audio_reference_protection_and_unreferenced_cleanup(tmp_path):
    paths = make_paths(tmp_path); cache = CacheService(paths)
    protected = write(cache.project_category_root(StorageCategory.GENERATED_AUDIO,"p1") / "used.wav", b"used")
    stale = write(cache.project_category_root(StorageCategory.GENERATED_AUDIO,"p1") / "old.wav", b"old")
    cleanup = CleanupService(cache, paths, generated_audio_referenced=lambda p,pid:p.name == "used.wav")
    result = cleanup.clear_categories([StorageCategory.GENERATED_AUDIO], project_id="p1")
    assert protected.exists() and not stale.exists()
    assert str(protected) in result.skipped_protected


def test_clear_all_cache_excludes_models_recovery_exports_project_media_and_assets(tmp_path):
    paths = make_paths(tmp_path); cache = CacheService(paths)
    safe = [
        write(cache.category_root(StorageCategory.PREVIEW_CACHE)/"a.bin", b"a"),
        write(cache.category_root(StorageCategory.THUMBNAIL_CACHE)/"b.bin", b"b"),
        write(cache.category_root(StorageCategory.RENDER_TEMP)/"c.bin", b"c"),
    ]
    protected = [
        write(paths.models/"model.bin", b"model"),
        write(paths.recovery/"snapshot.spvrecovery", b"recovery"),
        write(paths.exports/"final.mp4", b"export"),
        write(paths.assets/"source.mp4", b"asset"),
        write(tmp_path/"project"/"media"/"source.mp4", b"media"),
    ]
    cleanup = CleanupService(cache, paths)
    result = cleanup.clear_all_cache()
    assert all(not x.exists() for x in safe)
    assert all(x.exists() for x in protected)
    assert result.freed_bytes == 3


def test_recovery_model_export_categories_refused_even_if_requested(tmp_path):
    paths, cache, cleanup, _ = services(tmp_path)
    for category in (StorageCategory.RECOVERY_DATA,StorageCategory.AI_MODELS,StorageCategory.FINAL_EXPORTS,StorageCategory.PROJECT_MEDIA):
        plan=cleanup.preview_cleanup([category])
        assert category.value in plan.skipped_protected and not plan.entries


def test_old_logs_cleanup_preserves_current_log(tmp_path):
    paths = make_paths(tmp_path); cache = CacheService(paths)
    old = write(paths.logs/"old.log", b"old"); current=write(paths.logs/"current.log", b"current")
    old_time=time.time()-20*86400;os.utime(old,(old_time,old_time));os.utime(current,(old_time,old_time))
    cleanup=CleanupService(cache,paths,current_log_provider=lambda:current)
    result=cleanup.cleanup_old_logs(retention_days=14)
    assert not old.exists() and current.exists() and str(current) in result.skipped_active


def test_lru_selects_oldest_safe_and_excludes_protected(tmp_path):
    paths, cache, cleanup, _ = services(tmp_path)
    root=cache.category_root(StorageCategory.PREVIEW_CACHE)
    a=CacheEntry(root/"a",StorageCategory.PREVIEW_CACHE,size_bytes=60,last_accessed_at="2026-01-01")
    b=CacheEntry(root/"b",StorageCategory.PREVIEW_CACHE,size_bytes=60,last_accessed_at="2026-01-02")
    protected=CacheEntry(root/"p",StorageCategory.PREVIEW_CACHE,size_bytes=100,last_accessed_at="2020-01-01",protected=True)
    plan=cleanup.lru_plan(maximum_bytes=120,entries=[a,b,protected])
    assert protected.path not in [x.path for x in plan.entries]
    assert a.path in [x.path for x in plan.entries]
    assert str(protected.path) in plan.skipped_protected


def test_cache_location_change_and_migration(tmp_path):
    paths=make_paths(tmp_path);cache=CacheService(paths);old=cache.root
    write(cache.category_root(StorageCategory.PREVIEW_CACHE)/"p.bin",b"preview")
    destination=tmp_path/"other"/"cache2"
    moved=CacheMigrationService(cache).migrate(destination,mode="move")
    assert moved == destination.resolve() and cache.root == destination.resolve()
    assert (destination/"preview"/"p.bin").is_file() and not old.exists()
    saved=json.loads((paths.settings/"phase29_storage.json").read_text())
    assert Path(saved["cacheRoot"]) == destination.resolve()


def test_cache_migration_failure_rolls_back(tmp_path):
    paths=make_paths(tmp_path);cache=CacheService(paths);old=cache.root
    source=write(cache.category_root(StorageCategory.PREVIEW_CACHE)/"p.bin",b"preview")
    destination=tmp_path/"new-cache"
    def fail(_src,_dst): raise OSError("copy failed")
    with pytest.raises(CacheMigrationFailed):CacheMigrationService(cache).migrate(destination,mode="move",copier=fail)
    assert cache.root == old and source.exists()
    prefs=cache.preferences;assert Path(prefs["cacheRoot"]) == old


def test_unsafe_cache_roots_rejected(tmp_path):
    paths=make_paths(tmp_path);cache=CacheService(paths)
    with pytest.raises(CachePathUnsafe):cache.validate_root(Path(Path.cwd().anchor),create=False)
    with pytest.raises(CachePathUnsafe):cache.validate_root(cache.source_root,create=False)
    with pytest.raises(CachePathUnsafe):cache.validate_root(paths.root,create=False)


def test_path_traversal_cleanup_rejected(tmp_path):
    paths=make_paths(tmp_path);cache=CacheService(paths);cleanup=CleanupService(cache,paths)
    outside=write(tmp_path/"important.file",b"important")
    malicious=CacheEntry(cache.root/"preview"/".."/".."/"important.file",StorageCategory.PREVIEW_CACHE,size_bytes=outside.stat().st_size)
    plan=CleanupPlan(reason="malicious");plan.add(malicious)
    result=cleanup.execute(plan)
    assert outside.exists() and str(malicious.path) in result.skipped_unsafe


def test_canonical_containment_accepts_inside_rejects_outside(tmp_path):
    paths=make_paths(tmp_path);cache=CacheService(paths)
    inside=cache.root/"preview"/"x.bin"
    assert cache.assert_contained(inside)==inside.resolve(strict=False)
    with pytest.raises(CachePathUnsafe):cache.assert_contained(cache.root/".."/"settings"/"settings.json")


def test_symlink_escape_does_not_delete_outside_file(tmp_path):
    paths=make_paths(tmp_path);cache=CacheService(paths);cleanup=CleanupService(cache,paths)
    outside=write(tmp_path/"outside.txt",b"keep")
    link=cache.category_root(StorageCategory.PREVIEW_CACHE)/"escape.txt"
    try:link.symlink_to(outside)
    except (OSError,NotImplementedError):pytest.skip("symlink unavailable")
    plan=cleanup.preview_cleanup([StorageCategory.PREVIEW_CACHE])
    assert str(link) in plan.skipped_unsafe
    cleanup.execute(plan)
    assert outside.read_bytes()==b"keep"


def test_orphan_cache_detection(tmp_path):
    paths=make_paths(tmp_path);cache=CacheService(paths);cleanup=CleanupService(cache,paths,project_provider=lambda:[])
    orphan=write(cache.project_category_root(StorageCategory.PREVIEW_CACHE,"missing-project")/"x.bin",b"x")
    old=time.time()-3*86400;os.utime(orphan,(old,old))
    plan=cleanup.orphan_plan(existing_project_ids=set(),minimum_age_seconds=86400)
    assert orphan in [x.path for x in plan.entries]


def test_missing_cache_folder_recreated_and_regeneration(tmp_path):
    paths=make_paths(tmp_path);cache=CacheService(paths)
    import shutil
    shutil.rmtree(cache.root)
    cache.ensure_structure()
    assert cache.category_root(StorageCategory.PREVIEW_CACHE).is_dir()
    target=cache.category_root(StorageCategory.PREVIEW_CACHE)/"rebuilt.bin"
    cache.regenerate_missing(target,lambda p:p.write_bytes(b"rebuilt"),category=StorageCategory.PREVIEW_CACHE)
    assert target.read_bytes()==b"rebuilt"


def test_thumbnail_and_preview_cache_keys_are_stable_and_change_with_inputs(tmp_path):
    paths=make_paths(tmp_path);cache=CacheService(paths)
    t1=cache.thumbnail_key("mediafp","320x180");t2=cache.thumbnail_key("mediafp","320x180")
    assert t1==t2 and t1!=cache.thumbnail_key("changed","320x180")
    p1=cache.preview_key(source_fingerprint="s",scene_fingerprint="scene",subtitle_fingerprint="sub",audio_fingerprint="a",size="720p")
    p2=cache.preview_key(source_fingerprint="s",scene_fingerprint="scene2",subtitle_fingerprint="sub",audio_fingerprint="a",size="720p")
    assert p1!=p2


def test_invalidation_scopes_source_fingerprint(tmp_path):
    paths=make_paths(tmp_path);cache=CacheService(paths)
    a_dir=cache.category_root(StorageCategory.PREVIEW_CACHE)/"a";a=write(a_dir/"a.bin")
    b_dir=cache.category_root(StorageCategory.PREVIEW_CACHE)/"b";b=write(b_dir/"b.bin")
    cache.write_manifest(a_dir,{"sourceFingerprint":"source-a"});cache.write_manifest(b_dir,{"sourceFingerprint":"source-b"})
    assert cache.invalidate(StorageCategory.PREVIEW_CACHE,source_fingerprint="source-a")==[a]


def test_disk_monitor_normal_low_critical_states():
    class U:
        def __init__(self,total,free):self.total=total;self.free=free;self.used=total-free
    total=100*1024**3
    monitor=DiskMonitorService(disk_usage=lambda _p:U(total,50*1024**3))
    assert monitor.check("/").state==DiskState.NORMAL
    monitor.disk_usage=lambda _p:U(total,8*1024**3)
    assert monitor.check("/").state==DiskState.LOW
    monitor.disk_usage=lambda _p:U(total,2*1024**3)
    assert monitor.check("/").state==DiskState.CRITICAL
    with pytest.raises(DiskSpaceCritical):monitor.require_space("/",operation="render")


def test_cleanup_dry_run_does_not_delete_and_result_summary(tmp_path):
    paths=make_paths(tmp_path);cache=CacheService(paths);cleanup=CleanupService(cache,paths)
    target=write(cache.category_root(StorageCategory.PREVIEW_CACHE)/"x.bin",b"123")
    plan=cleanup.clear_all_cache(dry_run=True)
    assert target.exists() and plan.estimated_bytes==3
    result=cleanup.execute(plan);assert not target.exists() and result.freed_bytes==3 and result.deleted


def test_project_cache_clear_preserves_media_script_export(tmp_path):
    paths=make_paths(tmp_path);cache=CacheService(paths)
    project=tmp_path/"Projects"/"p1";project.mkdir(parents=True)
    safe=write(project/"cache"/"preview.bin",b"cache");thumb=write(project/"thumbnails"/"thumb.jpg",b"thumb")
    media=write(project/"media"/"video.mp4",b"media");script=write(project/"project.json",b"{}")
    export=write(project/"renders"/"final.mp4",b"final")
    cleanup=CleanupService(cache,paths,project_provider=lambda:[{"project_id":"p1","path":str(project)}])
    cleanup.clear_project_cache("p1")
    assert not safe.exists() and not thumb.exists()
    assert media.exists() and script.exists() and export.exists()

@pytest.mark.parametrize("name", ["ខ្មែរ/ឃ្លាំង", "ไทย/แคช", "Việt Nam/bộ nhớ đệm"])
def test_unicode_cache_paths_cleanup(tmp_path,name):
    paths=make_paths(tmp_path);cache=CacheService(paths);cleanup=CleanupService(cache,paths)
    target=write(cache.category_root(StorageCategory.PREVIEW_CACHE)/name/"ទិន្នន័យ.bin",b"abc")
    result=cleanup.clear_categories([StorageCategory.PREVIEW_CACHE])
    assert not target.exists() and result.freed_bytes==3


def test_restart_persistence_of_cache_preferences(tmp_path,monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME",str(tmp_path/"xdg"))
    first=AppPaths.discover();first.ensure();cache=CacheService(first)
    new=tmp_path/"ខ្មែរ-cache";cache.set_cache_root(new);cache.update_preferences(maximumCacheBytes=10*1024**3,automaticCleanup="conservative")
    second=AppPaths.discover();assert second.cache==new.resolve()
    again=CacheService(second);assert again.preferences["maximumCacheBytes"]==10*1024**3 and again.preferences["automaticCleanup"]=="conservative"


def test_stale_startup_cleanup_uses_category_specific_age(tmp_path):
    paths=make_paths(tmp_path);cache=CacheService(paths);cleanup=CleanupService(cache,paths);stale=StaleFileService(cleanup,cache)
    old=write(cache.category_root(StorageCategory.RENDER_TEMP)/"old.tmp",b"x");fresh=write(cache.category_root(StorageCategory.RENDER_TEMP)/"fresh.tmp",b"x")
    old_time=time.time()-30*3600;os.utime(old,(old_time,old_time))
    result=stale.startup_cleanup()
    assert not old.exists() and fresh.exists() and result.freed_bytes>=1


def test_large_cache_lru_planning_100k_entries_practical(tmp_path):
    paths=make_paths(tmp_path);cache=CacheService(paths);cleanup=CleanupService(cache,paths)
    root=cache.category_root(StorageCategory.PREVIEW_CACHE)
    entries=[CacheEntry(root/f"{i:06}.bin",StorageCategory.PREVIEW_CACHE,size_bytes=1024,last_accessed_at=f"2026-01-{1+(i%28):02}T00:00:00") for i in range(100_000)]
    start=time.monotonic();plan=cleanup.lru_plan(maximum_bytes=50_000*1024,entries=entries);elapsed=time.monotonic()-start
    assert plan.estimated_bytes>=50_000*1024 and len(plan.entries)>=50_000
    assert elapsed<20.0


def test_phase29_runtime_centralizes_batch_and_render_disk_guards():
    source=Path("app/phase29_runtime.py").read_text(encoding="utf-8")
    assert "scheduler._disk_ok=disk_ok" in source
    assert "disk.require_space" in source
    assert "DiskMonitorService" in source


def test_storage_ui_is_phase28_style_and_exposes_required_actions():
    page=Path("ui/qml/storage/StoragePage.qml").read_text(encoding="utf-8")
    overview=Path("ui/qml/storage/StorageOverview.qml").read_text(encoding="utf-8")
    project=Path("ui/qml/storage/ProjectStorageList.qml").read_text(encoding="utf-8")
    dialog=Path("ui/qml/storage/CleanupDialog.qml").read_text(encoding="utf-8")
    assert "Storage Used" in overview and "Recalculate" in overview
    assert "Clear Cache" in page and "Cache Location" in page and "Automatic Cleanup" in page
    assert "reuseItems: true" in project
    assert "Projects, source media, models, recovery copies and final exports" in dialog


def test_asset_library_thumbnail_cache_clear_preserves_managed_asset(tmp_path):
    paths = make_paths(tmp_path); cache = CacheService(paths)
    asset_root = paths.assets
    source = write(asset_root / "video" / "managed.mp4", b"source-media")
    thumb = write(asset_root / "thumbnails" / "asset.jpg", b"thumb")
    cleanup = CleanupService(cache, paths, asset_root_provider=lambda: asset_root)
    result = cleanup.clear_all_cache()
    assert source.exists()
    assert not thumb.exists()
    assert str(thumb.resolve()) in [str(Path(x).resolve()) for x in result.deleted]


def test_asset_storage_separates_source_and_thumbnail_cache(tmp_path):
    paths = make_paths(tmp_path); cache = CacheService(paths)
    asset_root = paths.assets
    write(asset_root / "video" / "managed.mp4", b"s" * 11)
    write(asset_root / "thumbnails" / "asset.jpg", b"t" * 7)
    usage = StorageUsageService(paths, cache, asset_root_provider=lambda: asset_root)
    result = usage.recalculate(force=True)
    by_category = {row["category"]: row for row in result["categories"]}
    assert by_category[StorageCategory.ASSET_LIBRARY.value]["sizeBytes"] == 11
    assert by_category[StorageCategory.ASSET_THUMBNAIL_CACHE.value]["sizeBytes"] == 7
    assert result["totalOwnedBytes"] == 18


def test_batch_dry_run_uses_central_disk_monitor(tmp_path):
    from services.batch_validation_service import BatchValidationService
    class Variants:
        def expand(self, rows, config): return []
    class CriticalMonitor:
        def check(self, path, *, estimated_bytes=0, label=""):
            return SimpleNamespace(state=DiskState.CRITICAL, free_bytes=2 * 1024**3)
    service = BatchValidationService(SimpleNamespace(), Variants(), disk_monitor=CriticalMonitor())
    summary = service.dry_run(
        batch_name="Disk test", template=SimpleNamespace(placeholders=[]), rows=[], mappings=[],
        variant_config=SimpleNamespace(source_language="en"), output_root=tmp_path / "outputs", settings={}
    )
    assert summary.disk_ok is False
    assert summary.free_bytes == 2 * 1024**3
