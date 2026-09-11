from __future__ import annotations

import csv
import json
import sqlite3
import time
from pathlib import Path

import pytest

from domain.asset import Asset
from domain.batch import Batch, BatchStatus
from domain.batch_errors import BatchInvalidInput, BatchMappingError
from domain.batch_item import BatchItem, BatchItemStatus
from domain.batch_mapping import BatchMapping
from domain.batch_stage import BatchStage, BatchStageState, BatchStageStatus
from domain.batch_variant import BatchVariantConfig
from domain.template import Template
from domain.template_placeholder import TemplatePlaceholder
from services.batch_asset_service import BatchAssetService
from services.batch_execution_service import BatchExecutionService
from services.batch_import_service import BatchImportService
from services.batch_mapping_service import BatchMappingService, safe_relative_output
from services.batch_recovery_service import BatchRecoveryService
from services.batch_service import BatchService
from services.batch_validation_service import BatchValidationService
from services.batch_variant_service import BatchVariantService
from storage.database import SQLiteDatabase
from storage.migrations.m023_create_batch_factory import migrate as migrate_batch
from storage.repositories.batch_item_repository import BatchItemRepository
from storage.repositories.batch_repository import BatchRepository
from workers.batch_scheduler import BatchScheduler
from workers.batch_worker import BatchWorker
from workers.worker_pool import WorkerPool


class FakeLanguageService:
    codes = {"en", "km", "th", "vi"}
    def __init__(self, translation=True): self.translation = translation
    def get(self, code):
        if code not in self.codes: raise KeyError(code)
        return code
    def supports_tts(self, code, engine_id="voxcpm2"): return code in self.codes and engine_id == "voxcpm2"
    def supports_translation_pair(self, source, target, engine_id=None): return bool(self.translation and source in self.codes and target in self.codes and source != target)


class FakeAssetRepository:
    def __init__(self, assets=None, collections=None):
        self._assets = {a.id:a for a in (assets or [])}
        self._collections = {k:set(v) for k,v in (collections or {}).items()}
    def get(self, asset_id): return self._assets.get(asset_id)
    def list_all(self): return list(self._assets.values())
    def assets_in_collection(self, cid): return set(self._collections.get(cid, set()))


def mkasset(name, asset_id, *, status="ready"):
    return Asset(asset_id=asset_id, name=name, asset_type="image", subtype="background", managed=False, file_path=f"/tmp/{asset_id}.png", file_size=1, status=status)


def template(*, workflow="video", placeholders=None, version="1.0", template_id="tpl-1", languages=("en","km","th","vi"), aspects=("16:9","9:16","1:1")):
    return Template(name="Batch Template", template_type="project", category="Video", description="", workflow=workflow, version=version, builtin=False, template_id=template_id, supported_languages=languages, supported_aspect_ratios=aspects, placeholders=list(placeholders or []))


def text_ph(pid, required=False): return TemplatePlaceholder(pid, pid.replace("_"," ").title(), "text", required=required)
def image_ph(pid, required=False): return TemplatePlaceholder(pid, pid.replace("_"," ").title(), "image", required=required)
def voice_ph(pid="voice", required=True, role=""): return TemplatePlaceholder(pid, "Voice", "voice", required=required, role=role)


def make_db(tmp_path):
    path = tmp_path / "batch.sqlite"
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys=ON")
    migrate_batch(conn)
    conn.commit(); conn.close()
    db = SQLiteDatabase(path)
    return db, BatchRepository(db), BatchItemRepository(db)


def make_services(tmp_path, *, assets=None, collections=None, translation=True, voice_available=True):
    db, batches, items = make_db(tmp_path)
    imports = BatchImportService(); mapping = BatchMappingService(); variants = BatchVariantService()
    asset_service = BatchAssetService(FakeAssetRepository(assets, collections))
    languages = FakeLanguageService(translation=translation)
    def voice_resolver(voice, language, role=""):
        return {"available": bool(voice_available and voice and language in languages.codes), "voiceId":voice, "engine":"voxcpm2", "role":role}
    validation = BatchValidationService(mapping, variants, language_service=languages, asset_service=asset_service, voice_resolver=voice_resolver)
    service = BatchService(batches, items, imports, mapping, variants, validation)
    return db,batches,items,imports,mapping,variants,asset_service,validation,service


def create_ready_batch(tmp_path, *, rows=None, tpl=None, mappings=None, variant=None, settings=None, assets=None, collections=None, translation=True, voice_available=True):
    parts = make_services(tmp_path, assets=assets, collections=collections, translation=translation, voice_available=voice_available)
    db,batches,items,imports,mapping,variants,asset_service,validation,service = parts
    tpl = tpl or template(placeholders=[text_ph("title", True)])
    rows = rows or [{"title":"Hello", "output_name":"hello"}]
    mappings = mappings or [BatchMapping("", "title", "column", "title", required=True), BatchMapping("", "output_name", "column", "output_name")]
    variant = variant or BatchVariantConfig("")
    batch = service.create_batch("Demo", tpl, rows, mappings, variant, tmp_path / "out", settings=settings or {"output_pattern":"{{output_name}}.mp4"})
    queue = service.prepare_items(batch.id)
    return parts,batch,queue


