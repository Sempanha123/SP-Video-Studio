from __future__ import annotations

import importlib.util
import json
import shutil
import sqlite3
import subprocess
import sys
import types
from dataclasses import dataclass
from pathlib import Path

import pytest

from domain.schema_version import APP_SCHEMA_VERSION, PROJECT_SCHEMA_VERSION, SETTINGS_SCHEMA_VERSION
from migrations.project.v001_to_v002 import canonical_language
from services.backup_service import BackupService
from services.migration_validation_service import MigrationValidationError, MigrationValidationService
from services.project_migration_service import NewerProjectVersionError, ProjectMigrationError, ProjectMigrationService
from services.recovery_migration_service import RecoveryMigrationService, RecoverySnapshotVersionError
from services.recovery_snapshot_service import RecoverySnapshotService
from services.settings_migration_service import SettingsMigrationService
from storage.migration_registry import MigrationRegistry, MigrationStep
from storage.json_writer import read_json
from tests.fixtures.phase38_legacy import FixtureDatabase, FixtureRepository, REAL_MILESTONE_FIXTURES, content_fingerprint, make_legacy_fixture

ROOT=Path(__file__).resolve().parents[1]

def _load_m028():
    spec=importlib.util.spec_from_file_location('phase38_m028_direct',ROOT/'storage/migrations/m028_phase38_migration_metadata.py')
    module=importlib.util.module_from_spec(spec);assert spec and spec.loader;spec.loader.exec_module(module);return module.migrate


@dataclass(frozen=True)
class FakeMigration:
    version:int;name:str;apply:object;validate:object=None


def _load_database(migrations):
    stub=types.ModuleType('storage.migrations');stub.MIGRATIONS=tuple(migrations)
    previous=sys.modules.get('storage.migrations');sys.modules['storage.migrations']=stub
    try:
        spec=importlib.util.spec_from_file_location(f'phase38_db_{id(migrations)}',ROOT/'storage/database.py')
        module=importlib.util.module_from_spec(spec);assert spec and spec.loader;spec.loader.exec_module(module);return module
    finally:
        if previous is None:sys.modules.pop('storage.migrations',None)
        else:sys.modules['storage.migrations']=previous


def _m1(c):
    c.execute('CREATE TABLE projects(id TEXT PRIMARY KEY,title TEXT,workflow TEXT,language TEXT,aspect_ratio TEXT,fps INTEGER,created_at TEXT,updated_at TEXT,last_opened_at TEXT,thumbnail_path TEXT,status TEXT,project_path TEXT UNIQUE,version INTEGER)')
def _m2(c):c.execute('CREATE TABLE sample(id INTEGER PRIMARY KEY,value TEXT)')
def _m3(c):c.execute("INSERT INTO sample(value) VALUES('ok')")

def test_schema_constants_are_explicit():
    assert APP_SCHEMA_VERSION==28 and PROJECT_SCHEMA_VERSION==2 and SETTINGS_SCHEMA_VERSION==2

def test_registry_orders_and_rejects_gaps():
    seen=[];r=MigrationRegistry((MigrationStep(1,2,'one',lambda _:seen.append(1)),MigrationStep(2,3,'two',lambda _:seen.append(2))))
    assert [x.migration_id for x in r.path(1,3)]==['one','two']
    with pytest.raises(KeyError):MigrationRegistry((MigrationStep(1,2,'one',lambda _:None),)).path(1,3)

def test_fresh_db_creation_and_order(tmp_path):
    mod=_load_database([FakeMigration(1,'projects',_m1),FakeMigration(2,'sample',_m2),FakeMigration(3,'seed',_m3)])
    db=mod.SQLiteDatabase(tmp_path/'fresh.db');db.initialize();assert db.current_version()==3
    assert [r['version'] for r in db.applied_migrations()]==[1,2,3]
    with db.connect() as c:assert c.execute('SELECT value FROM sample').fetchone()[0]=='ok'

