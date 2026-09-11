from __future__ import annotations
import json, sqlite3, time
from contextlib import contextmanager
from pathlib import Path
import pytest

from domain.autosave_state import AutosaveStatus,ProjectAutosaveState
from domain.recovery_errors import AutosaveFailed,RecoverySnapshotCorrupt,RecoveryRestoreFailed
from services.autosave_service import AutosavePolicy,AutosaveService
from services.project_snapshot_codec import ProjectSnapshotCodec
from services.project_integrity_service import ProjectIntegrityService
from services.recovery_snapshot_service import RecoverySnapshotService
from services.recovery_service import RecoveryService
from services.interrupted_job_recovery_service import InterruptedJobRecoveryService
from services.temp_recovery_service import TempRecoveryService
from services.shutdown_service import ShutdownService
from storage.atomic_write import atomic_write_json
from storage.database import SQLiteDatabase
from storage.recovery_store import RecoveryStore
from storage.repositories.recovery_repository import RecoveryRepository
from storage.migrations.m023_create_batch_factory import migrate as migrate23
from storage.migrations.m024_create_autosave_recovery import migrate as migrate24


def schema(db:SQLiteDatabase,root:Path):
    root.mkdir(parents=True,exist_ok=True)
    with db.connect() as c:
        c.executescript('''
        CREATE TABLE projects(id TEXT PRIMARY KEY,title TEXT NOT NULL,project_path TEXT NOT NULL);
        CREATE TABLE media_assets(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,project_path TEXT NOT NULL,FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE);
        CREATE TABLE scripts(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,text TEXT NOT NULL DEFAULT '',FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE);
        CREATE TABLE script_sections(id TEXT PRIMARY KEY,script_id TEXT NOT NULL,content TEXT NOT NULL DEFAULT '',FOREIGN KEY(script_id) REFERENCES scripts(id) ON DELETE CASCADE);
        CREATE TABLE scenes(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,title TEXT NOT NULL DEFAULT '',FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE);
        CREATE TABLE scene_layers(id TEXT PRIMARY KEY,scene_id TEXT NOT NULL,x REAL NOT NULL DEFAULT 0,scale REAL NOT NULL DEFAULT 1,chroma_similarity REAL NOT NULL DEFAULT 0.2,FOREIGN KEY(scene_id) REFERENCES scenes(id) ON DELETE CASCADE);
        CREATE TABLE subtitle_tracks(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE);
        CREATE TABLE subtitle_cues(id TEXT PRIMARY KEY,track_id TEXT NOT NULL,text TEXT NOT NULL,start_ms INTEGER,end_ms INTEGER,FOREIGN KEY(track_id) REFERENCES subtitle_tracks(id) ON DELETE CASCADE);
        CREATE TABLE translations(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'draft',metadata_json TEXT NOT NULL DEFAULT '{}',FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE);
        CREATE TABLE translation_segments(id TEXT PRIMARY KEY,translation_id TEXT NOT NULL,translated_text TEXT NOT NULL DEFAULT '',FOREIGN KEY(translation_id) REFERENCES translations(id) ON DELETE CASCADE);
        CREATE TABLE speakers(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,name TEXT NOT NULL,voice_id TEXT NOT NULL DEFAULT '',FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE);
        CREATE TABLE speech_blocks(id TEXT PRIMARY KEY,script_section_id TEXT NOT NULL,speaker_id TEXT,text TEXT NOT NULL DEFAULT '',voice_override_id TEXT NOT NULL DEFAULT '',FOREIGN KEY(script_section_id) REFERENCES script_sections(id) ON DELETE CASCADE,FOREIGN KEY(speaker_id) REFERENCES speakers(id) ON DELETE SET NULL);
        CREATE TABLE timeline_tracks(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,name TEXT NOT NULL DEFAULT '',FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE);
        CREATE TABLE timeline_items(id TEXT PRIMARY KEY,track_id TEXT NOT NULL,start_ms INTEGER NOT NULL DEFAULT 0,FOREIGN KEY(track_id) REFERENCES timeline_tracks(id) ON DELETE CASCADE);
        CREATE TABLE news_projects(project_id TEXT PRIMARY KEY,brief TEXT NOT NULL DEFAULT '',FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE);
        CREATE TABLE news_claims(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,notes TEXT NOT NULL DEFAULT '',approved INTEGER NOT NULL DEFAULT 0,FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE);
        CREATE TABLE story_projects(project_id TEXT PRIMARY KEY,idea TEXT NOT NULL DEFAULT '',FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE);
        CREATE TABLE story_beats(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,beat_order INTEGER NOT NULL,description TEXT NOT NULL DEFAULT '',FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE);
        CREATE TABLE shorts_projects(project_id TEXT PRIMARY KEY,crop_json TEXT NOT NULL DEFAULT '{}',FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE);
        CREATE TABLE short_candidates(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,title TEXT NOT NULL DEFAULT '',FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE);
        CREATE TABLE render_jobs(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,status TEXT NOT NULL,output_path TEXT,error_message TEXT NOT NULL DEFAULT '',metadata_json TEXT NOT NULL DEFAULT '{}');
        CREATE TABLE transcripts(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,status TEXT NOT NULL,metadata_json TEXT NOT NULL DEFAULT '{}');
        CREATE TABLE dub_segments(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,audio_status TEXT NOT NULL,metadata_json TEXT NOT NULL DEFAULT '{}');
        ''')
        migrate23(c);migrate24(c);c.commit()