def test_batch_model_and_status_machine():
    b = Batch("Demo", "tpl", "/tmp/out")
    b.validate(); assert b.status_code == "draft"
    b.transition("ready"); b.transition("running"); b.transition("paused"); b.transition("running"); b.transition("completed")
    with pytest.raises(ValueError): b.transition("running")


def test_batch_item_completed_requires_reset():
    item = BatchItem("b",0,"k","v",{})
    item.set_status("completed")
    with pytest.raises(ValueError): item.set_status("rendering")
    item.set_status("output_missing"); assert item.status_code == "output_missing"


def test_batch_stages_are_explicit_and_ordered():
    assert BatchStage.VALIDATE_INPUT.value == "validate_input"
    assert BatchStage.RENDER.value == "render"
    assert BatchStage.EXPORT.value == "export"
    assert list(BatchStage)[-1] is BatchStage.FINALIZE


def test_csv_unicode_and_bom(tmp_path):
    p=tmp_path/"rows.csv"; p.write_text("\ufefftitle,language\nEnglish,en\nខ្មែរ,km\nไทย,th\nTiếng Việt,vi\n", encoding="utf-8")
    rows=BatchImportService().import_csv(p)
    assert [x.data["title"] for x in rows] == ["English","ខ្មែរ","ไทย","Tiếng Việt"]


def test_json_and_jsonl_and_manual_import(tmp_path):
    imp=BatchImportService(); p=tmp_path/"rows.json"; p.write_text(json.dumps([{"title":"ខ្មែរ"},{"title":"ไทย"}],ensure_ascii=False),encoding="utf-8")
    assert len(imp.import_json(p))==2
    q=tmp_path/"rows.jsonl"; q.write_text('{"title":"A"}\n{"title":"B"}\n',encoding="utf-8")
    assert len(imp.import_jsonl(q))==2
    assert imp.manual_rows([{"title":"Việt"}])[0].data["title"]=="Việt"


def test_json_rejects_malformed_shape_and_deep_data(tmp_path):
    imp=BatchImportService(); p=tmp_path/"bad.json"; p.write_text('{"x":1}',encoding="utf-8")
    with pytest.raises(BatchInvalidInput): imp.import_json(p)
    value={}; cursor=value
    for i in range(20): cursor["x"]={}; cursor=cursor["x"]
    p.write_text(json.dumps([value]),encoding="utf-8")
    with pytest.raises(BatchInvalidInput): imp.import_json(p)


def test_mapping_direct_constant_system_and_transforms():
    svc=BatchMappingService(); maps=[
        BatchMapping("b","title","column"," title ",transforms=[]),
        BatchMapping("b","platform","constant",value="TikTok"),
        BatchMapping("b","row","system","row_number"),
        BatchMapping("b","upper","column","name",transforms=[{"type":"trim"},{"type":"uppercase"},{"type":"prefix","value":"#"}]),
    ]
    out=svc.resolve({" title ":"Hello","name":"  Việt Nam "},maps,row_index=2,batch_name="B")
    assert out=={"title":"Hello","platform":"TikTok","row":3,"upper":"#VIỆT NAM"}


def test_mapping_rejects_unsafe_transform_and_system():
    svc=BatchMappingService()
    with pytest.raises((ValueError,BatchMappingError)): svc.resolve({},[BatchMapping("b","x","constant",value="x",transforms=[{"type":"eval"}])],row_index=0,batch_name="B")
    with pytest.raises(BatchMappingError): svc.resolve({},[BatchMapping("b","x","system","shell")],row_index=0,batch_name="B")


def test_voice_by_language_and_role_mapping():
    svc=BatchMappingService(); maps=[
        BatchMapping("b","voice","voice_language",value={"th":"thai-v","default":"en-v"}),
        BatchMapping("b","guest_voice","voice_role",source="guest",value={"guest":"guest-v","reporter":"r-v"}),
    ]
    out=svc.resolve({},maps,row_index=0,batch_name="B",context={"language":"th"})
    assert out["voice"]=="thai-v" and out["guest_voice"]=="guest-v"


def test_safe_output_path_cannot_escape_root(tmp_path):
    for value in ("../../evil", "..\\..\\evil", "/absolute/evil", "C:\\outside\\bad"):
        rel=safe_relative_output("{{output_name}}",{"output_name":value})
        target=(tmp_path/rel).resolve(); assert target==tmp_path.resolve() or tmp_path.resolve() in target.parents
        assert ".." not in Path(rel).parts


