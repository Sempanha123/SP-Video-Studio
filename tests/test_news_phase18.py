from __future__ import annotations

import json
import socket
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from domain.news_claim import NewsClaimStatus
from services.news_brief_service import NewsBriefService
from services.news_claim_service import NewsClaimService
from services.news_errors import NewsClaimUnsupported, NewsSourceBlocked, NewsSourceSecurityError
from services.news_extraction_service import NewsExtractionService
from services.news_script_service import NewsScriptService
from services.news_service import NewsService
from services.news_source_fetch_service import HtmlArticleExtractor, PlainTextExtractor, PublicURLPolicy
from services.news_source_service import NewsSourceService
from services.news_validation_service import NewsValidationService, source_fingerprint
from services.project_service import ProjectService
from services.script_analysis_service import ScriptAnalysisService
from services.script_service import ScriptService
from storage.database import SQLiteDatabase
from storage.repositories.news_repository import NewsRepository
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.script_repository import ScriptRepository


def _resolver(ip: str):
    def resolve(host, port, *args, **kwargs):
        family = socket.AF_INET6 if ':' in ip else socket.AF_INET
        return [(family, socket.SOCK_STREAM, 6, '', (ip, port, 0, 0) if family == socket.AF_INET6 else (ip, port))]
    return resolve


def make_system(tmp_path: Path, *, language='en'):
    db=SQLiteDatabase(tmp_path/'app.db'); db.initialize()
    projects=ProjectRepository(db); news_repo=NewsRepository(db); scripts=ScriptRepository(db)
    ps=ProjectService(projects,tmp_path/'projects'); project=ps.create_project('News Test','news',language,'9:16',30)
    script_service=ScriptService(scripts,projects,ScriptAnalysisService())
    sources=NewsSourceService(news_repo,projects)
    extraction=NewsExtractionService(); claims=NewsClaimService(news_repo,extraction); validation=NewsValidationService(news_repo); briefs=NewsBriefService(news_repo)
    news_scripts=NewsScriptService(news_repo,script_service,briefs,validation)
    news=NewsService(news_repo,projects,sources,claims,briefs,news_scripts,validation)
    ps.set_script_service(script_service); ps.set_news_service(news)
    news.load_or_create(project.id)
    return SimpleNamespace(db=db,projects=projects,repo=news_repo,project_service=ps,project=project,script_service=script_service,sources=sources,claims=claims,briefs=briefs,validation=validation,news_scripts=news_scripts,news=news)


def add_supported_claim(sys, text='Company announced 100 units on September 10.', *, title='Source A'):
    src=sys.sources.add_manual(sys.project.id,title,text,publisher='Example Org')
    snap=sys.repo.latest_snapshot(sys.project.id,src.id)
    claim=sys.claims.create_manual(sys.project.id,text,source_id=src.id,snapshot_id=snap.id,evidence_text=text)
    sys.claims.approve(sys.project.id,claim.id)
    return src,snap,claim