def make_env(tmp_path:Path):
    db=SQLiteDatabase(tmp_path/'app.db');schema(db,tmp_path/'p1');repo=RecoveryRepository(db);store=RecoveryStore(tmp_path/'recovery',retention=4,min_free_bytes=0);clock=[100.0]
    autosave=AutosaveService(repo,clock=lambda:clock[0]);codec=ProjectSnapshotCodec(db);integrity=ProjectIntegrityService(db);jobs=InterruptedJobRecoveryService(db,repo);snaps=RecoverySnapshotService(repo,store,codec,autosave,app_version='27');recovery=RecoveryService(repo,store,snaps,codec,autosave,integrity,jobs,app_version='27')
    project=tmp_path/'p1';project.mkdir(exist_ok=True);(project/'project.json').write_text(json.dumps({'title':'A','unicode':'ខ្មែរ ไทย Tiếng Việt'},ensure_ascii=False),encoding='utf-8')
    with db.connect() as c,c:
        c.execute('INSERT INTO projects VALUES(?,?,?)',('p1','Project A',str(project)))
    recovery.start_session();return db,repo,store,autosave,codec,snaps,recovery,clock


def populate_creative(db:SQLiteDatabase,tmp:Path):
    media=tmp/'p1'/'clip.mp4';media.write_bytes(b'video')
    with db.connect() as c,c:
        c.execute('INSERT INTO media_assets VALUES(?,?,?)',('m1','p1',str(media)))
        c.execute('INSERT INTO scripts VALUES(?,?,?)',('s1','p1','Version A'));c.execute('INSERT INTO script_sections VALUES(?,?,?)',('sec1','s1','ខ្មែរ A'))
        c.execute('INSERT INTO scenes VALUES(?,?,?)',('sc1','p1','Scene A'));c.execute('INSERT INTO scene_layers VALUES(?,?,?,?,?)',('l1','sc1',0.1,1.0,0.22))
        c.execute('INSERT INTO subtitle_tracks VALUES(?,?)',('st1','p1'));c.execute('INSERT INTO subtitle_cues VALUES(?,?,?,?,?)',('cue1','st1','ไทย A',100,900))
        c.execute('INSERT INTO translations VALUES(?,?,?,?)',('tr1','p1','draft','{}'));c.execute('INSERT INTO translation_segments VALUES(?,?,?)',('trs1','tr1','Tiếng Việt A'))
        c.execute('INSERT INTO speakers VALUES(?,?,?,?)',('sp1','p1','Reporter','voiceA'));c.execute('INSERT INTO speech_blocks VALUES(?,?,?,?,?)',('b1','sec1','sp1','Reporter A','voiceA'))
        c.execute('INSERT INTO timeline_tracks VALUES(?,?,?)',('tt1','p1','Video'));c.execute('INSERT INTO timeline_items VALUES(?,?,?)',('ti1','tt1',100))
        c.execute('INSERT INTO news_projects VALUES(?,?)',('p1','brief A'));c.execute('INSERT INTO news_claims VALUES(?,?,?,?)',('n1','p1','claim A',1))
        c.execute('INSERT INTO story_projects VALUES(?,?)',('p1','idea A'));c.execute('INSERT INTO story_beats VALUES(?,?,?,?)',('beat1','p1',0,'beat A'))
        c.execute('INSERT INTO shorts_projects VALUES(?,?)',('p1','{"x":0.4}'));c.execute('INSERT INTO short_candidates VALUES(?,?,?)',('sh1','p1','short A'))