def test_unknown_mapping_target_is_invalid(tmp_path):
    parts=make_services(tmp_path); validation=parts[7]
    t=template(placeholders=[text_ph("headline",True)])
    summary=validation.dry_run(batch_name="B",template=t,rows=[{"headline":"x","mystery":"y"}],mappings=[BatchMapping("b","headline","column","headline",required=True),BatchMapping("b","not_a_placeholder","column","mystery")],variant_config=BatchVariantConfig("b"),output_root=tmp_path/"out",settings={"output_pattern":"{{row_number}}.mp4"})
    assert summary.invalid==1 and any(e["code"]=="unknown_placeholder" for e in summary.items[0].errors)


def test_required_and_optional_placeholder_validation(tmp_path):
    validation=make_services(tmp_path)[7]; t=template(placeholders=[text_ph("headline",True),text_ph("optional",False)])
    bad=validation.dry_run(batch_name="B",template=t,rows=[{"headline":""}],mappings=[BatchMapping("b","headline","column","headline",required=True)],variant_config=BatchVariantConfig("b"),output_root=tmp_path/"out1",settings={"output_pattern":"{{row_number}}.mp4"})
    assert bad.invalid==1
    good=validation.dry_run(batch_name="B",template=t,rows=[{"headline":"ok"}],mappings=[BatchMapping("b","headline","column","headline",required=True)],variant_config=BatchVariantConfig("b"),output_root=tmp_path/"out2",settings={"output_pattern":"{{row_number}}.mp4"})
    assert good.invalid==0


def test_template_language_and_aspect_compatibility(tmp_path):
    validation=make_services(tmp_path)[7]; t=template(placeholders=[text_ph("title",True)],languages=("en",),aspects=("16:9",))
    s=validation.dry_run(batch_name="B",template=t,rows=[{"title":"x"}],mappings=[BatchMapping("b","title","column","title",required=True)],variant_config=BatchVariantConfig("b",languages=["th"],aspect_ratios=["9:16"]),output_root=tmp_path/"out",settings={"output_pattern":"{{row_number}}.mp4"})
    codes={e["code"] for e in s.items[0].errors}; assert {"template_language","template_aspect"} <= codes


def test_asset_by_id_name_ambiguity_and_collection_rotation():
    a,b,c=mkasset("Same","a"),mkasset("Same","b"),mkasset("C","c")
    svc=BatchAssetService(FakeAssetRepository([a,b,c],{"col":{"a","b","c"}}))
    assert svc.by_id("a").id=="a"
    with pytest.raises(BatchMappingError): svc.by_name("Same")
    ids=[svc.choose("col",strategy="round_robin",row_index=i,item_key=f"k{i}",seed=1).id for i in range(6)]
    assert ids==["c","a","b","c","a","b"] or ids==["a","b","c","a","b","c"]  # lexical name+id ordering is deterministic
    assert ids[:3]==ids[3:]


def test_seeded_asset_random_is_reproducible():
    assets=[mkasset(chr(65+i),str(i)) for i in range(5)]; svc=BatchAssetService(FakeAssetRepository(assets,{"col":{a.id for a in assets}}))
    one=[svc.choose("col",strategy="seeded_random",row_index=i,item_key=f"row-{i}",seed=26).id for i in range(20)]
    two=[svc.choose("col",strategy="seeded_random",row_index=i,item_key=f"row-{i}",seed=26).id for i in range(20)]
    assert one==two


def test_asset_mapping_resolves_collection_in_dry_run(tmp_path):
    a,b,c=mkasset("A","a"),mkasset("B","b"),mkasset("C","c")
    validation=make_services(tmp_path,assets=[a,b,c],collections={"col":{"a","b","c"}})[7]
    t=template(placeholders=[image_ph("background",True),text_ph("title",True)])
    maps=[BatchMapping("b","title","column","title",required=True),BatchMapping("b","background","asset_collection",value={"collectionId":"col","strategy":"round_robin"},required=True)]
    s=validation.dry_run(batch_name="B",template=t,rows=[{"title":str(i)} for i in range(6)],mappings=maps,variant_config=BatchVariantConfig("b",seed=26),output_root=tmp_path/"out",settings={"output_pattern":"{{row_number}}.mp4"})
    ids=[x.resolved["background"] for x in s.items]; assert ids[:3]==ids[3:]


def test_language_variants_create_four_items():
    svc=BatchVariantService(); c=BatchVariantConfig("b",languages=["en","km","th","vi"])
    items=svc.expand([{"title":"x"}],c); assert len(items)==4 and {x["variant"]["language"] for x in items}=={"en","km","th","vi"}


def test_platform_and_combined_variant_counts():
    svc=BatchVariantService()
    assert svc.expansion_count(1,BatchVariantConfig("b",platforms=["tiktok","youtube_shorts","facebook_square"]))==3
    c=BatchVariantConfig("b",languages=["en","km","th"],platforms=["tiktok","youtube_shorts"])
    assert svc.expansion_count(2,c)==12 and len(svc.expand([{"x":1},{"x":2}],c))==12