def test_migration_already_applied_is_idempotent(tmp_path):
    calls=[]
    def step(c):calls.append('x');_m1(c)
    mod=_load_database([FakeMigration(1,'projects',step)]);db=mod.SQLiteDatabase(tmp_path/'idempotent.db');db.initialize();db.initialize();assert calls==['x']

def test_failed_app_migration_restores_backup_even_after_implicit_commit(tmp_path):
    mod1=_load_database([FakeMigration(1,'projects',_m1)]);path=tmp_path/'rollback.db';mod1.SQLiteDatabase(path).initialize()
    def broken(c):
        c.executescript('CREATE TABLE half_applied(id INTEGER);');raise RuntimeError('injected halfway')
    mod2=_load_database([FakeMigration(1,'projects',_m1),FakeMigration(2,'broken',broken)]);db=mod2.SQLiteDatabase(path)
    with pytest.raises(mod2.DatabaseMigrationError):db.initialize()
    c=sqlite3.connect(path)
    try:
        assert c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='half_applied'").fetchone()[0]==0
        assert c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==1
    finally:c.close()
    assert list((path.parent/'migration_backups'/'app').glob('app-v1-to-v2-*.db'))

def test_crash_marker_restores_backup_on_restart(tmp_path):
    mod=_load_database([FakeMigration(1,'projects',_m1)]);path=tmp_path/'crash.db';db=mod.SQLiteDatabase(path);db.initialize()
    backup=db.backup_to(tmp_path/'safe.db')
    c=sqlite3.connect(path);c.execute('CREATE TABLE crash_artifact(id INTEGER)');c.commit();c.close()
    db.migration_backup_root.mkdir(parents=True,exist_ok=True);db.migration_marker.write_text(json.dumps({'backup':str(backup),'migration_in_progress':True}),encoding='utf-8')
    db.initialize();c=sqlite3.connect(path)
    try:assert c.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='crash_artifact'").fetchone()[0]==0
    finally:c.close()
    assert not db.migration_marker.exists()

def test_phase38_app_migration_adds_versions_and_history(tmp_path):
    path=tmp_path/'legacy.db';c=sqlite3.connect(path)
    c.execute('CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY,name TEXT NOT NULL,applied_at TEXT NOT NULL)')
    c.execute("INSERT INTO schema_migrations VALUES(27,'manual_speech_editor','old')")
    _m1(c);c.execute("INSERT INTO projects VALUES('p','P','video','en','16:9',30,'a','b',NULL,NULL,'draft','/tmp/p',1)")
    _load_m028()(c);c.commit()
    assert 'app_version' in {r[1] for r in c.execute('PRAGMA table_info(schema_migrations)')}
    assert 'project_schema_version' in {r[1] for r in c.execute('PRAGMA table_info(projects)')}
    assert c.execute("SELECT app_version FROM schema_migrations WHERE version=27").fetchone()[0]=='legacy'
    assert c.execute("SELECT project_schema_version FROM projects WHERE id='p'").fetchone()[0]==1
    assert c.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='migration_history'").fetchone()[0]==1;c.close()

def _service(tmp_path,later=False):
    db,repo,project_dir,pid=make_legacy_fixture(tmp_path,later=later);backup=BackupService(db,tmp_path/'migration_backups');return db,repo,project_dir,pid,ProjectMigrationService(db,repo,backup)

def test_legacy_project_migration_backup_open_edit_save(tmp_path):
    db,repo,project_dir,pid,service=_service(tmp_path)
    before=content_fingerprint(db.path,pid);result=service.ensure_current(pid);assert result.ok and result.from_version==1 and result.to_version==2
    meta=read_json(project_dir/'project.json');assert meta['project_schema_version']==2 and meta['language']=='en' and meta['unknown_future_field']=={'keep':True}
    c=sqlite3.connect(db.path);assert c.execute('SELECT project_schema_version FROM projects WHERE id=?',(pid,)).fetchone()[0]==2
    block=c.execute('SELECT text,language FROM speech_blocks').fetchone();assert block[0]=='សួស្តី ព័ត៌មានសំខាន់' and block[1]=='en';c.close()
    meta['user_edit']='កែសម្រួល';(project_dir/'project.json').write_text(json.dumps(meta,ensure_ascii=False),encoding='utf-8');assert service.ensure_current(pid).from_version==2
    after=content_fingerprint(db.path,pid);assert before==after
    assert result.backup_path and (result.backup_path/'app.db').is_file() and (result.backup_path/'project.json').is_file()