def mutate_creative(db):
    with db.connect() as c,c:
        c.execute("UPDATE scripts SET text='Version B' WHERE id='s1'");c.execute("UPDATE script_sections SET content='ខ្មែរ B' WHERE id='sec1'")
        c.execute("UPDATE scene_layers SET x=.7,scale=1.3,chroma_similarity=.31 WHERE id='l1'");c.execute("UPDATE subtitle_cues SET text='ไทย B',start_ms=150,end_ms=950 WHERE id='cue1'")
        c.execute("UPDATE translation_segments SET translated_text='Tiếng Việt B' WHERE id='trs1'");c.execute("UPDATE speakers SET voice_id='voiceB' WHERE id='sp1'");c.execute("UPDATE speech_blocks SET text='Reporter B',voice_override_id='voiceB' WHERE id='b1'")
        c.execute("UPDATE timeline_items SET start_ms=333 WHERE id='ti1'");c.execute("UPDATE news_claims SET notes='claim B' WHERE id='n1'");c.execute("UPDATE news_projects SET brief='brief B' WHERE project_id='p1'")
        c.execute("UPDATE story_beats SET beat_order=2,description='beat B' WHERE id='beat1'");c.execute("UPDATE shorts_projects SET crop_json='{\"x\":0.8}' WHERE project_id='p1'")


def q(db,sql):
    with db.connect() as c:return c.execute(sql).fetchone()[0]


def test_autosave_policy_compatibility():
    p=AutosavePolicy(.5);p.touch(1);assert p.pending and not p.due(1.4) and p.due(1.5);p.clear();assert not p.pending

def test_dirty_revision_and_state(tmp_path):
    db,repo,store,a,*_=make_env(tmp_path);r=a.mark_dirty('p1','script');s=a.state('p1');assert r==1 and s.project_revision==1 and s.saved_revision==0 and s.status_code=='scheduled'

def test_debounce_and_coalescing(tmp_path):
    db,repo,store,a,codec,snaps,recovery,clock=make_env(tmp_path);calls=[];a.register_handler('script',lambda p,t,r:calls.append(r));a.mark_dirty('p1','script');a.mark_dirty('p1','script');clock[0]=101;assert a.tick()==[];clock[0]=102;assert a.tick()==['p1'];assert calls==[2] and a.state('p1').saved_revision==2

def test_edit_during_save_remains_dirty(tmp_path):
    *_,a,codec,snaps,recovery,clock=make_env(tmp_path)
    def save(pid,topics,rev):a.mark_dirty(pid,'script',now=clock[0]+.1)
    a.register_handler('script',save);a.mark_dirty('p1','script');a.flush('p1');s=a.state('p1');assert s.project_revision==2 and s.saved_revision==1 and s.dirty

def test_save_failure_and_retry(tmp_path):
    db,repo,store,a,*_=make_env(tmp_path);fail=[True]
    def h(*_):
        if fail[0]:raise OSError('disk')
    a.register_handler('script',h);a.mark_dirty('p1','script')
    with pytest.raises(AutosaveFailed):a.flush('p1')
    assert a.state('p1').status_code=='failed';fail[0]=False;assert a.retry('p1') and a.state('p1').saved_revision==1

def test_structural_saved_immediate(tmp_path):
    *_,a,codec,snaps,recovery,clock=make_env(tmp_path);rev=a.mark_structural_saved('p1','speaker');s=a.state('p1');assert rev==1 and s.saved_revision==1 and not s.dirty