def test_deterministic_item_keys():
    svc=BatchVariantService(); c=BatchVariantConfig("b",languages=["th"],platforms=["tiktok"])
    assert svc.expand([{"x":1}],c)[0]["itemKey"]==svc.expand([{"x":999}],c)[0]["itemKey"]


def test_reviewed_translation_requires_content(tmp_path):
    validation=make_services(tmp_path)[7]; t=template(placeholders=[text_ph("script",True)])
    maps=[BatchMapping("b","script","column","script",required=True),BatchMapping("b","translation_reviewed","column","translation_reviewed")]
    c=BatchVariantConfig("b",languages=["th"],source_language="en")
    s=validation.dry_run(batch_name="B",template=t,rows=[{"script":"source","translation_reviewed":True}],mappings=maps,variant_config=c,output_root=tmp_path/"out",settings={"output_pattern":"{{row_number}}.mp4","translation_policy":"reviewed_only"})
    assert any(e["code"]=="translation_review_required" for e in s.items[0].errors)


def test_machine_translation_capability_checked(tmp_path):
    validation=make_services(tmp_path,translation=False)[7]; t=template(placeholders=[text_ph("script",True)])
    s=validation.dry_run(batch_name="B",template=t,rows=[{"script":"source"}],mappings=[BatchMapping("b","script","column","script",required=True)],variant_config=BatchVariantConfig("b",languages=["th"],source_language="en"),output_root=tmp_path/"out",settings={"output_pattern":"{{row_number}}.mp4","translation_policy":"allow_machine_translation"})
    assert any(e["code"]=="translation_unsupported" for e in s.items[0].errors)


def test_tts_voice_validation_for_generic_batch(tmp_path):
    validation=make_services(tmp_path,voice_available=False)[7]; t=template(placeholders=[text_ph("script",True)])
    maps=[BatchMapping("b","script","column","script",required=True),BatchMapping("b","voice","constant",value="v1")]
    s=validation.dry_run(batch_name="B",template=t,rows=[{"script":"hello"}],mappings=maps,variant_config=BatchVariantConfig("b",languages=["en"]),output_root=tmp_path/"out",settings={"output_pattern":"{{row_number}}.mp4","enable_tts":True})
    assert any(e["code"]=="missing_voice" for e in s.items[0].errors)


def test_news_topic_only_is_blocked(tmp_path):
    validation=make_services(tmp_path)[7]; t=template(workflow="news",placeholders=[text_ph("title",False)])
    s=validation.dry_run(batch_name="News",template=t,rows=[{"topic":"Company X"}],mappings=[],variant_config=BatchVariantConfig("b"),output_root=tmp_path/"out",settings={"output_pattern":"{{row_number}}.mp4"})
    assert any(e["code"]=="news_grounding_required" for e in s.items[0].errors)


def test_news_grounded_script_allowed(tmp_path):
    validation=make_services(tmp_path)[7]; t=template(workflow="news",placeholders=[text_ph("script",True)])
    s=validation.dry_run(batch_name="News",template=t,rows=[{"script":"Approved supplied text"}],mappings=[BatchMapping("b","script","column","script",required=True)],variant_config=BatchVariantConfig("b"),output_root=tmp_path/"out",settings={"output_pattern":"{{row_number}}.mp4"})
    assert s.invalid==0


def test_batch_creation_snapshots_template_and_input(tmp_path):
    parts,batch,_=create_ready_batch(tmp_path)
    stored=parts[1].get(batch.id); assert stored.template_snapshot["version"]=="1.0" and stored.input_snapshot[0]["title"]=="Hello"
    # Later external template changes cannot mutate the persisted snapshot.
    assert stored.template_snapshot["name"]=="Batch Template"


def test_batch_prepare_is_idempotent_and_restart_persistent(tmp_path):
    parts,batch,queue=create_ready_batch(tmp_path); items=parts[2]
    first=[x.id for x in queue]; second=[x.id for x in parts[-1].prepare_items(batch.id)]
    assert first==second
    _,b2,i2=make_db(tmp_path)  # reopen same SQLite path
    assert b2.get(batch.id) is not None and len(i2.list_for_batch(batch.id))==1


def test_checkpointing_and_stage_resume_skips_completed(tmp_path):
    parts,batch,queue=create_ready_batch(tmp_path); batches,items=parts[1],parts[2]
    calls=[]; ex=BatchExecutionService(batches,items)
    for stage in BatchStage: ex.register_handler(stage,lambda b,i,cancellation=None,progress=None,s=stage: calls.append(s.value) or {})
    worker=BatchWorker(ex,batches,items) if False else BatchWorker(ex,items)
    item=queue[0]; worker.run_item(batch,item,max_stages=4)
    assert len([s for s in items.stage_states(item.id) if s.status_code=="completed"])==4
    worker.run_item(batch,items.get(item.id),max_stages=1)
    assert len(calls)==5


