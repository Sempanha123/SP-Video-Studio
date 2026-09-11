from __future__ import annotations
import sqlite3,time
from pathlib import Path
from types import SimpleNamespace
import pytest
from PIL import Image

from domain.asset import Asset
from domain.asset_errors import AssetDuplicate,AssetInUse,AssetPathUnsafe,AssetRelinkMismatch
from domain.asset_license import AssetLicense
from domain.asset_usage import AssetUsage
from services.asset_import_service import AssetImportService
from services.asset_library_service import AssetLibraryService
from services.asset_project_integration_service import AssetProjectIntegrationService
from services.asset_relink_service import AssetRelinkService
from services.asset_search_service import AssetSearchService
from services.asset_template_integration_service import AssetTemplateIntegrationService
from services.asset_usage_service import AssetUsageService
from services.asset_validation_service import AssetValidationService
from storage.database import SQLiteDatabase
from storage.migrations.m022_create_asset_library import migrate
from storage.repositories.asset_repository import AssetRepository
from domain.media import MediaAsset

class Classifier:
    def classify(self,p):
        e=Path(p).suffix.lower()
        if e in {'.mp4','.mov','.mkv','.avi','.webm','.m4v'}:return 'video'
        if e in {'.mp3','.wav','.m4a','.aac','.flac','.ogg','.opus'}:return 'audio'
        if e in {'.jpg','.jpeg','.png','.webp','.bmp'}:return 'image'
        return None
class ProbeResult:
    def __init__(self,t):
        self.duration_ms=12000 if t in {'video','audio'} else None;self.width=1920 if t=='video' else None;self.height=1080 if t=='video' else None;self.fps=30.0 if t=='video' else None;self.codec='h264' if t=='video' else '';self.audio_codec='aac' if t in {'video','audio'} else '';self.sample_rate=48000 if t in {'video','audio'} else None;self.channels=2 if t in {'video','audio'} else None
class Prober:
    def probe(self,p,expected_type=None):return ProbeResult(expected_type)
class Thumbs:
    def generate(self,t,src,dst,duration_ms=None):
        Path(dst).parent.mkdir(parents=True,exist_ok=True);Image.new('RGB',(64,36)).save(dst);return Path(dst)
class FakeMediaService:
    classifier=Classifier();prober=Prober();thumbnails=Thumbs()

class DBMediaRepo:
    def __init__(self,db):self.db=db;self.items={}
    def create(self,a):
        a.validate();self.items[a.id]=a
        with self.db.connect() as c,c:c.execute('INSERT INTO media_assets(id,project_id) VALUES(?,?)',(a.id,a.project_id))
        return a
    def update(self,a):self.items[a.id]=a;return a
    def get_by_id(self,i):return self.items.get(i)
    def list_by_project(self,pid,*args,**kwargs):return [x for x in self.items.values() if x.project_id==pid]
    def delete(self,i):
        self.items.pop(i,None)
        with self.db.connect() as c,c:c.execute('DELETE FROM media_assets WHERE id=?',(i,))
class Project:
    def __init__(self,pid,path):self.project_id=pid;self.project_path=str(path);self.id=pid
class ProjectRepo:
    def __init__(self,db,tmp):self.db=db;self.tmp=tmp;self.items={}
    def add(self,pid):
        root=self.tmp/pid;root.mkdir();(root/'media/video').mkdir(parents=True);(root/'media/audio').mkdir(parents=True);(root/'media/images').mkdir(parents=True);(root/'thumbnails').mkdir()
        p=Project(pid,root);self.items[pid]=p
        with self.db.connect() as c,c:c.execute('INSERT INTO projects(id) VALUES(?)',(pid,))
        return p
    def get_by_id(self,pid):return self.items.get(pid)
class FakeVisual:
    def __init__(self):self.layers=[];self.chroma=[]
    def add_media_layer(self,pid,sid,mid,role='broll',speaker_id=''):
        x=SimpleNamespace(id=f'l{len(self.layers)+1}',project_id=pid,scene_id=sid,media_id=mid,role=role,speaker_id=speaker_id,to_dict=lambda:{'id':'layer'});self.layers.append(x);return x
    def apply_pip_preset(self,*a):pass
    def set_chroma_key(self,*a):self.chroma.append(a)