def test_multilingual_speaker_speech_layer_audio_dub_migration(tmp_path):
    db,repo,project_dir,pid,service=_service(tmp_path,later=True);before=content_fingerprint(db.path,pid);result=service.ensure_current(pid);assert result.ok
    c=sqlite3.connect(db.path);c.row_factory=sqlite3.Row
    try:
        assert c.execute('SELECT language FROM projects WHERE id=?',(pid,)).fetchone()[0]=='vi'
        assert c.execute('SELECT language FROM speakers WHERE id="speaker-1"').fetchone()[0]=='th'
        assert c.execute('SELECT language FROM speech_blocks WHERE id="speech-existing"').fetchone()[0]=='vi'
        assert {r[0] for r in c.execute('SELECT role FROM audio_tracks WHERE project_id=?',(pid,))}>={'source_audio','dub'}
        assert c.execute('SELECT COUNT(*) FROM audio_mix_settings WHERE project_id=?',(pid,)).fetchone()[0]==1
        assert json.loads(c.execute('SELECT metadata_json FROM scene_layers WHERE id="layer-1"').fetchone()[0])['chromaKey']['enabled'] is True
    finally:c.close()
    assert content_fingerprint(db.path,pid)==before

def test_speechblock_migration_is_idempotent(tmp_path):
    db,repo,project_dir,pid,service=_service(tmp_path);service.ensure_current(pid)
    c=sqlite3.connect(db.path);first=c.execute('SELECT COUNT(*) FROM speech_blocks').fetchone()[0];c.close();service.ensure_current(pid)
    c=sqlite3.connect(db.path);second=c.execute('SELECT COUNT(*) FROM speech_blocks').fetchone()[0];c.close();assert first==second==1

def test_language_unknown_is_preserved_not_guessed(tmp_path):
    db,repo,project_dir,pid,service=_service(tmp_path);meta=read_json(project_dir/'project.json');meta['language']='xx-private';(project_dir/'project.json').write_text(json.dumps(meta),encoding='utf-8')
    c=sqlite3.connect(db.path);c.execute('UPDATE projects SET language=? WHERE id=?',('xx-private',pid));c.commit();c.close();result=service.ensure_current(pid)
    migrated=read_json(project_dir/'project.json');assert migrated['language']=='xx-private';assert migrated['migration_metadata']['legacyLanguage']=='xx-private';assert any(w.code=='unknown_project_language' for w in result.warnings)

def test_newer_project_is_never_modified(tmp_path):
    db,repo,project_dir,pid,service=_service(tmp_path);meta=read_json(project_dir/'project.json');meta['version']=99;meta['project_schema_version']=99;(project_dir/'project.json').write_text(json.dumps(meta),encoding='utf-8')
    c=sqlite3.connect(db.path);c.execute('UPDATE projects SET version=99,project_schema_version=99 WHERE id=?',(pid,));c.commit();c.close();before=(project_dir/'project.json').read_bytes()
    with pytest.raises(NewerProjectVersionError,match='newer MMO Video Studio version'):service.ensure_current(pid)
    assert (project_dir/'project.json').read_bytes()==before and not (tmp_path/'migration_backups'/'projects').exists()