def test_news_schema_v15_and_tables(tmp_path):
    s=make_system(tmp_path)
    assert s.db.current_version()==16
    with s.db.connect() as c:
        names={r['name'] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'news_%'")}
    assert {'news_projects','news_sources','news_source_snapshots','news_claims','news_evidence','news_briefs','news_brief_items','news_script_mappings'} <= names

@pytest.mark.parametrize('ip',['127.0.0.1','::1','10.2.3.4','172.16.9.9','172.31.0.4','192.168.1.2','169.254.1.1'])
def test_ssrf_private_targets_are_blocked(ip):
    with pytest.raises(NewsSourceSecurityError): PublicURLPolicy(_resolver(ip)).validate('https://example.com/article')

@pytest.mark.parametrize('scheme',['file','ftp','gopher'])
def test_non_http_schemes_are_blocked(scheme):
    with pytest.raises(NewsSourceSecurityError): PublicURLPolicy(_resolver('8.8.8.8')).validate(f'{scheme}://example.com/a')


def test_http_https_public_are_allowed():
    p=PublicURLPolicy(_resolver('8.8.8.8'))
    assert p.validate('http://example.com').scheme=='http'
    assert p.validate('https://example.com').scheme=='https'


def test_html_extraction_ignores_navigation_and_footer():
    html=b'''<html><head><title>Test Story</title><meta name="author" content="Reporter"></head><body><nav>Navigation links links links</nav><article><h1>Test Story</h1><p>The company announced 100 units on September 10.</p><p>Important article context belongs here.</p></article><footer>Footer privacy cookies links</footer></body></html>'''
    x=HtmlArticleExtractor().extract(html,content_type='text/html',charset='utf-8',url='https://example.com/story')
    assert x.title=='Test Story' and x.author=='Reporter'
    assert 'announced 100 units' in x.content_text
    assert 'Navigation links' not in x.content_text and 'Footer privacy' not in x.content_text


def test_plain_text_khmer_decode():
    text='ក្រុមហ៊ុនបានប្រកាសផលិតផលថ្មីនៅថ្ងៃនេះ។'
    x=PlainTextExtractor().extract(text.encode(),content_type='text/plain',charset='utf-8',url='https://example.com')
    assert x.content_text==text


def test_manual_source_snapshot_hash_and_restart(tmp_path):
    s=make_system(tmp_path)
    src=s.sources.add_manual(s.project.id,'Manual','A sourced fact 100.')
    a=s.repo.latest_snapshot(s.project.id,src.id)
    assert len(a.content_hash)==64
    again=NewsRepository(SQLiteDatabase(tmp_path/'app.db'))
    b=again.latest_snapshot(s.project.id,src.id)
    assert b.content_text=='A sourced fact 100.' and b.content_hash==a.content_hash


def test_source_version_preserves_old_claim_snapshot(tmp_path):
    s=make_system(tmp_path)
    src=s.sources.add_manual(s.project.id,'Manual','Value is 100.')
    a=s.repo.latest_snapshot(s.project.id,src.id)
    claim=s.claims.create_manual(s.project.id,'Value is 100.',source_id=src.id,snapshot_id=a.id,evidence_text='Value is 100.')
    b=s.sources.update_manual_text(s.project.id,src.id,'Value is 120.')
    assert a.id!=b.id and len(s.repo.snapshots(src.id))==2
    evidence=s.repo.evidence_for_claim(claim.id)[0]
    assert evidence.snapshot_id==a.id and s.repo.snapshot(a.id).content_text=='Value is 100.'


def test_claim_requires_evidence_then_approves(tmp_path):
    s=make_system(tmp_path)
    claim=s.claims.create_manual(s.project.id,'Unsupported claim')
    with pytest.raises(NewsClaimUnsupported): s.claims.approve(s.project.id,claim.id)
    assert s.repo.claim(s.project.id,claim.id).status_code=='unsupported'
    src=s.sources.add_manual(s.project.id,'Evidence','Unsupported claim')
    snap=s.repo.latest_snapshot(s.project.id,src.id)
    s.claims.add_evidence(s.project.id,claim.id,src.id,snap.id,'Unsupported claim')
    approved=s.claims.approve(s.project.id,claim.id)
    assert approved.status_code=='approved'


def test_manual_claim_from_evidence_and_lock_edit(tmp_path):
    s=make_system(tmp_path); src=s.sources.add_manual(s.project.id,'S','Price is 100 USD.');snap=s.repo.latest_snapshot(s.project.id,src.id)
    c=s.claims.create_manual(s.project.id,'Price is 100 USD.',claim_type='number',source_id=src.id,snapshot_id=snap.id,evidence_text='Price is 100 USD.')
    s.claims.approve(s.project.id,c.id); s.claims.set_locked(s.project.id,c.id,True)
    with pytest.raises(Exception): s.claims.edit(s.project.id,c.id,'Price is 120 USD.')
    s.claims.set_locked(s.project.id,c.id,False); edited=s.claims.edit(s.project.id,c.id,'Price is 120 USD.')
    assert edited.status_code=='needs_review' and edited.user_modified


def test_claim_merge_preserves_evidence(tmp_path):
    s=make_system(tmp_path); src=s.sources.add_manual(s.project.id,'S','Company announced 100 units. Company announced one hundred units.');snap=s.repo.latest_snapshot(s.project.id,src.id)
    a=s.claims.create_manual(s.project.id,'Company announced 100 units.',source_id=src.id,snapshot_id=snap.id,evidence_text='Company announced 100 units.')
    b=s.claims.create_manual(s.project.id,'Company announced one hundred units.',source_id=src.id,snapshot_id=snap.id,evidence_text='Company announced one hundred units.')
    s.claims.merge(s.project.id,a.id,b.id)
    assert len(s.repo.evidence_for_claim(a.id))==2 and s.repo.claim(s.project.id,b.id).status_code=='rejected'


def test_possible_duplicate_is_only_suggestion(tmp_path):
    s=make_system(tmp_path); a=s.claims.create_manual(s.project.id,'Company announced the product today.'); b=s.claims.create_manual(s.project.id,'Company announced the product today!')
    pairs=s.claims.possible_duplicates(s.project.id,.7)
    assert any({x[0],x[1]}=={a.id,b.id} for x in pairs)
    assert s.repo.claim(s.project.id,a.id).status_code=='candidate'


def test_number_conflict_no_automatic_winner(tmp_path):
    s=make_system(tmp_path)
    a=s.claims.create_manual(s.project.id,'The company reported revenue of 100 million in 2026.')
    b=s.claims.create_manual(s.project.id,'The company reported revenue of 120 million in 2026.')
    conflicts=s.claims.detect_conflicts(s.project.id)
    assert conflicts and s.repo.claim(s.project.id,a.id).status_code=='conflicting' and s.repo.claim(s.project.id,b.id).status_code=='conflicting'


def test_quote_metadata_preserves_original(tmp_path):
    s=make_system(tmp_path); src=s.sources.add_manual(s.project.id,'Quote','Alex said “We will launch tomorrow.”');snap=s.repo.latest_snapshot(s.project.id,src.id)
    c=s.claims.create_manual(s.project.id,'Alex said the launch is tomorrow.',claim_type='quote',source_id=src.id,snapshot_id=snap.id,evidence_text='Alex said “We will launch tomorrow.”',quote={'text':'We will launch tomorrow.','speaker':'Alex','kind':'exact','original':'We will launch tomorrow.'})
    got=s.repo.claim(s.project.id,c.id)
    assert got.quote_kind=='exact' and got.original_quote=='We will launch tomorrow.' and got.speaker=='Alex'


def test_brief_contains_only_approved_claim_links(tmp_path):
    s=make_system(tmp_path); _,_,approved=add_supported_claim(s); s.claims.create_manual(s.project.id,'Candidate only')
    brief=s.briefs.create_from_approved(s.project.id); items=s.repo.brief_items(brief.id)
    assert [i.claim_id for i in items]==[approved.id]
    s.briefs.set_status(s.project.id,brief.id,'approved'); assert s.repo.brief(s.project.id,brief.id).status=='approved'


def test_source_fingerprint_and_brief_outdated_on_claim_change(tmp_path):
    s=make_system(tmp_path);_,_,claim=add_supported_claim(s); b=s.briefs.create_from_approved(s.project.id);s.briefs.set_status(s.project.id,b.id,'approved'); before=b.source_fingerprint
    s.claims.edit(s.project.id,claim.id,'Company announced 101 units on September 10.')
    got,_=s.briefs.get(s.project.id,b.id)
    assert source_fingerprint(s.repo,s.project.id)!=before and got.status=='outdated'


def test_grounded_script_maps_claims_and_manual_fact_becomes_unsupported(tmp_path):
    s=make_system(tmp_path);_,_,claim=add_supported_claim(s); brief=s.briefs.create_from_approved(s.project.id)
    script,sections,mappings=s.news_scripts.build_script(s.project.id,brief_id=brief.id)
    factual=[m for m in mappings if m.mapping_type=='factual']
    assert factual and claim.id in factual[0].claim_ids
    sections[0].content += '\n\nOfficials confirmed 999 additional units today.'
    s.script_service.save_section(s.project.id,sections[0])
    report=s.news_scripts.validate_grounding(s.project.id,script.id)
    assert report['unsupported']>=1


def test_script_edit_invalidates_mapping_but_not_claim(tmp_path):
    s=make_system(tmp_path);_,_,claim=add_supported_claim(s);script,sections,_=s.news_scripts.build_script(s.project.id)
    sections[0].content='Company denied 100 units on September 10.';s.script_service.save_section(s.project.id,sections[0])
    report=s.news_scripts.validate_grounding(s.project.id,script.id)
    assert report['needsReview']>=1 or report['unsupported']>=1
    assert s.repo.claim(s.project.id,claim.id).status_code=='approved'


def test_khmer_workflow_unicode_search_and_persistence(tmp_path):
    s=make_system(tmp_path,language='km'); text='ក្រុមហ៊ុនបានប្រកាសផលិតផលថ្មីនៅថ្ងៃនេះ។ តម្លៃគឺ 100 ដុល្លារ។'
    src=s.sources.add_manual(s.project.id,'ប្រភពខ្មែរ',text,language='km')
    snap=s.repo.latest_snapshot(s.project.id,src.id); c=s.claims.create_manual(s.project.id,'តម្លៃគឺ 100 ដុល្លារ។',source_id=src.id,snapshot_id=snap.id,evidence_text='តម្លៃគឺ 100 ដុល្លារ។')
    s.claims.approve(s.project.id,c.id); brief=s.briefs.create_from_approved(s.project.id); script,sections,_=s.news_scripts.build_script(s.project.id,brief_id=brief.id)
    assert 'តម្លៃ' in sections[0].content and s.sources.search(s.project.id,'ក្រុមហ៊ុន')[0].id==src.id
    reloaded=NewsRepository(SQLiteDatabase(tmp_path/'app.db')); assert 'តម្លៃ' in reloaded.claim(s.project.id,c.id).text


def test_source_removal_marks_last_supported_claim_unsupported(tmp_path):
    s=make_system(tmp_path);src,_,claim=add_supported_claim(s); s.sources.remove(s.project.id,src.id)
    assert s.repo.claim(s.project.id,claim.id).status_code=='unsupported'


def test_source_export_excludes_article_body_by_default(tmp_path):
    s=make_system(tmp_path);s.sources.add_manual(s.project.id,'Manual','secret article body 100')
    out=s.sources.export_sources(s.project.id,tmp_path/'sources.json'); data=json.loads(out.read_text())
    assert 'contentText' not in data['sources'][0]['snapshot']
    txt=s.sources.source_list_text(s.project.id); assert 'secret article body' not in txt


def test_project_duplication_remaps_news_ids_and_managed_source_copy(tmp_path):
    s=make_system(tmp_path); local=tmp_path/'ព័ត៌មាន.txt';local.write_text('Revenue 100 million.',encoding='utf-8')
    src=s.sources.add_local(s.project.id,local,language='km'); snap=s.repo.latest_snapshot(s.project.id,src.id)
    claim=s.claims.create_manual(s.project.id,'Revenue 100 million.',source_id=src.id,snapshot_id=snap.id,evidence_text='Revenue 100 million.');s.claims.approve(s.project.id,claim.id)
    s.briefs.create_from_approved(s.project.id); s.news_scripts.build_script(s.project.id)
    dup=s.project_service.duplicate_project(s.project.id)
    sources=s.repo.list_sources(dup.id); claims=s.repo.list_claims(dup.id); briefs=s.repo.list_briefs(dup.id); mappings=s.repo.mappings(dup.id)
    assert sources and claims and briefs and mappings
    assert sources[0].id!=src.id and claims[0].id!=claim.id
    assert Path(sources[0].source_path).is_file() and Path(sources[0].source_path).is_relative_to(Path(dup.project_path))
    ev=s.repo.evidence_for_claim(claims[0].id)[0]; assert ev.source_id==sources[0].id and ev.snapshot_id!=snap.id
    assert all(m.project_id==dup.id for m in mappings)


def test_project_delete_cascades_news_and_managed_files(tmp_path):
    s=make_system(tmp_path); external=tmp_path/'external.txt';external.write_text('Fact 100',encoding='utf-8');src=s.sources.add_local(s.project.id,external)
    project_path=Path(s.project.project_path); s.project_service.delete_project(s.project.id)
    assert external.exists() and not project_path.exists()
    assert s.repo.get_project(s.project.id) is None and s.repo.list_sources(s.project.id)==[]


def test_50_sources_300_claims_remain_queryable(tmp_path):
    s=make_system(tmp_path)
    start=time.perf_counter()
    for i in range(50): s.sources.add_manual(s.project.id,f'Source {i}',f'Source value {i} is {i}.')
    sources=s.repo.list_sources(s.project.id)
    for i in range(300):
        src=sources[i%50];snap=s.repo.latest_snapshot(s.project.id,src.id); text=f'Claim {i} value {i}.'
        s.claims.create_manual(s.project.id,text,source_id=src.id,snapshot_id=snap.id,evidence_text=snap.content_text)
    assert len(s.repo.list_sources(s.project.id))==50 and len(s.repo.list_claims(s.project.id))==300
    assert time.perf_counter()-start < 12

class _Headers:
    def __init__(self, content_type='text/html', charset='utf-8', extra=None):
        self._content_type=content_type; self._charset=charset; self._extra=dict(extra or {})
    def get_content_type(self): return self._content_type
    def get_content_charset(self): return self._charset
    def get(self,key,default=None): return self._extra.get(key,default)

class _Response:
    def __init__(self, data:bytes, url='https://example.com/a', content_type='text/html', extra=None):
        self.data=data; self.headers=_Headers(content_type,extra=extra); self._url=url
    def read(self,n=-1): return self.data if n<0 else self.data[:n]
    def geturl(self): return self._url

class _Opener:
    def __init__(self, actions): self.actions=list(actions); self.requests=[]
    def open(self, req, timeout=None):
        import urllib.error
        self.requests.append(req.full_url)
        action=self.actions.pop(0)
        if isinstance(action,Exception): raise action
        return action


def test_redirect_to_private_ip_is_rejected():
    import urllib.error
    from email.message import Message
    from services.news_source_fetch_service import NewsSourceFetchService
    h=Message(); h['Location']='http://private.example/internal'
    redirect=urllib.error.HTTPError('https://public.example/a',302,'Found',h,None)
    def resolver(host,port,*args,**kwargs):
        ip='8.8.8.8' if host=='public.example' else '127.0.0.1'
        return [(socket.AF_INET,socket.SOCK_STREAM,6,'',(ip,port))]
    svc=NewsSourceFetchService(policy=PublicURLPolicy(resolver),opener=_Opener([redirect]))
    with pytest.raises(NewsSourceSecurityError): svc.fetch('https://public.example/a')


def test_fetch_size_limit_and_429_message():
    import urllib.error
    from email.message import Message
    from services.news_source_fetch_service import NewsSourceFetchService
    svc=NewsSourceFetchService(policy=PublicURLPolicy(_resolver('8.8.8.8')),max_bytes=1024,opener=_Opener([_Response(b'x'*1500,content_type='text/plain')]))
    with pytest.raises(NewsSourceBlocked): svc.fetch('https://example.com/a')
    err=urllib.error.HTTPError('https://example.com/a',429,'limited',Message(),None)
    svc=NewsSourceFetchService(policy=PublicURLPolicy(_resolver('8.8.8.8')),opener=_Opener([err]))
    with pytest.raises(Exception,match='temporarily limited'): svc.fetch('https://example.com/a')


def test_url_refresh_creates_new_snapshot_and_old_evidence_resolves(tmp_path):
    from services.news_source_fetch_service import NewsSourceFetchService
    html1=b'<article><p>Reported value is 100 units on September 10.</p></article>'
    html2=b'<article><p>Reported value is 120 units on September 11.</p></article>'
    fetch=NewsSourceFetchService(policy=PublicURLPolicy(_resolver('8.8.8.8')),opener=_Opener([_Response(html1),_Response(html2)]))
    s=make_system(tmp_path); s.sources.fetcher=fetch
    src=s.sources.add_url(s.project.id,'https://example.com/a')
    a=s.repo.latest_snapshot(s.project.id,src.id)
    claim=s.claims.create_manual(s.project.id,'Reported value is 100 units on September 10.',source_id=src.id,snapshot_id=a.id,evidence_text='Reported value is 100 units on September 10.')
    b=s.sources.refresh(s.project.id,src.id)
    assert b.id!=a.id and s.repo.source(s.project.id,src.id).source_updated
    assert s.repo.evidence_for_claim(claim.id)[0].snapshot_id==a.id and s.repo.snapshot(a.id) is not None


def test_date_conflict_is_flagged_without_winner(tmp_path):
    s=make_system(tmp_path)
    a=s.claims.create_manual(s.project.id,'The launch was reported on September 10, 2026.')
    b=s.claims.create_manual(s.project.id,'The launch was reported on September 11, 2026.')
    conflicts=s.claims.detect_conflicts(s.project.id)
    assert conflicts and {s.repo.claim(s.project.id,a.id).status_code,s.repo.claim(s.project.id,b.id).status_code}=={'conflicting'}


def test_translated_quote_metadata_can_preserve_original(tmp_path):
    s=make_system(tmp_path)
    c=s.claims.create_manual(s.project.id,'អាឡិចបាននិយាយថានឹងបើកដំណើរការថ្ងៃស្អែក។',claim_type='quote',quote={'text':'នឹងបើកដំណើរការថ្ងៃស្អែក។','speaker':'Alex','kind':'translated_quote','original':'We will launch tomorrow.'})
    got=s.repo.claim(s.project.id,c.id); assert got.quote_kind=='translated_quote' and got.original_quote=='We will launch tomorrow.'


def test_translation_scene_and_director_handoffs_reuse_existing_services(tmp_path):
    s=make_system(tmp_path); add_supported_claim(s); script,_,_=s.news_scripts.build_script(s.project.id)
    class FakeTranslationRepo:
        def update_translation(self,item): self.item=item; return item
    class FakeTranslation:
        def __init__(self): self.repository=FakeTranslationRepo(); self.calls=[]
        def create_from_script(self,project_id,script_id,target_language,engine_id='manual'):
            self.calls.append((project_id,script_id,target_language,engine_id)); return SimpleNamespace(metadata={},translation_id='t1')
    class FakeScene:
        def __init__(self,section_id,name): self.script_section_id=section_id; self.name=name; self.metadata={}; self.id='scene1'
    class FakeSceneRepo:
        def update(self,item): return item
    class FakeScenes:
        def __init__(self): self.repository=FakeSceneRepo(); self.calls=[]
        def create_from_script(self,project_id,append=False):
            self.calls.append(project_id); section=s.script_service.repository.list_sections(script.id)[0]; return [FakeScene(section.id,section.title)]
    class FakeDirector:
        def __init__(self): self.requests=[]
        def create_plan(self,req): self.requests.append(req); return ('plan',[])
    ft,fs,fd=FakeTranslation(),FakeScenes(),FakeDirector()
    s.news_scripts.translation_service=ft; s.news_scripts.scene_service=fs; s.news_scripts.director_service=fd
    tr=s.news_scripts.create_translation(s.project.id,'km'); assert tr.metadata['news_claim_provenance'] and ft.calls
    scenes=s.news_scripts.create_scenes(s.project.id); assert scenes[0].metadata['news_role'] in {'lead','context','background','outro'}
    s.news_scripts.create_director_plan(s.project.id); assert fd.requests[0].workflow=='news' and fd.requests[0].metadata['newsGrounded'] is True


def test_news_project_metadata_update_roundtrip(tmp_path):
    s=make_system(tmp_path)
    m=s.news.update_setup(s.project.id,topic='AI product update',angle='technology',region='Cambodia',language='en',target_audience='general',target_duration_ms=90000,platform='youtube')
    r=NewsRepository(SQLiteDatabase(tmp_path/'app.db')).get_project(s.project.id)
    assert r.topic=='AI product update' and r.angle=='technology' and r.target_duration_ms==90000 and r.platform=='youtube'


def test_source_timeout_maps_to_typed_fetch_error():
    from services.news_errors import NewsSourceFetchError
    from services.news_source_fetch_service import NewsSourceFetchService
    opener = _Opener([socket.timeout('timed out')])
    svc = NewsSourceFetchService(
        policy=PublicURLPolicy(_resolver('8.8.8.8')),
        timeout=0.01,
        opener=opener,
    )
    with pytest.raises(NewsSourceFetchError, match='timed out'):
        svc.fetch('https://example.com/a')


def test_english_news_three_sources_five_claims_brief_and_script(tmp_path):
    s = make_system(tmp_path, language='en')
    source_texts = [
        ('Official', 'The company announced Product X on September 10, 2026.'),
        ('Report', 'Product X is priced at 100 USD and launches in October 2026.'),
        ('Background', 'The company previously released Product W in 2025.'),
    ]
    sources = [s.sources.add_manual(s.project.id, name, text, publisher=name) for name, text in source_texts]
    claim_specs = [
        (0, 'The company announced Product X on September 10, 2026.'),
        (1, 'Product X is priced at 100 USD.'),
        (1, 'Product X launches in October 2026.'),
        (2, 'The company previously released Product W in 2025.'),
        (0, 'Product X was announced by the company.'),
    ]
    for source_index, text in claim_specs:
        src = sources[source_index]
        snap = s.repo.latest_snapshot(s.project.id, src.id)
        claim = s.claims.create_manual(
            s.project.id,
            text,
            source_id=src.id,
            snapshot_id=snap.id,
            evidence_text=snap.content_text,
        )
        s.claims.approve(s.project.id, claim.id)
    brief = s.briefs.create_from_approved(s.project.id, title='60-second Short Update')
    script, sections, mappings = s.news_scripts.build_script(s.project.id, brief_id=brief.id, style='short_update')
    assert len(s.repo.list_sources(s.project.id)) == 3
    assert len([c for c in s.repo.list_claims(s.project.id) if c.status_code == 'approved']) == 5
    assert sections and mappings
    grounding = s.news_scripts.validate_grounding(s.project.id, script.id)
    assert grounding['unsupported'] == 0
    assert grounding['grounded'] >= 1


def test_restart_restores_full_news_provenance_graph(tmp_path):
    s = make_system(tmp_path)
    src_a = s.sources.add_manual(s.project.id, 'Official', 'Company announced 100 units on September 10.')
    src_b = s.sources.add_manual(s.project.id, 'Report', 'A report also stated 100 units on September 10.')
    snap_a = s.repo.latest_snapshot(s.project.id, src_a.id)
    snap_b = s.repo.latest_snapshot(s.project.id, src_b.id)
    claim = s.claims.create_manual(
        s.project.id,
        'Company announced 100 units on September 10.',
        source_id=src_a.id,
        snapshot_id=snap_a.id,
        evidence_text='Company announced 100 units on September 10.',
    )
    s.claims.add_evidence(
        s.project.id,
        claim.id,
        src_b.id,
        snap_b.id,
        'A report also stated 100 units on September 10.',
    )
    s.claims.approve(s.project.id, claim.id)
    brief = s.briefs.create_from_approved(s.project.id)
    script, _, mappings = s.news_scripts.build_script(s.project.id, brief_id=brief.id)
    assert mappings

    db2 = SQLiteDatabase(tmp_path / 'app.db')
    db2.initialize()
    repo2 = NewsRepository(db2)
    assert repo2.get_project(s.project.id) is not None
    re_sources = repo2.list_sources(s.project.id)
    re_claim = repo2.claim(s.project.id, claim.id)
    re_evidence = repo2.evidence_for_claim(claim.id)
    re_briefs = repo2.list_briefs(s.project.id)
    re_mappings = repo2.mappings(s.project.id, script.id)
    assert {src.id for src in re_sources} == {src_a.id, src_b.id}
    assert re_claim is not None and re_claim.status_code == 'approved'
    assert {ev.snapshot_id for ev in re_evidence} == {snap_a.id, snap_b.id}
    assert re_briefs and re_briefs[0].brief_id == brief.id
    assert re_mappings and all(claim.id in m.claim_ids for m in re_mappings if m.mapping_type == 'factual')


def test_phase17_schema_v14_upgrades_to_news_schema_v15(tmp_path):
    import sqlite3
    from domain.project import utc_now_iso
    from storage.migrations import MIGRATIONS

    path = tmp_path / 'upgrade.db'
    connection = sqlite3.connect(path)
    connection.execute(
        'CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)'
    )
    for migration in MIGRATIONS:
        if migration.version > 14:
            continue
        migration.apply(connection)
        connection.execute(
            'INSERT INTO schema_migrations(version, name, applied_at) VALUES (?, ?, ?)',
            (migration.version, migration.name, utc_now_iso()),
        )
    connection.commit()
    connection.close()

    db = SQLiteDatabase(path)
    assert db.current_version() == 14
    db.initialize()
    assert db.current_version() == 16
    with db.connect() as c:
        assert c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news_sources'").fetchone()