def test_pause_recovery_resume_no_duplicate_completed_stages(tmp_path):
    parts,batch,queue=create_ready_batch(tmp_path); batches,items,service=parts[1],parts[2],parts[-1]
    ex=BatchExecutionService(batches,items); calls={s.value:0 for s in BatchStage}
    for stage in BatchStage:
        def handler(b,i,cancellation=None,progress=None,s=stage): calls[s.value]+=1; return {"project_id":"project-1"} if s is BatchStage.CREATE_PROJECT else {}
        ex.register_handler(stage,handler)
    worker=BatchWorker(ex,items)
    worker.run_item(batch,queue[0],max_stages=5)
    b=batches.get(batch.id); b.status="running"; batches.save(b)
    item=items.get(queue[0].id); item.status="rendering"; item.current_stage=BatchStage.RENDER.value; items.save(item)
    rec=BatchRecoveryService(batches,items); result=rec.recover_startup(); assert result["interruptedItems"]==1 and batches.get(batch.id).status_code=="paused"
    service.retry_item(item.id); service.resume(batch.id)
    before=dict(calls); worker.run_item(batches.get(batch.id),items.get(item.id))
    for stage in list(BatchStage)[:5]: assert calls[stage.value]==before[stage.value]
    assert items.get(item.id).status_code=="completed"


def test_failed_render_retry_does_not_rerun_tts(tmp_path):
    settings={"output_pattern":"{{output_name}}.mp4","enable_tts":True}
    parts,batch,queue=create_ready_batch(tmp_path,mappings=[BatchMapping("","title","column","title",required=True),BatchMapping("","output_name","column","output_name"),BatchMapping("","voice","constant",value="v")],settings=settings)
    batches,items,service=parts[1],parts[2],parts[-1]; ex=BatchExecutionService(batches,items); calls={}
    for stage in BatchStage:
        def handler(b,i,cancellation=None,progress=None,s=stage):
            calls[s.value]=calls.get(s.value,0)+1
            if s is BatchStage.RENDER and calls[s.value]==1: raise RuntimeError("render failed")
            return {}
        ex.register_handler(stage,handler)
    worker=BatchWorker(ex,items)
    item=queue[0]
    with pytest.raises(RuntimeError): worker.run_item(batch,item)
    tts_calls=calls.get(BatchStage.GENERATE_TTS.value,0); assert tts_calls==1
    service.retry_item(item.id); worker.run_item(batches.get(batch.id),items.get(item.id))
    assert calls[BatchStage.GENERATE_TTS.value]==tts_calls and calls[BatchStage.RENDER.value]==2


def test_stage_invalidation_voice_starts_at_tts(tmp_path):
    parts,batch,queue=create_ready_batch(tmp_path); items,service=parts[2],parts[-1]; item=queue[0]
    for stage in BatchStage:
        items.checkpoint(item,BatchStageState(item.id,stage.value,BatchStageStatus.COMPLETED,1.0))
    service.invalidate(item.id,"voice")
    states={s.stage_code:s.status_code for s in items.stage_states(item.id)}
    assert states[BatchStage.TRANSLATE.value]=="completed" and states[BatchStage.GENERATE_TTS.value]=="invalidated" and states[BatchStage.RENDER.value]=="invalidated"


def test_retry_completed_with_errors_resets_batch_ready(tmp_path):
    parts,batch,queue=create_ready_batch(tmp_path); batches,items,service=parts[1],parts[2],parts[-1]; item=queue[0]
    item.status="failed";items.save(item);b=batches.get(batch.id);b.status="completed_with_errors";batches.save(b)
    service.retry_item(item.id)
    assert batches.get(batch.id).status_code=="ready" and items.get(item.id).status_code=="pending"


def test_scheduler_completes_mock_batch_and_lock_prevents_duplicate_owner(tmp_path):
    parts,batch,queue=create_ready_batch(tmp_path); batches,items,service=parts[1],parts[2],parts[-1]; ex=BatchExecutionService(batches,items)
    for stage in BatchStage: ex.register_handler(stage,lambda *a,**k:{})
    worker=BatchWorker(ex,items); pool=WorkerPool(max_workers=2); sched=BatchScheduler(service,batches,items,worker,pool)
    try:
        sched.run_until_idle(batch.id)
        assert items.get(queue[0].id).status_code=="completed"
        assert batches.get(batch.id).status_code=="completed"
        assert batches.acquire_lock(batch.id,"other") is True
        assert batches.acquire_lock(batch.id,"another") is False
        batches.release_lock(batch.id,"other")
    finally: pool.shutdown()