def test_failed_project_migration_rolls_back_and_keeps_backup(tmp_path):
    db,repo,project_dir,pid,service=_service(tmp_path)
    def fail(c,pid,meta,warnings):c.execute('UPDATE projects SET title="HALF" WHERE id=?',(pid,));meta['title']='HALF';raise RuntimeError('injected')
    service.registry=MigrationRegistry((MigrationStep(1,2,'injected_failure',fail),));original=read_json(project_dir/'project.json')
    with pytest.raises(ProjectMigrationError) as caught:service.ensure_current(pid)
    c=sqlite3.connect(db.path);row=c.execute('SELECT title,project_schema_version FROM projects WHERE id=?',(pid,)).fetchone();c.close()
    assert row[0]!='HALF' and row[1]==1 and read_json(project_dir/'project.json')==original
    assert caught.value.backup_path and Path(caught.value.backup_path).is_dir()

def test_interrupted_project_marker_restores_metadata(tmp_path):
    db,repo,project_dir,pid,service=_service(tmp_path);backup=service.backups.create_project_backup(pid,project_dir);service.backups.write_marker(pid,{'backupPath':str(backup.root)})
    damaged=read_json(project_dir/'project.json');damaged['title']='DAMAGED';(project_dir/'project.json').write_text(json.dumps(damaged),encoding='utf-8');service.ensure_current(pid)
    assert read_json(project_dir/'project.json')['title']!='DAMAGED'

def test_settings_migration_preserves_choices_and_unknown():
    payload={'settings_version':1,'general':{'language':'en'},'appearance':{'theme':'dark','futureOpacity':.7},'projects':{'default_projects_folder':'D:/Projects'},'performance':{'profile':'low_memory'},'keyboard_shortcuts':{'overrides':{'app.save':'Ctrl+Alt+S'}},'accessibility':{'reduce_motion':'on','interface_text_size':'large','stronger_focus_indicator':True},'future_section':{'keep':123}}
    migrated,changed=SettingsMigrationService().migrate(payload);assert changed and migrated['settings_version']==2 and migrated['future_section']=={'keep':123} and migrated['appearance']['futureOpacity']==.7

def test_settings_flat_legacy_names_map_without_dropping_originals():
    payload={'settings_version':1,'project_root':'X:/Old','performance_profile':'balanced','shortcuts':{'app.save':'Ctrl+S'},'mystery':'keep'};m,_=SettingsMigrationService().migrate(payload)
    assert m['projects']['default_projects_folder']=='X:/Old' and m['performance']['profile']=='balanced' and m['keyboard_shortcuts']['overrides']['app.save']=='Ctrl+S' and m['mystery']=='keep'

def test_recovery_snapshot_migration_and_newer_rejection():
    service=RecoveryMigrationService();m,changed=service.migrate_payload({'schemaVersion':1,'projectId':'p','payload':{'text':'ខ្មែរ'}});assert changed and m['schemaVersion']==2 and m['payload']['text']=='ខ្មែរ'
    with pytest.raises(RecoverySnapshotVersionError):service.migrate_payload({'schemaVersion':99})

def test_template_migration_adapter_reuses_existing_migrator(monkeypatch):
    fake=types.ModuleType('services.template_schema_migrator')
    class Migrator:
        def migrate(self,payload):payload=dict(payload);payload['delegated']=True;return payload
    fake.TemplateSchemaMigrator=Migrator;monkeypatch.setitem(sys.modules,'services.template_schema_migrator',fake);sys.modules.pop('migrations.template',None)
    import migrations.template as adapter
    assert adapter.migrate_payload({'schemaVersion':1})['delegated'] is True

def test_asset_and_batch_state_survive_project_migration(tmp_path):
    db,repo,project_dir,pid,service=_service(tmp_path,later=True)
    c=sqlite3.connect(db.path);before_asset=c.execute('SELECT * FROM asset_library_items').fetchone();before_batch=c.execute('SELECT * FROM batches').fetchone();c.close();service.ensure_current(pid)
    c=sqlite3.connect(db.path);assert c.execute('SELECT * FROM asset_library_items').fetchone()==before_asset;assert c.execute('SELECT * FROM batches').fetchone()==before_batch;c.close()