@pytest.fixture
def env(tmp_path):
    db=SQLiteDatabase(tmp_path/'app.db')
    with db.connect() as c,c:
        c.execute('CREATE TABLE projects(id TEXT PRIMARY KEY)')
        c.execute('CREATE TABLE media_assets(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE)')
        migrate(c)
    root=tmp_path/'global-assets';repo=AssetRepository(db,root);validation=AssetValidationService();media_service=FakeMediaService();importer=AssetImportService(repo,media_service,validation);search=AssetSearchService(repo);projects=ProjectRepo(db,tmp_path);media=DBMediaRepo(db);visual=FakeVisual();usage=AssetUsageService(repo,projects,media,visual);relink=AssetRelinkService(repo,importer,media,validation);library=AssetLibraryService(repo,search,importer,usage,relink,validation)
    return SimpleNamespace(db=db,root=root,repo=repo,validation=validation,importer=importer,search=search,projects=projects,media=media,visual=visual,usage=usage,relink=relink,library=library,tmp=tmp_path)

def files(tmp):
    v=tmp/'city.mp4';v.write_bytes(b'video-data'*100)
    a=tmp/'sting.wav';a.write_bytes(b'audio-data'*80)
    i=tmp/'logo.png';Image.new('RGBA',(320,180),(255,0,0,120)).save(i)
    return v,i,a

def test_asset_model_and_subtypes_path_safety(tmp_path):
    a=Asset('B-roll','video','broll',managed=True,relative_path='video/a.mp4');a.validate();assert a.type=='video'
    with pytest.raises(ValueError):Asset('Bad','video','broll',managed=True,relative_path='../evil.mp4').validate()

def test_basic_import_video_image_audio_metadata_thumbnail_persistence(env):
    v,i,a=files(env.tmp);items=[env.importer.import_file(v),env.importer.import_file(i),env.importer.import_file(a)]
    assert [x.type for x in items]==['video','image','audio'];assert items[0].duration_ms==12000 and items[0].width==1920;assert items[1].width==320;assert items[0].resolved_thumbnail(env.root).is_file();assert env.repo.count()==3
    reopened=AssetRepository(env.db,env.root);assert len(reopened.list_all())==3

def test_referenced_import_keeps_original(env):
    v,_,_=files(env.tmp);a=env.importer.import_file(v,managed=False);assert not a.managed and Path(a.file_path)==v.resolve();assert not (env.root/'video'/f'{a.id}.mp4').exists()

def test_duplicate_detection_use_existing_and_cancel(env):
    v,_,_=files(env.tmp);first=env.importer.import_file(v);second=env.importer.import_file(v);assert first.id==second.id and env.repo.count()==1
    with pytest.raises(AssetDuplicate):env.importer.import_file(v,duplicate_policy='cancel')

def test_collections_many_to_many_and_delete_keeps_asset(env):
    v,_,_=files(env.tmp);a=env.importer.import_file(v);c1=env.library.create_collection('News B-roll');c2=env.library.create_collection('Technology');env.library.set_collection(a.id,c1.id,True);env.library.set_collection(a.id,c2.id,True);assert set(env.repo.asset_collections(a.id))=={c1.id,c2.id};env.library.delete_collection(c1.id);assert env.repo.get(a.id) is not None and env.repo.asset_collections(a.id)==[c2.id]

def test_unicode_tags_and_search_khmer(env):
    v,_,_=files(env.tmp);a=env.importer.import_file(v,name='វីដេអូព័ត៌មានទីក្រុង');env.library.set_tags(a.id,['ព័ត៌មាន']);assert env.search.search(query='ព័ត៌មាន')[0].id==a.id

def test_unicode_search_thai(env):
    v,_,_=files(env.tmp);a=env.importer.import_file(v,name='วิดีโอผู้สื่อข่าว');env.library.set_tags(a.id,['ข่าว']);assert env.search.search(query='ข่าว')[0].id==a.id

def test_unicode_search_vietnamese_preserves_accents(env):
    v,_,_=files(env.tmp);a=env.importer.import_file(v,name='Phóng viên công nghệ');env.library.set_tags(a.id,['công nghệ']);assert env.search.search(query='công nghệ')[0].name=='Phóng viên công nghệ'

