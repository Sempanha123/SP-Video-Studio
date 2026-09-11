from __future__ import annotations

import json
import sqlite3
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.paths import AppPaths
from domain.asset import Asset
from domain.performance import PerformanceProfile
from media.probe import FFprobeService
from services.ai_resource_manager import AIResourceManager
from services.asset_search_service import AssetSearchService
from services.audio_waveform_service import AudioWaveformService
from services.cache_service import CacheService
from services.performance_profile_service import PerformanceProfileService
from services.performance_telemetry_service import PerformanceTelemetryService
from services.preview_request_service import PreviewRequestService
from services.subtitle_lookup_service import SubtitleLookupService
from services.thumbnail_request_service import ThumbnailRequestService
from storage.database import SQLiteDatabase
from storage.migrations.m022_create_asset_library import migrate as migrate_assets
from storage.migrations.m023_create_batch_factory import migrate as migrate_batch
from storage.migrations.m026_performance_indexes import migrate as migrate_perf
from storage.repositories.asset_repository import AssetRepository
from storage.repositories.batch_item_repository import BatchItemRepository
from workers.worker_pool import WorkerPool, WorkerPriority


def make_paths(tmp_path:Path)->AppPaths:
    root=tmp_path/'MMOVideoStudio';p=AppPaths(root=root,models=root/'models',cache=root/'cache',temp=root/'temp',logs=root/'logs',settings=root/'settings',downloads=root/'downloads');p.ensure();return p