def test_foreign_key_validation_detects_orphan(tmp_path):
    db,repo,project_dir,pid,service=_service(tmp_path);c=sqlite3.connect(db.path);c.execute('PRAGMA foreign_keys=OFF');c.execute("INSERT INTO speakers VALUES('orphan','missing','X','speaker','','en','','','{}',?,?)",('a','b'));c.commit();c.close()
    c=sqlite3.connect(db.path);c.execute('PRAGMA foreign_keys=ON')
    with pytest.raises(MigrationValidationError):MigrationValidationService().validate_database(c)
    c.close()

def test_language_aliases_are_careful():
    assert canonical_language('English')==('en',None);assert canonical_language('en-US')==('en',None);assert canonical_language('Thai')==('th',None);assert canonical_language('vi-VN')==('vi',None);assert canonical_language('mystery')==('mystery','mystery')

def test_post_migration_render_smoke(tmp_path):
    if not shutil.which('ffmpeg'):pytest.skip('FFmpeg is unavailable')
    db,repo,project_dir,pid,service=_service(tmp_path);service.ensure_current(pid);meta=read_json(project_dir/'project.json');assert meta['project_schema_version']==2
    # edit/save after migration
    meta['title']='កែសម្រួល Migrated';(project_dir/'project.json').write_text(json.dumps(meta,ensure_ascii=False),encoding='utf-8')
    output=project_dir/'renders'/'migration-smoke.mp4';done=subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i','color=c=black:s=64x64:r=10:d=0.2','-c:v','libx264','-pix_fmt','yuv420p','-y',str(output)],capture_output=True,text=True,timeout=20,shell=False)
    assert done.returncode==0 and output.is_file() and output.stat().st_size>0

def test_runtime_and_entrypoint_contract():
    main=(ROOT/'main.py').read_text(encoding='utf-8');runtime=(ROOT/'app/phase38_runtime.py').read_text(encoding='utf-8')
    import re
    match=re.search(r"from app\.phase(\d+)_runtime import run",main);assert match and int(match.group(1))>=38
    assert 'ProjectMigrationService' in runtime and 'ensure_current(project_id)' in runtime

def test_storage_migration_backups_are_protected():
    text=(ROOT/'domain/storage_category.py').read_text(encoding='utf-8');assert "MIGRATION_BACKUPS='migration_backups'" in text and "StorageSafety.PROTECTED" in text

def test_project_schema_metadata_preserves_unknown_fields_static():
    text=(ROOT/'domain/project.py').read_text(encoding='utf-8');assert 'extra_metadata' in text and 'project_schema_version' in text

def test_no_drop_recreate_shortcut_in_phase38_sources():
    paths=[ROOT/'services/project_migration_service.py',ROOT/'storage/database.py',ROOT/'storage/migrations/m028_phase38_migration_metadata.py']
    merged='\n'.join(p.read_text(encoding='utf-8').lower() for p in paths);assert 'drop table' not in merged and 'delete from projects' not in merged

def test_application_database_newer_schema_is_rejected(tmp_path):
    mod=_load_database([FakeMigration(1,'projects',_m1)])
    path=tmp_path/'future.db';db=mod.SQLiteDatabase(path);db.initialize()
    c=sqlite3.connect(path)
    c.execute("INSERT INTO schema_migrations(version,name,applied_at,app_version) VALUES(29,'future','later','future')")
    c.commit();c.close()
    with pytest.raises(mod.DatabaseMigrationError,match='newer SP Video Studio'):
        db.initialize()