def test_atomic_json_unicode(tmp_path):
    p=tmp_path/'x.json';atomic_write_json(p,{'x':'ខ្មែរ ไทย Tiếng Việt'});assert json.loads(p.read_text())['x']=='ខ្មែរ ไทย Tiếng Việt'

def test_atomic_replace_failure_preserves_old(tmp_path):
    from storage.atomic_write import atomic_write_text
    p=tmp_path/'x.txt';p.write_text('old')
    def fail(a,b):raise OSError('replace failed')
    with pytest.raises(OSError):atomic_write_text(p,'new',replace=fail)
    assert p.read_text()=='old' and not list(tmp_path.glob('.x.txt.*.tmp'))

def test_snapshot_checksum_and_corruption(tmp_path):
    db,repo,store,a,codec,snaps,recovery,clock=make_env(tmp_path);populate_creative(db,tmp_path);a.mark_dirty('p1','script');s=snaps.create('p1',recovery.session.session_id,reason='test');assert s and store.load_snapshot(s.path)['payload']
    p=Path(s.path);p.write_text(p.read_text()+'x')
    with pytest.raises(RecoverySnapshotCorrupt):snaps.load(s.id)

def test_snapshot_only_if_dirty(tmp_path):
    *_,snaps,recovery,clock=make_env(tmp_path);assert snaps.create('p1',recovery.session.session_id) is None

def test_snapshot_retention(tmp_path):
    db,repo,store,a,codec,snaps,recovery,clock=make_env(tmp_path);populate_creative(db,tmp_path)
    for i in range(7):a.mark_dirty('p1','script',now=100+i);snaps.create('p1',recovery.session.session_id,reason=str(i))
    assert len(store.list_project('p1'))<=4 and len(repo.snapshots('p1'))<=4

def test_snapshot_does_not_copy_media(tmp_path):
    db,repo,store,a,codec,snaps,recovery,clock=make_env(tmp_path);populate_creative(db,tmp_path);a.mark_dirty('p1','script');s=snaps.create('p1',recovery.session.session_id);env=store.load_snapshot(s.path);assert env['payload']['mediaReferences'][0]['path'].endswith('clip.mp4');assert Path(s.path).stat().st_size<100_000

def test_missing_media_warning(tmp_path):
    db,repo,store,a,codec,snaps,recovery,clock=make_env(tmp_path);populate_creative(db,tmp_path);a.mark_dirty('p1','script');s=snaps.create('p1',recovery.session.session_id);(tmp_path/'p1'/'clip.mp4').unlink();assert codec.media_warnings(store.load_snapshot(s.path)['payload'])[0]['status']=='missing'

def test_script_timeline_subtitle_translation_speaker_recovery(tmp_path):
    db,repo,store,a,codec,snaps,recovery,clock=make_env(tmp_path);populate_creative(db,tmp_path);mutate_creative(db);a.mark_dirty('p1','script');snap=snaps.create('p1',recovery.session.session_id,reason='crash')
    with db.connect() as c,c:
        c.execute("UPDATE scripts SET text='lost' WHERE id='s1'");c.execute("UPDATE scene_layers SET x=.0 WHERE id='l1'");c.execute("UPDATE subtitle_cues SET text='lost' WHERE id='cue1'");c.execute("UPDATE translation_segments SET translated_text='lost' WHERE id='trs1'");c.execute("UPDATE speech_blocks SET text='lost' WHERE id='b1'")
    recovery.recover(snap.id);assert q(db,"SELECT text FROM scripts WHERE id='s1'")=='Version B';assert q(db,"SELECT x FROM scene_layers WHERE id='l1'")==pytest.approx(.7);assert q(db,"SELECT text FROM subtitle_cues WHERE id='cue1'")=='ไทย B';assert q(db,"SELECT translated_text FROM translation_segments WHERE id='trs1'")=='Tiếng Việt B';assert q(db,"SELECT text FROM speech_blocks WHERE id='b1'")=='Reporter B'