def test_cancel_pending_preserves_completed(tmp_path):
    rows=[{"title":str(i),"output_name":str(i)} for i in range(3)]
    parts,batch,queue=create_ready_batch(tmp_path,rows=rows); items,service=parts[2],parts[-1]
    queue[0].status="completed"; queue[0].output_path=str(tmp_path/"done.mp4"); items.save(queue[0])
    service.cancel_pending(batch.id)
    assert items.get(queue[0].id).status_code=="completed"
    assert all(items.get(x.id).status_code=="cancelled" for x in queue[1:])


def test_low_disk_pauses_before_new_work(tmp_path, monkeypatch):
    parts,batch,queue=create_ready_batch(tmp_path,settings={"output_pattern":"{{output_name}}.mp4","disk_reserve_bytes":10**18}); batches,items,service=parts[1],parts[2],parts[-1]
    ex=BatchExecutionService(batches,items); worker=BatchWorker(ex,items); pool=WorkerPool(max_workers=1); sched=BatchScheduler(service,batches,items,worker,pool)
    try:sched.run_until_idle(batch.id,max_cycles=2); assert batches.get(batch.id).status_code=="paused" and batches.pause_reason(batch.id)=="low_disk_space"
    finally:pool.shutdown()


def test_recovery_marks_missing_completed_output(tmp_path):
    parts,batch,queue=create_ready_batch(tmp_path); batches,items=parts[1],parts[2]; item=queue[0]; item.status="completed";item.output_path=str(tmp_path/"missing.mp4");items.save(item)
    out=BatchRecoveryService(batches,items).recover_startup(); assert out["missingOutputs"]==1 and items.get(item.id).status_code=="output_missing"


def test_batch_history_duplicate_and_delete_record_safe(tmp_path):
    parts,batch,queue=create_ready_batch(tmp_path); batches,items,service=parts[1],parts[2],parts[-1]
    clone=service.duplicate_batch(batch.id); assert clone.id!=batch.id and clone.template_snapshot==batch.template_snapshot and items.count(clone.id)==0
    assert any(x["id"]==batch.id for x in service.history())
    output=tmp_path/"external.mp4";output.write_bytes(b"safe")
    queue[0].output_path=str(output);items.save(queue[0]);service.delete_batch(batch.id)
    assert output.exists() and batches.get(batch.id) is None


def test_results_csv_preserves_unicode(tmp_path):
    parts,batch,queue=create_ready_batch(tmp_path,rows=[{"title":"ខ្មែរ","output_name":"វីដេអូ"}]); service=parts[-1]
    path=service.export_results_csv(batch.id,tmp_path/"results.csv"); text=path.read_text(encoding="utf-8-sig");assert queue[0].item_key in text


def test_template_snapshot_survives_installed_template_version_change(tmp_path):
    parts,batch,queue=create_ready_batch(tmp_path,tpl=template(version="1.0")); batches=parts[1]
    installed=template(version="2.0")
    stored=batches.get(batch.id); assert stored.template_snapshot["version"]=="1.0" and installed.version=="2.0"


def test_khmer_thai_vietnamese_batch_unicode(tmp_path):
    rows=[{"title":"ព័ត៌មានខ្មែរ","output_name":"ខ្មែរ"},{"title":"ข่าวไทย","output_name":"ไทย"},{"title":"Tin Việt Nam","output_name":"Tiếng Việt"}]
    parts,batch,queue=create_ready_batch(tmp_path,rows=rows,variant=BatchVariantConfig(""),tpl=template(placeholders=[text_ph("title",True)]))
    assert [x.input_data["title"] for x in queue]==[r["title"] for r in rows]
    assert all(".." not in x.resolved_data["output_relative"] for x in queue)


def test_large_1000_item_queue_search_and_persistence(tmp_path):
    rows=[{"title":f"Item {i}","output_name":f"video-{i}"} for i in range(1000)]
    parts,batch,queue=create_ready_batch(tmp_path,rows=rows); items=parts[2]
    assert len(queue)==1000 and items.count(batch.id)==1000
    found=items.list_for_batch(batch.id,search="Item 999",limit=20); assert len(found)==1 and found[0].resolved_data["title"]=="Item 999"
    page=items.list_for_batch(batch.id,limit=50,offset=950); assert len(page)==50


def test_no_ai_normal_video_batch_can_complete_with_injected_existing_handlers(tmp_path):
    rows=[{"title":f"Card {i}","output_name":f"card-{i}"} for i in range(10)]
    parts,batch,queue=create_ready_batch(tmp_path,rows=rows,settings={"output_pattern":"{{output_name}}.mp4","stage_requirements":{"translate":False,"generate_tts":False,"generate_subtitles":False}})
    batches,items,service=parts[1],parts[2],parts[-1]; ex=BatchExecutionService(batches,items)
    def create(b,i,**k):return {"project_id":f"project-{i.row_index}"}
    def render(b,i,**k):
        path=Path(b.output_directory)/i.resolved_data["output_relative"];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b"tiny-video");return {"output_path":str(path)}
    ex.register_handler(BatchStage.CREATE_PROJECT,create);ex.register_handler(BatchStage.RENDER,render);ex.register_handler(BatchStage.EXPORT,lambda b,i,**k:{"output_reference":i.output_path})
    worker=BatchWorker(ex,items);pool=WorkerPool(max_workers=2);sched=BatchScheduler(service,batches,items,worker,pool)
    try:sched.run_until_idle(batch.id); assert all(items.get(x.id).status_code=="completed" for x in queue); assert len(list((tmp_path/"out").glob("*.mp4")))==10
    finally:pool.shutdown()