def test_phase38_app_migration_interrupts_running_batch_and_versions_recovery(tmp_path):
    path=tmp_path/'upgrade.db';c=sqlite3.connect(path)
    c.execute('CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY,name TEXT NOT NULL,applied_at TEXT NOT NULL)')
    c.execute("INSERT INTO schema_migrations VALUES(27,'manual_speech_editor','old')")
    c.execute('CREATE TABLE projects(id TEXT PRIMARY KEY,title TEXT,workflow TEXT,language TEXT,aspect_ratio TEXT,fps INTEGER,created_at TEXT,updated_at TEXT,last_opened_at TEXT,thumbnail_path TEXT,status TEXT,project_path TEXT UNIQUE,version INTEGER)')
    c.execute("INSERT INTO projects VALUES('p','P','video','en','16:9',30,'a','b',NULL,NULL,'draft','/tmp/p',1)")
    c.execute("CREATE TABLE batches(id TEXT PRIMARY KEY,status TEXT NOT NULL,pause_reason TEXT NOT NULL DEFAULT '')")
    c.execute("INSERT INTO batches VALUES('b','running','')")
    c.execute('CREATE TABLE batch_items(id TEXT PRIMARY KEY,status TEXT NOT NULL)')
    c.execute("INSERT INTO batch_items VALUES('i','rendering')")
    c.execute('CREATE TABLE batch_stage_state(item_id TEXT,stage TEXT,status TEXT NOT NULL,PRIMARY KEY(item_id,stage))')
    c.execute("INSERT INTO batch_stage_state VALUES('i','render','running')")
    c.execute('CREATE TABLE recovery_snapshots(id TEXT PRIMARY KEY,project_id TEXT,session_id TEXT,project_revision INTEGER,created_at TEXT,reason TEXT,snapshot_type TEXT,status TEXT,path TEXT,size INTEGER,checksum TEXT,metadata_json TEXT)')
    c.execute("INSERT INTO recovery_snapshots VALUES('s','p','sess',1,'now','','periodic','valid','x',1,'hash','{}')")
    _load_m028()(c);c.commit()
    assert c.execute("SELECT status,pause_reason FROM batches WHERE id='b'").fetchone()==('paused','App upgrade interrupted an active Batch safely')
    assert c.execute("SELECT status FROM batch_items WHERE id='i'").fetchone()[0]=='interrupted'
    assert c.execute("SELECT status FROM batch_stage_state WHERE item_id='i'").fetchone()[0]=='interrupted'
    assert 'schema_version' in {r[1] for r in c.execute('PRAGMA table_info(recovery_snapshots)')}
    assert c.execute("SELECT schema_version FROM recovery_snapshots WHERE id='s'").fetchone()[0]==1
    c.close()


def test_legacy_project_volume_fields_migrate_to_generic_mixer(tmp_path):
    db,repo,project_dir,pid,service=_service(tmp_path)
    meta=read_json(project_dir/'project.json');meta['source_volume']=0.4;meta['narration_volume']=0.8
    (project_dir/'project.json').write_text(json.dumps(meta,ensure_ascii=False),encoding='utf-8')
    service.ensure_current(pid)
    c=sqlite3.connect(db.path)
    try:
        roles={r[0] for r in c.execute('SELECT role FROM audio_tracks WHERE project_id=?',(pid,))}
        assert {'source_audio','narration'}.issubset(roles)
        raw=c.execute('SELECT metadata_json FROM audio_mix_settings WHERE project_id=?',(pid,)).fetchone()[0]
        values=json.loads(raw)['legacyVolumeSettings'];assert values['source_volume']==0.4 and values['narration_volume']==0.8
    finally:c.close()


def test_project_backup_can_restore_database_and_metadata(tmp_path):
    db,repo,project_dir,pid,service=_service(tmp_path)
    backup=service.backups.create_project_backup(pid,project_dir)
    original=read_json(project_dir/'project.json')
    c=sqlite3.connect(db.path);c.execute('UPDATE projects SET title=? WHERE id=?',('DAMAGED',pid));c.commit();c.close()
    damaged=dict(original);damaged['title']='DAMAGED';(project_dir/'project.json').write_text(json.dumps(damaged),encoding='utf-8')
    service.backups.restore_project_backup(backup,db.path,project_dir)
    c=sqlite3.connect(db.path)
    try:assert c.execute('SELECT title FROM projects WHERE id=?',(pid,)).fetchone()[0]==original['title']
    finally:c.close()
    assert read_json(project_dir/'project.json')==original