def test_news_story_shorts_green_screen_recovery(tmp_path):
    db,repo,store,a,codec,snaps,recovery,clock=make_env(tmp_path);populate_creative(db,tmp_path);mutate_creative(db);a.mark_dirty('p1','story_text');snap=snaps.create('p1',recovery.session.session_id)
    with db.connect() as c,c:c.execute("UPDATE news_claims SET notes='lost' WHERE id='n1'");c.execute("UPDATE story_beats SET description='lost' WHERE id='beat1'");c.execute("UPDATE shorts_projects SET crop_json='{}' WHERE project_id='p1'");c.execute("UPDATE scene_layers SET chroma_similarity=.1,scale=.8 WHERE id='l1'")
    recovery.recover(snap.id);assert q(db,"SELECT notes FROM news_claims WHERE id='n1'")=='claim B';assert q(db,"SELECT description FROM story_beats WHERE id='beat1'")=='beat B';assert '0.8' in q(db,"SELECT crop_json FROM shorts_projects WHERE project_id='p1'");assert q(db,"SELECT chroma_similarity FROM scene_layers WHERE id='l1'")==pytest.approx(.31)

def test_recovery_comparison_summary(tmp_path):
    db,repo,store,a,codec,snaps,recovery,clock=make_env(tmp_path);populate_creative(db,tmp_path);a.mark_dirty('p1','script');snap=snaps.create('p1',recovery.session.session_id);mutate_creative(db);summary=recovery.summary(snap.id);assert summary['comparison']['Script']['changed'] and summary['comparison']['Scenes']['changed']

def test_discard_keeps_project(tmp_path):
    db,repo,store,a,codec,snaps,recovery,clock=make_env(tmp_path);a.mark_dirty('p1','script');s=snaps.create('p1',recovery.session.session_id);recovery.discard(s.id);assert q(db,"SELECT COUNT(*) FROM projects WHERE id='p1'")==1 and repo.snapshot(s.id) is None

def test_clean_shutdown_no_unclean_prompt(tmp_path):
    db,repo,store,a,codec,snaps,recovery,clock=make_env(tmp_path);recovery.mark_clean_shutdown();r2=RecoveryService(repo,store,snaps,codec,a,ProjectIntegrityService(db),InterruptedJobRecoveryService(db,repo));r2.start_session();assert not r2.previous_unclean

def test_unclean_shutdown_detected(tmp_path):
    db,repo,store,a,codec,snaps,recovery,clock=make_env(tmp_path);r2=RecoveryService(repo,store,snaps,codec,a,ProjectIntegrityService(db),InterruptedJobRecoveryService(db,repo));r2.start_session();assert r2.previous_unclean

def test_integrity_quick_check(tmp_path):
    db,*_=make_env(tmp_path);assert ProjectIntegrityService(db).lightweight_check()['ok']

def test_render_interruption_not_completed(tmp_path):
    db,repo,*_=make_env(tmp_path);out=tmp_path/'partial.mp4';out.write_bytes(b'partial')
    with db.connect() as c,c:c.execute("INSERT INTO render_jobs VALUES(?,?,?,?,?,?)",('r1','p1','rendering',str(out),'','{}'))
    counts=InterruptedJobRecoveryService(db,repo).recover_interrupted_jobs();assert counts['render']==1 and q(db,"SELECT status FROM render_jobs WHERE id='r1'")=='interrupted'

def test_stt_translation_dub_interruption(tmp_path):
    db,repo,*_=make_env(tmp_path)
    with db.connect() as c,c:
        c.execute("INSERT INTO transcripts VALUES(?,?,?,?)",('tx','p1','transcribing','{}'));c.execute("INSERT INTO translations VALUES(?,?,?,?)",('tr','p1','translating','{}'));c.execute("INSERT INTO translation_segments VALUES(?,?,?)",('seg','tr','completed'));c.execute("INSERT INTO dub_segments VALUES(?,?,?,?)",('d1','p1','generating','{}'));c.execute("INSERT INTO dub_segments VALUES(?,?,?,?)",('d2','p1','ready','{}'))
    counts=InterruptedJobRecoveryService(db,repo).recover_interrupted_jobs();assert counts['stt']==1 and counts['translation']==1 and counts['dub']==1;assert q(db,"SELECT translated_text FROM translation_segments WHERE id='seg'")=='completed';assert q(db,"SELECT audio_status FROM dub_segments WHERE id='d2'")=='ready'