def test_reporter_and_multi_speaker_data_survive_resolution(tmp_path):
    rows=[{"headline":"A","reporter_text":"Hello","guest_text":"Hi","reporter_voice":"rv","guest_voice":"gv","output_name":"x"}]
    t=template(workflow="news",placeholders=[text_ph("headline",True),text_ph("script",False)])
    maps=[BatchMapping("","headline","column","headline",required=True),BatchMapping("","reporter_text","column","reporter_text"),BatchMapping("","guest_text","column","guest_text"),BatchMapping("","reporter_voice","column","reporter_voice"),BatchMapping("","guest_voice","column","guest_voice"),BatchMapping("","output_name","column","output_name"),BatchMapping("","source_attribution","constant",value="User supplied")]
    parts=make_services(tmp_path); service=parts[-1]; batch=service.create_batch("Reporter",t,rows,maps,BatchVariantConfig(""),tmp_path/"out",settings={"output_pattern":"{{output_name}}.mp4"}); q=service.prepare_items(batch.id)
    assert q[0].resolved_data["reporter_voice"]=="rv" and q[0].resolved_data["guest_voice"]=="gv" and q[0].resolved_data["reporter_text"]=="Hello"


def test_dry_run_summary_reports_invalid_missing_asset_voice_and_collision(tmp_path):
    missing_voice_validation=make_services(tmp_path,voice_available=False)[7]
    t=template(placeholders=[text_ph("title",True),image_ph("background",True),voice_ph()])
    maps=[BatchMapping("b","title","column","title",required=True),BatchMapping("b","background","asset_fixed",value="missing",required=True),BatchMapping("b","voice","constant",value="bad",required=True),BatchMapping("b","output_name","constant",value="same")]
    s=missing_voice_validation.dry_run(batch_name="B",template=t,rows=[{"title":"A"},{"title":"B"}],mappings=maps,variant_config=BatchVariantConfig("b"),output_root=tmp_path/"out",settings={"output_pattern":"{{output_name}}.mp4","enable_tts":True,"collision_policy":"fail"})
    codes={e["code"] for x in s.items for e in x.errors}; assert "missing_asset" in codes and "missing_voice" in codes and "output_collision" in codes

def test_real_ffmpeg_three_item_batch_smoke_reuses_existing_compositor(tmp_path):
    import subprocess
    from rendering.layer_compositor import build_layered_scene_command
    source=tmp_path/"source.mp4"
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","lavfi","-i","testsrc2=s=320x180:r=24:d=0.4","-an","-c:v","libx264","-pix_fmt","yuv420p",str(source)],check=True)
    class Caps: filters={"scale","crop","pad","overlay","chromakey","colorkey","format","fps","trim","setpts"}
    class Runner:
        def discover_capabilities(self): return Caps()
    class Overlay:
        def write_ass(self,*args,**kwargs): return None
    class Renderer:
        runner=Runner(); overlay_renderer=Overlay(); fonts_dir=None
    class Settings: width=160; height=90; fps=24

    rows=[{"title":f"Real {i}","output_name":f"real-{i}"} for i in range(3)]
    parts,batch,queue=create_ready_batch(tmp_path,rows=rows,settings={"output_pattern":"{{output_name}}.mp4","stage_requirements":{"translate":False,"generate_tts":False,"generate_subtitles":False}})
    batches,items,service=parts[1],parts[2],parts[-1]; ex=BatchExecutionService(batches,items)
    ex.register_handler(BatchStage.CREATE_PROJECT,lambda b,i,**k:{"project_id":f"p-{i.row_index}"})
    def render(b,i,**kwargs):
        out=Path(b.output_directory)/i.resolved_data["output_relative"]
        intermediate=tmp_path/f"{i.id}.nut"
        spec={"sceneId":i.id,"durationMs":400,"visual":{"path":str(source),"mediaType":"video","fitMode":"fill","backgroundColor":"#000000","reframe":{"scale":1.0,"fitMode":"fill"}},"audio":{},"layers":[],"overlays":[],"transitionIn":{},"transitionOut":{}}
        args=build_layered_scene_command(Renderer(),lambda *a,**k: (_ for _ in ()).throw(AssertionError("compositor expected")),spec,Settings(),intermediate,temp_dir=tmp_path)
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",*args],check=True)
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(intermediate),"-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac",str(out)],check=True)
        return {"output_path":str(out),"output_reference":str(out)}
    ex.register_handler(BatchStage.RENDER,render); ex.register_handler(BatchStage.EXPORT,lambda b,i,**k:{"output_reference":i.output_path})
    worker=BatchWorker(ex,items); pool=WorkerPool(max_workers=2); sched=BatchScheduler(service,batches,items,worker,pool)
    try:
        sched.run_until_idle(batch.id)
        outputs=sorted((tmp_path/"out").glob("*.mp4")); assert len(outputs)==3
        for path in outputs:
            probe=subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","csv=s=x:p=0",str(path)],capture_output=True,text=True,check=True)
            assert probe.stdout.strip()=="160x90"
    finally: pool.shutdown()