def test_recovery_snapshot_service_migrates_old_payload_in_memory_and_rejects_newer():
    from domain.recovery_snapshot import RecoverySnapshot
    from domain.recovery_errors import RecoveryVersionUnsupported
    class Repo:
        def __init__(self,payload_version=1):
            self.snap=RecoverySnapshot('p','sess',1,'now','old','periodic','snap',1,'hash',schema_version=payload_version)
        def snapshot(self,_):return self.snap
        def save_snapshot(self,s):self.snap=s
    class Store:
        def __init__(self,payload):self.payload=payload
        def load_snapshot(self,_):return {'payload':dict(self.payload)}
    class Codec:pass
    class Auto:pass
    repo=Repo(1);service=RecoverySnapshotService(repo,Store({'schemaVersion':1,'projectId':'p','text':'ភាសាខ្មែរ ภาษาไทย Tiếng Việt'}),Codec(),Auto())
    snap,payload=service.load(repo.snap.id)
    assert payload['schemaVersion']==2 and 'ភាសាខ្មែរ' in payload['text'] and snap.metadata['recoveryPayloadMigratedInMemory'] is True
    future=Repo(99);service=RecoverySnapshotService(future,Store({'schemaVersion':99,'projectId':'p'}),Codec(),Auto())
    with pytest.raises(RecoveryVersionUnsupported):service.load(future.snap.id)
    assert future.snap.status_code=='unsupported'


def test_recovery_repository_persists_schema_version_contract_static():
    text=(ROOT/'storage/repositories/recovery_repository.py').read_text(encoding='utf-8')
    assert 'schema_version' in text and 'RecoverySnapshot' in text


def test_real_legacy_fixture_milestones_are_documented():
    required={"early_project_media","script_only","scene_subtitle","advanced_timeline","news","story_dub","phase22_multilingual","audio_mixer","current"}
    assert required==set(REAL_MILESTONE_FIXTURES)
    assert REAL_MILESTONE_FIXTURES["news"][2][0]=="news_projects"
    assert REAL_MILESTONE_FIXTURES["story_dub"][2][0]=="story_projects"

def test_phase38_migration_package_is_in_distribution():
    pyproject=(ROOT/'pyproject.toml').read_text(encoding='utf-8')
    assert 'migrations*' in pyproject and (ROOT/'migrations/__init__.py').is_file()


def test_phase38_project_migration_failure_ux_contract_static():
    controller=(ROOT/'ui/controllers/project_controller.py').read_text(encoding='utf-8')
    main=(ROOT/'ui/qml/Main.qml').read_text(encoding='utf-8')
    migration=(ROOT/'services/project_migration_service.py').read_text(encoding='utf-8')
    assert 'migrationIssue = Signal(str, str, str)' in controller
    assert 'MMO Video Studio could not update this project safely. The original project was kept unchanged.' in migration
    assert 'Open Diagnostics' in main and 'Open Backup Location' in main and 'Close' in main
    assert 'projectController.openFolder(window.migrationIssueLocation)' in main


def test_phase38_newer_project_ux_contract_static():
    controller=(ROOT/'ui/controllers/project_controller.py').read_text(encoding='utf-8')
    main=(ROOT/'ui/qml/Main.qml').read_text(encoding='utf-8')
    migration=(ROOT/'services/project_migration_service.py').read_text(encoding='utf-8')
    runtime=(ROOT/'app/phase38_runtime.py').read_text(encoding='utf-8')
    assert 'This project was created with a newer MMO Video Studio version.' in migration
    assert '"newer_project", exc.user_message' in controller
    assert 'text:"Open Folder"' in main and '?"Cancel":"Close"' in main
    assert 'ProjectValidationError' not in runtime