def test_temp_classification_and_safe_cleanup(tmp_path):
    import os
    root=tmp_path/'temp';p=root/'old';p.mkdir(parents=True);(p/'recovery-manifest.json').write_text(json.dumps({'safe_cleanup':True,'stage':'done'}));old=time.time()-90000;os.utime(p,(old,old));svc=TempRecoveryService(root);assert svc.classify(p)=='safe-to-delete';assert svc.cleanup(p) and not p.exists()

def test_temp_recoverable_not_deleted(tmp_path):
    root=tmp_path/'temp';p=root/'job';p.mkdir(parents=True);(p/'recovery-manifest.json').write_text(json.dumps({'safe_cleanup':False,'stage':'rendering'}));svc=TempRecoveryService(root);assert svc.classify(p)=='recoverable' and not svc.cleanup(p)

def test_low_disk_periodic_skips(tmp_path,monkeypatch):
    db,repo,store,a,codec,snaps,recovery,clock=make_env(tmp_path);populate_creative(db,tmp_path);a.mark_dirty('p1','script');monkeypatch.setattr(store,'has_space',lambda *_:False);assert snaps.periodic_if_due('p1',recovery.session.session_id,now=1000) is None;assert a.state('p1').dirty

def test_unicode_exact_recovery(tmp_path):
    db,repo,store,a,codec,snaps,recovery,clock=make_env(tmp_path);populate_creative(db,tmp_path)
    text='English\nខ្មែរ\nไทย\nTiếng Việt'
    with db.connect() as c,c:c.execute('UPDATE script_sections SET content=? WHERE id=?',(text,'sec1'))
    a.mark_dirty('p1','script');s=snaps.create('p1',recovery.session.session_id);with_db=lambda value:None
    with db.connect() as c,c:c.execute("UPDATE script_sections SET content='lost' WHERE id='sec1'")
    recovery.recover(s.id);assert q(db,"SELECT content FROM script_sections WHERE id='sec1'")==text

def test_revision_race_latest_not_falsely_saved(tmp_path):
    db,repo,store,a,codec,snaps,recovery,clock=make_env(tmp_path)
    seen=[]
    def h(pid,topics,rev):
        seen.append(rev)
        if rev==1:a.mark_dirty(pid,'script',now=101)
    a.register_handler('script',h);a.mark_dirty('p1','script');a.flush('p1');assert a.state('p1').saved_revision==1 and a.state('p1').project_revision==2;a.flush('p1');assert a.state('p1').saved_revision==2

def test_shutdown_failure_leaves_session_unclean(tmp_path):
    db,repo,store,a,codec,snaps,recovery,clock=make_env(tmp_path);a.register_handler('script',lambda *_:(_ for _ in ()).throw(OSError('x')));a.mark_dirty('p1','script');shutdown=ShutdownService(a,recovery,snaps,timeout_seconds=.5);assert not shutdown.prepare_exit() and store.marker_path.exists()

def test_shutdown_success_marks_clean(tmp_path):
    db,repo,store,a,codec,snaps,recovery,clock=make_env(tmp_path);a.register_handler('script',lambda *_:None);a.mark_dirty('p1','script');shutdown=ShutdownService(a,recovery,snaps,timeout_seconds=.5);assert shutdown.prepare_exit() and not store.marker_path.exists()

def test_large_project_snapshot_performance(tmp_path):
    db,repo,store,a,codec,snaps,recovery,clock=make_env(tmp_path)
    with db.connect() as c,c:
        for i in range(100):c.execute('INSERT INTO scenes VALUES(?,?,?)',(f's{i}','p1',f'Scene {i}'))
        c.execute('INSERT INTO subtitle_tracks VALUES(?,?)',('many','p1'))
        c.executemany('INSERT INTO subtitle_cues VALUES(?,?,?,?,?)',[(f'c{i}','many',f'cue {i}',i*100,i*100+90) for i in range(1000)])
    a.mark_dirty('p1','subtitle_text');start=time.perf_counter();s=snaps.create('p1',recovery.session.session_id);elapsed=time.perf_counter()-start;assert s and elapsed<3.0