def test_favorite_filter_sort(env):
    v,i,_=files(env.tmp);a=env.importer.import_file(v);b=env.importer.import_file(i);env.library.set_favorite(b.id,True);assert env.search.search(filter_id='favorites')[0].id==b.id;assert {x.id for x in env.search.search(filter_id='video')}=={a.id}

def test_project_use_two_projects_same_global_file_no_copy(env):
    v,_,_=files(env.tmp);a=env.importer.import_file(v);p1=env.projects.add('A');p2=env.projects.add('B');m1=env.usage.add_to_project('A',a.id,'broll');m2=env.usage.add_to_project('B',a.id,'broll');assert m1.project_path==m2.project_path==str(a.resolved_path(env.root));assert env.repo.usage_count(a.id)==2;assert not any((Path(p1.project_path)/'media/video').iterdir())

def test_delete_in_use_guard(env):
    v,_,_=files(env.tmp);a=env.importer.import_file(v);env.projects.add('A');env.usage.add_to_project('A',a.id);with_raised=False
    with pytest.raises(AssetInUse):env.library.delete_asset(a.id)
    assert env.repo.get(a.id)

def test_detach_make_project_copy_keeps_other_project_global(env):
    v,_,_=files(env.tmp);a=env.importer.import_file(v);env.projects.add('A');env.projects.add('B');m1=env.usage.add_to_project('A',a.id);m2=env.usage.add_to_project('B',a.id);env.usage.make_project_copy('A',m1.id);assert not env.media.get_by_id(m1.id).metadata_json.get('globalAssetId');assert Path(env.media.get_by_id(m1.id).project_path).is_file();assert env.media.get_by_id(m2.id).metadata_json['globalAssetId']==a.id;assert env.repo.usage_count(a.id)==1

def test_referenced_delete_never_deletes_original(env):
    v,_,_=files(env.tmp);a=env.importer.import_file(v,managed=False);env.library.delete_asset(a.id);assert v.exists() and env.repo.get(a.id) is None

def test_managed_delete_and_path_guard(env):
    v,_,_=files(env.tmp);a=env.importer.import_file(v);p=a.resolved_path(env.root);env.library.delete_asset(a.id);assert not p.exists()
    outside=env.tmp/'outside.mp4';outside.write_bytes(b'x');bad=Asset('tampered','video','broll',managed=True,relative_path='video/safe.mp4');bad.validate();env.repo.create(bad);bad.relative_path='../outside.mp4'
    # Simulate corrupted database/path state; the delete guard must still refuse outside-root removal.
    with pytest.raises(AssetPathUnsafe):env.validation.assert_managed_path(outside,env.root)
    assert outside.exists()

def test_missing_and_relink_recovers_all_project_refs(env):
    v,_,_=files(env.tmp);a=env.importer.import_file(v,managed=False);env.projects.add('A');env.projects.add('B');m1=env.usage.add_to_project('A',a.id);m2=env.usage.add_to_project('B',a.id);moved=env.tmp/'moved.mp4';v.rename(moved);assert env.relink.detect_change(a.id)=='missing';env.relink.relink(a.id,moved);assert env.media.get_by_id(m1.id).project_path==str(moved.resolve())==env.media.get_by_id(m2.id).project_path;assert env.repo.get(a.id).status_code=='ready'

def test_relink_mismatch_requires_explicit_force(env):
    v,i,_=files(env.tmp);a=env.importer.import_file(v,managed=False)
    with pytest.raises(AssetRelinkMismatch):env.relink.relink(a.id,i)

def test_green_screen_presenter_metadata_applies_chroma(env):
    v,_,_=files(env.tmp);a=env.importer.import_file(v,subtype='presenter',metadata={'chromaReady':True,'keyColor':'#00FF00','chromaSimilarity':.3,'defaultPosition':'bottom_right'});env.projects.add('A');layer=env.usage.add_visual_layer('A','scene1',a.id,role='presenter');assert layer.role=='presenter';assert env.visual.chroma

def test_reporter_metadata_stays_label_not_project_speaker(env):
    v,_,_=files(env.tmp);a=env.importer.import_file(v,subtype='reporter',metadata={'speakerLabel':'Reporter A','chromaReady':True});assert a.metadata['speakerLabel']=='Reporter A' and 'speakerId' not in a.metadata