def test_scheduler_allows_light_parallelism_but_serializes_tts(tmp_path):
    rows=[{"title":f"Item {i}","output_name":f"i-{i}"} for i in range(4)]
    parts,batch,queue=create_ready_batch(tmp_path,rows=rows,mappings=[BatchMapping("","title","column","title",required=True),BatchMapping("","output_name","column","output_name"),BatchMapping("","voice","constant",value="v")],settings={"output_pattern":"{{output_name}}.mp4","enable_tts":True})
    batches,items,service=parts[1],parts[2],parts[-1]; ex=BatchExecutionService(batches,items)
    lock=__import__('threading').Lock(); active={"project":0,"tts":0}; maximum={"project":0,"tts":0}
    def project(b,i,**k):
        with lock: active["project"]+=1; maximum["project"]=max(maximum["project"],active["project"])
        time.sleep(.03)
        with lock: active["project"]-=1
        return {"project_id":f"p-{i.row_index}"}
    def tts(b,i,**k):
        with lock: active["tts"]+=1; maximum["tts"]=max(maximum["tts"],active["tts"])
        time.sleep(.02)
        with lock: active["tts"]-=1
        return {}
    ex.register_handler(BatchStage.CREATE_PROJECT,project); ex.register_handler(BatchStage.GENERATE_TTS,tts)
    ex.register_handler(BatchStage.RENDER,lambda b,i,**k:{"output_path":str(Path(b.output_directory)/f"{i.item_key}.mp4")})
    ex.register_handler(BatchStage.EXPORT,lambda *a,**k:{})
    worker=BatchWorker(ex,items); pool=WorkerPool(max_workers=4); sched=BatchScheduler(service,batches,items,worker,pool)
    try:
        sched.run_until_idle(batch.id)
        assert maximum["project"]>=2
        assert maximum["tts"]==1
    finally:pool.shutdown()


def test_batch_ui_extends_existing_app_without_second_renderer_or_tts_queue():
    root=Path(__file__).resolve().parents[1]
    page=(root/"ui/qml/pages/BatchPage.qml").read_text(encoding="utf-8")
    factory=(root/"ui/qml/batch/BatchFactory.qml").read_text(encoding="utf-8")
    runtime=(root/"app/phase26_runtime.py").read_text(encoding="utf-8")
    assert "BatchFactory" in page and "Template" in factory and "Dry Run" in factory
    assert "ExportService" in runtime and "MultiSpeakerTTSService" in runtime
    assert not (root/"rendering/batch_renderer.py").exists()
    assert not (root/"workers/batch_tts_queue.py").exists()


def test_keep_both_makes_intra_batch_output_names_deterministically_unique(tmp_path):
    validation=make_services(tmp_path)[7]; t=template(placeholders=[text_ph("title",True)])
    maps=[BatchMapping("b","title","column","title",required=True),BatchMapping("b","output_name","constant",value="same")]
    summary=validation.dry_run(batch_name="B",template=t,rows=[{"title":"A"},{"title":"B"},{"title":"C"}],mappings=maps,variant_config=BatchVariantConfig("b"),output_root=tmp_path/"out",settings={"output_pattern":"{{output_name}}.mp4","collision_policy":"keep_both"})
    names=[x.output_relative for x in summary.items]
    assert names==["same.mp4","same (2).mp4","same (3).mp4"]
    assert summary.invalid==0


def test_phase26_runtime_existing_service_contracts_are_wired_correctly():
    runtime = (Path(__file__).parents[1] / "app" / "phase26_runtime.py").read_text(encoding="utf-8")
    recovery = (Path(__file__).parents[1] / "services" / "batch_recovery_service.py").read_text(encoding="utf-8")
    assert "BatchRecoveryService(batch_repository, item_repository, logger=logger)" in runtime
    assert "output_validator=None,logger=None" in recovery.replace(" ", "")
    assert "BatchWorker(execution, item_repository, logger=logger)" in runtime
    assert "translate_document(item.project_id, job.id, cancellation=cancellation)" in runtime
    assert 'getattr(p, "ratio", 0.5)' in runtime