def test_project_delete_recovery_cleanup(tmp_path):
    db,repo,store,a,codec,snaps,recovery,clock=make_env(tmp_path);a.mark_dirty('p1','script');s=snaps.create('p1',recovery.session.session_id);snaps.delete_project('p1');assert not store.list_project('p1') and repo.snapshots('p1')==[]

def test_tts_resume_code_skips_existing_audio():
    source=Path(__file__).parents[1]/'services'/'multispeaker_tts_service.py';text=source.read_text();assert '_completed_audio' in text and 'existing if existing is not None else self.generate_block' in text

def test_qml_recovery_surface_present():
    root=Path(__file__).parents[1]/'ui'/'qml'/'recovery';names={p.name for p in root.glob('*.qml')};assert {'RecoveryDialog.qml','RecoveryCard.qml','RecoveryComparison.qml','RecoveryStatus.qml','RecoveryHost.qml'}<=names

def test_runtime_does_not_auto_resume_heavy_jobs():
    text=(Path(__file__).parents[1]/'app'/'phase27_runtime.py').read_text();assert 'recover_interrupted_jobs' in (Path(__file__).parents[1]/'services'/'interrupted_job_recovery_service.py').read_text();assert 'resume(' not in (Path(__file__).parents[1]/'services'/'interrupted_job_recovery_service.py').read_text()

def test_migration_has_revision_session_snapshot_jobs():
    p=Path(__file__).parents[1]/'storage'/'migrations'/'m024_create_autosave_recovery.py';t=p.read_text();assert all(x in t for x in ['autosave_state','recovery_sessions','recovery_snapshots','interrupted_jobs'])

def test_database_backup_api_and_wal_code_present():
    t=(Path(__file__).parents[1]/'storage'/'database.py').read_text();assert 'journal_mode=WAL' in t and '.backup(' in t

def test_sqlite_restore_transaction_rolls_back_half_state(tmp_path):
    db,repo,store,a,codec,snaps,recovery,clock=make_env(tmp_path);populate_creative(db,tmp_path);mutate_creative(db)
    payload=codec.capture('p1')
    # Force a child FK failure after deletion/reinsert work has begun.
    payload['tables']['scripts']=[]
    with pytest.raises(RecoveryRestoreFailed):codec.restore('p1',payload)
    assert q(db,"SELECT text FROM scripts WHERE id='s1'")=='Version B'
    assert q(db,"SELECT content FROM script_sections WHERE id='sec1'")=='ខ្មែរ B'


def test_batch_crash_30_completed_one_interrupted_69_pending(tmp_path):
    from services.batch_recovery_service import BatchRecoveryService
    from storage.repositories.batch_repository import BatchRepository
    from storage.repositories.batch_item_repository import BatchItemRepository
    db,repo,*_=make_env(tmp_path)
    now='2026-09-12T00:00:00+00:00'
    with db.connect() as c,c:
        c.execute("""INSERT INTO batches(id,name,template_id,status,created_at,updated_at,output_directory,total_items,completed_items,template_snapshot_json,input_snapshot_json,settings_json,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",('b100','Thai News 100','tpl','running',now,now,str(tmp_path/'out'),100,30,'{}','[]','{}','{}'))
        for i in range(100):
            status='completed' if i<30 else ('rendering' if i==30 else 'pending')
            stage='render' if i==30 else ('export' if i<30 else 'create_project')
            c.execute("""INSERT INTO batch_items(id,batch_id,row_index,item_key,status,current_stage,progress,created_at,updated_at,input_data_json,resolved_data_json,metadata_json,fingerprint) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",(f'i{i}','b100',i,f'row-{i}',status,stage,1.0 if i<30 else 0.0,now,now,'{}','{}','{}',f'f{i}'))
    svc=BatchRecoveryService(BatchRepository(db),BatchItemRepository(db));result=svc.recover_startup()
    assert result['interruptedItems']==1
    with db.connect() as c:
        counts={r['status']:r['n'] for r in c.execute("SELECT status,COUNT(*) n FROM batch_items GROUP BY status")}
        batch=c.execute("SELECT status FROM batches WHERE id='b100'").fetchone()['status']
    assert counts.get('completed')==30 and counts.get('interrupted')==1 and counts.get('pending')==69
    assert batch=='paused'