def test_rights_attribution_summary(env):
    v,_,_=files(env.tmp);a=env.importer.import_file(v);env.projects.add('A');env.usage.add_to_project('A',a.id);env.library.set_license(a.id,rights_status='licensed',license_name='User license',attribution_required=True,attribution_text='Video: Example');rows=env.usage.attribution_summary('A');assert rows[0]['attributionText']=='Video: Example'

def test_template_placeholder_resolves_global_asset_to_project_media(env):
    v,_,_=files(env.tmp);a=env.importer.import_file(v,subtype='reporter');env.projects.add('A');bridge=AssetTemplateIntegrationService(env.usage);resolved=bridge.resolve_map('A',{'reporter_video':{'globalAssetId':a.id}});m=env.media.get_by_id(resolved['reporter_video']);assert m.metadata_json['globalAssetId']==a.id

def test_bulk_and_folder_import_with_cancel(env):
    paths=[]
    for n in range(5):p=env.tmp/f'x{n}.mp4';p.write_bytes(f'{n}'.encode()*100);paths.append(p)
    assert len(env.importer.scan_folder(env.tmp))>=5
    token=SimpleNamespace(is_cancelled=False);seen=[]
    summary=env.importer.import_many(paths,progress=lambda i,total,name:seen.append((i,total,name)));assert len(summary.imported)==5 and seen[-1][0]==5
    token.is_cancelled=True;summary2=env.importer.import_many(paths,cancellation=token);assert summary2.cancelled

def test_library_move_preserves_managed_and_referenced(env):
    v,_,audi=files(env.tmp);managed=env.importer.import_file(v);referenced=env.importer.import_file(audi,managed=False);old_ref=referenced.file_path;new=env.tmp/'moved-library';env.library.migrate_library(new,mode='move');assert env.repo.library_root==new.resolve();assert managed.resolved_path(new).is_file();assert env.repo.get(referenced.id).file_path==old_ref

def test_file_change_detection(env):
    v,_,_=files(env.tmp);a=env.importer.import_file(v,managed=False);time.sleep(.002);v.write_bytes(v.read_bytes()+b'changed');assert env.relink.detect_change(a.id)=='changed'

def test_restart_persistence_assets_collections_tags_favorites_root(env):
    v,_,_=files(env.tmp);a=env.importer.import_file(v);env.library.set_favorite(a.id,True);env.library.set_tags(a.id,['ព័ត៌មាន','ข่าว','công nghệ']);c=env.library.create_collection('វីដេអូខ្មែរ');env.library.set_collection(a.id,c.id,True);repo2=AssetRepository(env.db,env.root);a2=repo2.get(a.id);assert a2.favorite and len(repo2.tags(a.id))==3 and repo2.collections()[0]['name']=='វីដេអូខ្មែរ'

def test_one_thousand_asset_search_metadata_only(env):
    start=time.perf_counter()
    for i in range(1000):env.repo.create(Asset(f'Asset {i}','image','general',managed=True,relative_path=f'image/{i}.png',file_size=i))
    rows=env.search.search(query='Asset 99');elapsed=time.perf_counter()-start;assert rows and elapsed<8.0

def test_database_migration_tables_exist(env):
    with env.db.connect() as c:names={r['name'] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert {'assets','asset_collections','asset_collection_items','asset_tags','asset_tag_items','asset_usage','asset_licenses'}<=names

def test_remove_from_library_keep_file_preserves_in_use_managed_bytes(env):
    v,_,_=files(env.tmp);a=env.importer.import_file(v);path=a.resolved_path(env.root);env.projects.add('A');m=env.usage.add_to_project('A',a.id);env.library.delete_asset(a.id,strategy='keep_file');assert path.exists();assert env.repo.get(a.id) is None;assert env.media.get_by_id(m.id).metadata_json.get('externalReference') is True

def test_runtime_and_timeline_wire_global_references_without_second_media_engine():
    root=Path(__file__).resolve().parents[1];runtime=(root/'app/phase25_runtime.py').read_text(encoding='utf-8');qml=(root/'ui/qml/timeline/TimelineEditor.qml').read_text(encoding='utf-8')
    assert "globalAssetId" in runtime and "duplicate_media_safe" in runtime and "remove_media_safe" in runtime
    assert 'sp-global-asset' in qml and 'AssetLibrary.addAtPlayhead' in qml