def asset_repo(tmp_path:Path,count:int=1000):
    db=SQLiteDatabase(tmp_path/'assets.db')
    with db.connect() as c,c:
        c.execute('CREATE TABLE projects(id TEXT PRIMARY KEY)');c.execute('CREATE TABLE media_assets(id TEXT PRIMARY KEY,project_id TEXT)');migrate_assets(c)
        rows=[]
        for i in range(count):
            aid=f'a{i:04d}';rows.append((aid,f'Asset {i:04d}','video','broll','',1,f'video/{aid}.mp4','',1000,1920,1080,30.0,'h264','aac',48000,2,1000,'video/mp4','.mp4',f'fp{i}','sha256',0,f'a{i}.mp4','2026-01-01','2026-01-01','',0,'ready',f'notes {i}','en','{}'))
        c.executemany('''INSERT INTO assets(id,name,type,subtype,file_path,managed,relative_path,thumbnail_path,duration_ms,width,height,fps,video_codec,audio_codec,sample_rate,channels,file_size,mime_type,extension,fingerprint,fingerprint_kind,source_mtime_ns,original_filename,created_at,updated_at,last_used_at,favorite,status,notes,spoken_language,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',rows)
        c.executemany('INSERT INTO asset_tags(name,normalized_name) VALUES(?,?)',[(f'Tag{i}',f'tag{i}') for i in range(10)])
        ids=[r['id'] for r in c.execute('SELECT id FROM asset_tags ORDER BY id')]
        c.executemany('INSERT INTO asset_tag_items(tag_id,asset_id) VALUES(?,?)',[(ids[i%10],f'a{i:04d}') for i in range(count)])
    return db,AssetRepository(db,tmp_path/'library')


def test_asset_1000_bulk_search_has_no_n_plus_one(tmp_path,monkeypatch):
    _,repo=asset_repo(tmp_path);search=AssetSearchService(repo)
    monkeypatch.setattr(repo,'tags',lambda *_:(_ for _ in ()).throw(AssertionError('N+1 tags call')))
    monkeypatch.setattr(repo,'asset_collections',lambda *_:(_ for _ in ()).throw(AssertionError('N+1 collection call')))
    monkeypatch.setattr(repo,'usage_count',lambda *_:(_ for _ in ()).throw(AssertionError('N+1 usage call')))
    start=time.perf_counter();rows=search.search(query='Tag5');elapsed=time.perf_counter()-start
    assert len(rows)==100 and elapsed<1.0


def test_asset_bulk_search_page_and_unicode(tmp_path):
    _,repo=asset_repo(tmp_path);search=AssetSearchService(repo)
    page=search.search_rows(query='Asset',limit=160);assert len(page)==160
    assert search.count(query='Asset')==1000


def test_ffprobe_repeated_and_concurrent_requests_deduplicate(tmp_path):
    source=tmp_path/'clip.mp4';source.write_bytes(b'x');calls={'n':0};lock=threading.Lock()
    payload=json.dumps({'streams':[{'codec_type':'video','codec_name':'h264','width':10,'height':10,'avg_frame_rate':'30/1'}],'format':{'duration':'1'}})
    def runner(*a,**k):
        with lock:calls['n']+=1
        time.sleep(.02);return SimpleNamespace(returncode=0,stdout=payload,stderr='')
    service=FFprobeService(lambda:'ffprobe',runner=runner)
    with ThreadPoolExecutor(max_workers=10) as pool:list(pool.map(lambda _:service.probe(source,'video'),range(10)))
    for _ in range(10):service.probe(source,'video')
    assert calls['n']==1 and service.cache_info()['entries']==1


def test_ffprobe_cache_invalidates_when_file_changes(tmp_path):
    source=tmp_path/'clip.mp4';source.write_bytes(b'a');calls={'n':0}
    payload=json.dumps({'streams':[{'codec_type':'video','codec_name':'h264','width':10,'height':10,'avg_frame_rate':'30/1'}],'format':{'duration':'1'}})
    def runner(*a,**k):calls['n']+=1;return SimpleNamespace(returncode=0,stdout=payload,stderr='')
    service=FFprobeService(lambda:'ffprobe',runner=runner)
    service.probe(source,'video');time.sleep(.001);source.write_bytes(b'ab');service.probe(source,'video')
    assert calls['n']==2


def test_ffprobe_memory_cache_is_bounded(tmp_path):
    payload=json.dumps({'streams':[{'codec_type':'audio','codec_name':'aac'}],'format':{'duration':'1'}})
    service=FFprobeService(lambda:'ffprobe',runner=lambda *a,**k:SimpleNamespace(returncode=0,stdout=payload,stderr=''),cache_entries=8)
    for i in range(20):
        p=tmp_path/f'{i}.wav';p.write_bytes(bytes([i]));service.probe(p,'audio')
    assert service.cache_info()['entries']<=8


def test_waveform_same_audio_deduplicates_concurrent_generation(tmp_path):
    paths=make_paths(tmp_path);cache=CacheService(paths);source=tmp_path/'voice.wav';source.write_bytes(b'x');svc=AudioWaveformService(cache)
    calls={'n':0};guard=threading.Lock()
    def samples(_):
        with guard:calls['n']+=1
        time.sleep(.03);return ([0,100,-100]*500,8000)
    svc._samples=samples
    with ThreadPoolExecutor(max_workers=10) as pool:rows=list(pool.map(lambda _:svc.generate(source,buckets=100),range(10)))
    assert calls['n']==1 and sum(bool(x['cacheHit']) for x in rows)==9


def test_waveform_multiresolution_levels_use_distinct_cache(tmp_path):
    paths=make_paths(tmp_path);cache=CacheService(paths);source=tmp_path/'voice.wav';source.write_bytes(b'x');svc=AudioWaveformService(cache);svc._samples=lambda _ :([0,100,-100]*5000,8000)
    low=svc.generate_level(source,'low');high=svc.generate_level(source,'high')
    assert len(low['buckets'])<=320 and len(high['buckets'])>len(low['buckets'])


def test_worker_pool_prioritizes_interactive_queued_work():
    pool=WorkerPool(max_workers=1,max_pending=16);gate=threading.Event();order=[]
    try:
        first=pool.submit_priority(WorkerPriority.NORMAL,lambda:(gate.wait(),order.append('running')))
        time.sleep(.01)
        bg=pool.submit_priority(WorkerPriority.BACKGROUND,lambda:order.append('background'))
        interactive=pool.submit_priority(WorkerPriority.INTERACTIVE,lambda:order.append('interactive'))
        gate.set();first.result(1);interactive.result(1);bg.result(1)
        assert order[-2:]==['interactive','background']
    finally:pool.shutdown()


def test_worker_pool_threads_are_bounded_and_shutdown():
    before=threading.active_count();pool=WorkerPool(max_workers=3,max_pending=20)
    futures=[pool.submit(lambda x=x:x) for x in range(20)];assert [f.result(1) for f in futures]==list(range(20));assert pool.stats()['workers']==3
    pool.shutdown();time.sleep(.02);assert threading.active_count()<=before+1


class _Thumb:
    def __init__(self):self.calls=0
    def generate(self,*a,**k):self.calls+=1;time.sleep(.03);return Path(a[2])


def test_thumbnail_dedup_same_key_ten_requests(tmp_path):
    pool=WorkerPool(max_workers=3);thumb=_Thumb();service=ThumbnailRequestService(thumb,pool);source=tmp_path/'a.jpg';source.write_bytes(b'x');dest=tmp_path/'t.jpg'
    try:
        requests=[service.request(f'card-{i}','image',source,dest,priority='interactive') for i in range(10)]
        [x.future.result(1) for x in requests];assert thumb.calls==1
    finally:pool.shutdown()


def test_offscreen_thumbnail_request_becomes_stale(tmp_path):
    pool=WorkerPool(max_workers=1);thumb=_Thumb();service=ThumbnailRequestService(thumb,pool);source=tmp_path/'a.jpg';source.write_bytes(b'x');dest=tmp_path/'t.jpg'
    try:
        req=service.request('card','image',source,dest);service.cancel_owner('card');req.future.result(1);assert not service.is_current(req)
    finally:pool.shutdown()


def test_preview_late_result_is_rejected():
    pool=WorkerPool(max_workers=2);service=PreviewRequestService(pool);gate=threading.Event()
    try:
        a=service.request('scene',lambda:(gate.wait(),'A')[1]);b=service.request('scene',lambda:'B');assert b.future.result(1)=='B';gate.set();assert a.future.result(1)=='A';assert not service.is_current(a) and service.is_current(b)
    finally:pool.shutdown()


class Cue:
    def __init__(self,start,end):self.start_ms=start;self.end_ms=end


def test_subtitle_lookup_5000_cues_is_indexed_and_correct():
    cues=[Cue(i*1000,i*1000+900) for i in range(5000)];svc=SubtitleLookupService();svc.build('t',cues,'v1')
    for i in (0,1,500,2500,4999):assert svc.active('t',i*1000+100)==[cues[i]]
    assert svc.active('t',499)==[cues[0]] and svc.active('t',999)==[]


def test_subtitle_index_cache_is_bounded():
    svc=SubtitleLookupService(max_tracks=4)
    for i in range(10):svc.build(str(i),[Cue(0,1000)],i)
    assert len(svc._indexes)<=4


def test_batch_1000_summary_uses_aggregate_query(tmp_path):
    db=SQLiteDatabase(tmp_path/'batch.db')
    with db.connect() as c,c:
        migrate_batch(c);c.execute("INSERT INTO batches(id,name,template_id,status,created_at,updated_at,output_directory) VALUES('b','B','t','running','x','x',?)",(str(tmp_path),))
        rows=[]
        for i in range(1000):
            status='completed' if i<400 else ('failed' if i<450 else ('rendering' if i<500 else 'pending'))
            rows.append((f'i{i}','b',i,f'key{i}',status,'render',i/1000,'','','','','',0,'x','x','','','{}','{}','{}',''))
        c.executemany('''INSERT INTO batch_items(id,batch_id,row_index,item_key,status,current_stage,progress,project_id,variant_key,output_path,error_code,error_message,attempt_count,created_at,updated_at,started_at,completed_at,input_data_json,resolved_data_json,metadata_json,fingerprint) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',rows)
    summary=BatchItemRepository(db).summary_for_batch('b')
    assert summary['total']==1000 and summary['counts']['running']==50 and summary['counts']['failed']==50


def test_performance_indexes_created_only_for_available_schema(tmp_path):
    raw=sqlite3.connect(tmp_path/'p.db')
    try:
        raw.executescript('CREATE TABLE assets(id TEXT,created_at TEXT,last_used_at TEXT); CREATE TABLE batch_items(batch_id TEXT,status TEXT,row_index INTEGER,item_key TEXT); CREATE TABLE subtitle_cues(track_id TEXT,start_ms INTEGER,end_ms INTEGER);')
        migrate_perf(raw);names={r[0] for r in raw.execute("SELECT name FROM sqlite_master WHERE type='index'")}
        assert {'idx_assets_created_perf','idx_batch_items_batch_status_perf','idx_subtitle_cues_playback_perf'}<=names
    finally:raw.close()


def test_profile_persistence_and_preview_quality(tmp_path):
    service=PerformanceProfileService(tmp_path);service.set_profile('low_memory');service.set_preview_quality('performance');service.set_worker_limit(3)
    reopened=PerformanceProfileService(tmp_path);policy=reopened.preview_policy(active_layers=5,source_height=2160)
    assert reopened.profile=='low_memory' and reopened.worker_limit==3 and policy.proxy_height<=540 and not policy.expensive_preview_effects


def test_quality_preview_does_not_modify_export_settings(tmp_path):
    service=PerformanceProfileService(tmp_path);service.set_preview_quality('quality');policy=service.preview_policy(active_layers=5,source_height=2160)
    assert policy.proxy_height<=1080 and policy.expensive_preview_effects
    root=Path(__file__).resolve().parents[1];assert 'phase31' not in (root/'rendering/renderer.py').read_text(encoding='utf-8').casefold()


def test_cpu_only_profile_and_telemetry_work(tmp_path):
    profile=PerformanceProfileService(tmp_path);profile.set_profile('balanced');pool=WorkerPool(max_workers=2)
    try:
        snap=PerformanceTelemetryService(pool,profile).snapshot();assert snap.thread_count>=1 and snap.process_ram_bytes>=0 and profile.recommended_workers()>=1
    finally:pool.shutdown()


def test_ai_resource_manager_reuses_current_model_and_releases_incompatible():
    state={'tts':True,'stt':True};unloads=[]
    manager=AIResourceManager('balanced')
    manager.register('tts',lambda:(unloads.append('tts'),state.__setitem__('tts',False)),lambda:False,lambda:state['tts'])
    manager.register('stt',lambda:(unloads.append('stt'),state.__setitem__('stt',False)),lambda:False,lambda:state['stt'])
    manager.prepare('tts','cuda:0');assert unloads==['stt']
    manager.prepare('tts','cuda:0');assert unloads==['stt']


def test_ai_oom_recovery_retries_exactly_once():
    state={'other':True};manager=AIResourceManager('balanced');released=[]
    manager.register('other',lambda:(released.append('other'),state.__setitem__('other',False)),lambda:False,lambda:state['other'])
    calls={'n':0}
    def op():
        calls['n']+=1
        if calls['n']==1:raise RuntimeError('CUDA out of memory')
        return 'ok'
    assert manager.run_with_oom_retry('tts','cuda:0',op)=='ok' and calls['n']==2 and released==['other']


def test_main_qml_uses_single_lazy_page_loader():
    text=(Path(__file__).resolve().parents[1]/'ui/qml/Main.qml').read_text(encoding='utf-8')
    assert 'Loader {id:pageLoader' in text and 'pageSource(window.currentPage)' in text


def test_large_list_qml_is_virtualized_debounced_and_thumbnail_bounded():
    root=Path(__file__).resolve().parents[1]
    grid=(root/'ui/qml/assets/AssetGrid.qml').read_text(encoding='utf-8');card=(root/'ui/qml/assets/AssetCard.qml').read_text(encoding='utf-8');filters=(root/'ui/qml/assets/AssetFilterBar.qml').read_text(encoding='utf-8');batch=(root/'ui/qml/batch/BatchQueue.qml').read_text(encoding='utf-8')
    assert 'GridView' in grid and 'reuseItems: true' in grid and 'loadMoreRequested' in grid
    assert 'sourceSize.width: 320' in card and 'asynchronous: true' in card
    assert 'interval: 220' in filters and 'interval: 220' in batch and 'ListView' in batch and 'reuseItems: true' in batch


def test_timeline_drag_persistence_remains_release_based():
    # Full source file is not reconstructed in this test workspace; Phase 31 must not
    # add hot-loop persistence to TimelineEditor.
    text=(Path(__file__).resolve().parents[1]/'ui/qml/timeline/TimelineEditor.qml').read_text(encoding='utf-8')
    assert 'onContentXChanged' not in text or 'save' not in text.casefold()


def test_performance_runtime_is_layered_and_phase32_absent():
    root=Path(__file__).resolve().parents[1];runtime=(root/'app/phase31_runtime.py').read_text(encoding='utf-8')
    assert 'app.phase30_runtime' in runtime and 'SubtitleLookupService' in runtime and 'PerformanceProfileService' in runtime
    assert not (root/'app/phase32_runtime.py').exists()


def test_worker_runtime_limit_throttles_active_tasks():
    pool=WorkerPool(max_workers=3,max_pending=20);pool.set_active_limit(1);gate=threading.Event();started=[];lock=threading.Lock()
    def work(i):
        with lock:started.append(i)
        gate.wait(.2)
        return i
    try:
        futures=[pool.submit(work,i) for i in range(3)]
        time.sleep(.03)
        assert len(started)==1 and pool.stats()['limit']==1
        gate.set();assert sorted(f.result(1) for f in futures)==[0,1,2]
    finally:pool.shutdown()


def test_worker_queue_saturation_does_not_block_submitter():
    pool=WorkerPool(max_workers=1,max_pending=1);gate=threading.Event()
    try:
        first=pool.submit(lambda:gate.wait(.3));time.sleep(.01)
        second=pool.submit(lambda:1);start=time.perf_counter();third=pool.submit(lambda:2);elapsed=time.perf_counter()-start
        assert elapsed<.05 and third.done()
        with pytest.raises(RuntimeError):third.result()
        gate.set();first.result(1);second.result(1)
    finally:pool.shutdown()


def test_low_memory_profile_releases_idle_heavy_model():
    state={'tts':True};released=[];manager=AIResourceManager('low_memory',idle_timeout_seconds=10)
    manager.register('tts',lambda:(released.append('tts'),state.__setitem__('tts',False)),lambda:False,lambda:state['tts'])
    manager.touch('tts');assert manager.release_idle()==['tts'] and released==['tts']


def test_asset_controller_initialization_does_not_force_filesystem_scan():
    root=Path(__file__).resolve().parents[1]
    text=(root/'ui/controllers/asset_library_controller.py').read_text(encoding='utf-8')
    init=text.split('def __init__',2)[-1].split('@Property',1)[0]
    assert 'self.refresh()' not in init and 'self._refresh_rows()' in init


def test_batch_queue_refresh_rate_is_throttled_below_20hz():
    root=Path(__file__).resolve().parents[1]
    text=(root/'ui/qml/batch/BatchFactory.qml').read_text(encoding='utf-8')
    assert 'interval: 900' in text


def test_phase31_performance_settings_control_live_worker_pool():
    root=Path(__file__).resolve().parents[1]
    controller=(root/'ui/controllers/performance_controller.py').read_text(encoding='utf-8')
    runtime=(root/'app/phase31_runtime.py').read_text(encoding='utf-8')
    assert 'set_active_limit' in controller and 'worker_pool' in controller
    assert 'worker_pool,parent' in runtime


def test_performance_indexes_cover_hot_large_project_paths(tmp_path):
    raw=sqlite3.connect(tmp_path/'perf.db')
    try:
        raw.executescript('''
        CREATE TABLE assets(id TEXT,created_at TEXT,last_used_at TEXT);
        CREATE TABLE asset_usage(asset_id TEXT,project_id TEXT);
        CREATE TABLE batch_items(batch_id TEXT,status TEXT,row_index INTEGER,item_key TEXT);
        CREATE TABLE subtitle_cues(track_id TEXT,start_ms INTEGER,end_ms INTEGER);
        CREATE TABLE subtitle_words(cue_id TEXT,word_order INTEGER);
        CREATE TABLE scenes(project_id TEXT,scene_order INTEGER);
        CREATE TABLE speech_blocks(script_section_id TEXT,block_order INTEGER);
        CREATE TABLE transcript_segments(transcript_id TEXT,start_ms INTEGER,end_ms INTEGER);
        ''')
        migrate_perf(raw); names={r[0] for r in raw.execute("SELECT name FROM sqlite_master WHERE type='index'")}
        assert 'idx_asset_usage_asset_project_perf' in names and 'idx_scenes_project_order_perf' in names and 'idx_speech_blocks_section_order_perf' in names
    finally:raw.close()


def test_timeline_clip_delegates_are_windowed_to_visible_time_range():
    root=Path(__file__).resolve().parents[1]
    track=(root/'ui/qml/timeline/TimelineTrack.qml').read_text(encoding='utf-8')
    editor=(root/'ui/qml/timeline/TimelineEditor.qml').read_text(encoding='utf-8')
    assert 'property var visibleClips' in track and 'model: root.visibleClips' in track
    assert 'visibleStartMs:' in editor and 'visibleEndMs:' in editor and '/ 250' in editor


def test_subtitle_repository_lookup_indexes_ranges_without_loading_all_words(tmp_path):
    db=SQLiteDatabase(tmp_path/'subs.db')
    with db.connect() as c,c:
        c.execute('CREATE TABLE subtitle_cues(id TEXT PRIMARY KEY,track_id TEXT,start_ms INTEGER,end_ms INTEGER)')
        c.executemany('INSERT INTO subtitle_cues(id,track_id,start_ms,end_ms) VALUES(?,?,?,?)',[(f'c{i}','t',i*1000,i*1000+900) for i in range(1000)])
    class Repo:
        def __init__(self,database):self.database=database;self.cue_calls=0
        def cues(self,*_):raise AssertionError('full cue list must not be loaded for playback index')
        def cue(self,cid):
            self.cue_calls+=1
            with self.database.connect() as c:r=c.execute('SELECT * FROM subtitle_cues WHERE id=?',(cid,)).fetchone()
            return Cue(int(r['start_ms']),int(r['end_ms'])) if r else None
    repo=Repo(db);svc=SubtitleLookupService();first=svc.active_repository(repo,'t',123100,'v1');second=svc.active_repository(repo,'t',123200,'v1')
    assert len(first)==1 and len(second)==1 and repo.cue_calls==1
