from __future__ import annotations
import csv,hashlib,json
from pathlib import Path
from typing import Any,Mapping
from uuid import uuid4
from domain.batch import Batch,BatchStatus
from domain.batch_errors import BatchInvalidInput
from domain.batch_item import BatchItem,BatchItemStatus
from domain.batch_mapping import BatchMapping
from domain.batch_stage import BatchStage,STAGE_INDEX
from domain.batch_variant import BatchVariantConfig
from domain.project import utc_now_iso

class BatchService:
    def __init__(self,batches,items,imports,mapping,variants,validation,*,project_service=None,logger=None):
        self.batches=batches;self.items=items;self.imports=imports;self.mapping=mapping;self.variants=variants;self.validation=validation;self.project_service=project_service;self.logger=logger
    def create_batch(self,name:str,template,rows:list[Mapping[str,Any]],mappings:list[BatchMapping],variant:BatchVariantConfig,output_directory:str|Path,*,input_source_type:str='manual',input_source_path:str='',settings:Mapping[str,Any]|None=None)->Batch:
        snapshot=template.to_dict() if hasattr(template,'to_dict') else dict(template)
        normalized=[dict(row) for row in rows]
        batch=Batch(name=name.strip(),template_id=str(getattr(template,'id',snapshot.get('id',''))),output_directory=str(Path(output_directory).expanduser().resolve()),input_source_type=input_source_type,input_source_path=input_source_path,settings=dict(settings or {}),template_snapshot=snapshot,input_snapshot=normalized,metadata={'inputSnapshotVersion':1,'templateVersion':str(snapshot.get('version') or '1.0')})
        variant.batch_id=batch.id
        for m in mappings:m.batch_id=batch.id
        batch.validate()
        if hasattr(self.batches,'create_definition'):
            self.batches.create_definition(batch,mappings,variant)
        else:
            self.batches.create(batch)
            try:self.batches.save_mappings(batch.id,mappings);self.batches.save_variant(variant)
            except Exception:self.batches.delete(batch.id);raise
        return batch
    def dry_run(self,batch_id:str,template=None):
        batch=self.require(batch_id);template=template or self._template_from_snapshot(batch.template_snapshot);variant=self.batches.variant(batch_id) or BatchVariantConfig(batch_id);return self.validation.dry_run(batch_name=batch.name,template=template,rows=batch.input_snapshot,mappings=self.batches.mappings(batch_id),variant_config=variant,output_root=batch.output_directory,settings=batch.settings)
    def prepare_items(self,batch_id:str,template=None,*,skip_invalid:bool=False,confirm_large:bool=False)->list[BatchItem]:
        batch=self.require(batch_id)
        if self.items.count(batch_id):return self.items.list_for_batch(batch_id)
        summary=self.dry_run(batch_id,template)
        if summary.invalid and not skip_invalid:raise BatchInvalidInput(f'{summary.invalid} Batch items are invalid. Fix or explicitly skip them.')
        preview=(self.batches.variant(batch_id) or BatchVariantConfig(batch_id)).to_dict();count=summary.total
        if count>=self.variants.CONFIRM_THRESHOLD and not confirm_large:raise BatchInvalidInput(f'This Batch will create {count} outputs. Explicit confirmation is required.')
        variant=self.batches.variant(batch_id) or BatchVariantConfig(batch_id);expanded=self.variants.expand(batch.input_snapshot,variant);dry_by_key={x.item_key:x for x in summary.items};created=[]
        for entry in expanded:
            dry=dry_by_key[entry['itemKey']];resolved=dict(dry.resolved);resolved['output_relative']=dry.output_relative
            fingerprint=self.item_fingerprint(entry['input'],batch.template_snapshot,entry['variant'],resolved)
            status=BatchItemStatus.SKIPPED.value if dry.validity=='invalid' and skip_invalid else BatchItemStatus.PENDING.value
            item=BatchItem(batch.id,entry['rowIndex'],entry['itemKey'],entry['variantKey'],dict(entry['input']),status=status,resolved_data=resolved,fingerprint=fingerprint,metadata={'dryRunValidity':dry.validity,'dryRunWarnings':dry.warnings,'dryRunErrors':dry.errors,'templateVersion':batch.metadata.get('templateVersion','1.0'),'variant':entry['variant']})
            created.append(item)
        self.items.create_many(created);batch.total_items=len(created);batch.status=BatchStatus.READY.value;self.refresh_counts(batch.id);self.batches.save(batch);return created
    def refresh_counts(self,batch_id:str)->Batch:
        b=self.require(batch_id);items=self.items.list_for_batch(batch_id);b.total_items=len(items);b.completed_items=sum(x.status_code==BatchItemStatus.COMPLETED.value for x in items);b.failed_items=sum(x.status_code in {BatchItemStatus.FAILED.value,BatchItemStatus.INTERRUPTED.value,BatchItemStatus.OUTPUT_MISSING.value} for x in items);b.cancelled_items=sum(x.status_code==BatchItemStatus.CANCELLED.value for x in items);self.batches.save(b);return b
    def pause(self,batch_id:str,reason:str='User requested pause')->Batch:
        b=self.require(batch_id)
        if b.status_code==BatchStatus.RUNNING.value:b.transition(BatchStatus.PAUSED);self.batches.set_pause_reason(batch_id,reason);self.batches.save(b)
        return b
    def resume(self,batch_id:str)->Batch:
        b=self.require(batch_id)
        if b.status_code in {BatchStatus.PAUSED.value,BatchStatus.READY.value}:b.transition(BatchStatus.RUNNING);self.batches.set_pause_reason(batch_id,'');self.batches.save(b)
        return b
    def cancel_pending(self,batch_id:str)->int:
        changed=0
        for item in self.items.list_for_batch(batch_id):
            if item.status_code in {BatchItemStatus.PENDING.value,BatchItemStatus.PAUSED.value,BatchItemStatus.NEEDS_REVIEW.value,BatchItemStatus.INTERRUPTED.value}:
                item.status=BatchItemStatus.CANCELLED.value;item.completed_at=utc_now_iso();self.items.save(item);changed+=1
        b=self.require(batch_id)
        if b.status_code not in {BatchStatus.COMPLETED.value,BatchStatus.COMPLETED_WITH_ERRORS.value}:b.status=BatchStatus.CANCELLED.value;b.completed_at=utc_now_iso();self.batches.save(b)
        self.refresh_counts(batch_id);return changed
    def cancel_item(self,item_id:str)->BatchItem:
        item=self.require_item(item_id)
        if item.status_code!=BatchItemStatus.COMPLETED.value:item.status=BatchItemStatus.CANCELLED.value;item.completed_at=utc_now_iso();self.items.save(item);self.refresh_counts(item.batch_id)
        return item
    def skip_item(self,item_id:str)->BatchItem:
        item=self.require_item(item_id)
        if item.status_code not in {BatchItemStatus.COMPLETED.value,BatchItemStatus.CANCELLED.value}:item.status=BatchItemStatus.SKIPPED.value;item.completed_at=utc_now_iso();self.items.save(item);self.refresh_counts(item.batch_id)
        return item
    def retry_item(self,item_id:str)->BatchItem:
        item=self.require_item(item_id)
        if item.status_code not in {BatchItemStatus.FAILED.value,BatchItemStatus.INTERRUPTED.value,BatchItemStatus.OUTPUT_MISSING.value,BatchItemStatus.NEEDS_REVIEW.value}:return item
        item.status=BatchItemStatus.PENDING.value;item.error_code='';item.error_message='';item.completed_at='';item.attempt_count+=1;self.items.save(item)
        batch=self.require(item.batch_id)
        if batch.status_code in {BatchStatus.COMPLETED_WITH_ERRORS.value,BatchStatus.FAILED.value,BatchStatus.CANCELLED.value}:
            batch.transition(BatchStatus.READY,force_reset=True);batch.completed_at='';self.batches.save(batch)
        return item
    def retry_all_failed(self,batch_id:str)->int:
        count=0
        for item in self.items.list_for_batch(batch_id):
            before=item.status_code;self.retry_item(item.id)
            if before!=item.status_code:count+=1
        return count
    def invalidate(self,item_id:str,change_type:str)->int:
        starts={'voice':BatchStage.GENERATE_TTS.value,'language':BatchStage.TRANSLATE.value,'asset':BatchStage.PREPARE_SCENES.value,'template':BatchStage.RESOLVE_TEMPLATE.value,'script':BatchStage.PREPARE_SCRIPT.value,'subtitle':BatchStage.GENERATE_SUBTITLES.value,'render':BatchStage.RENDER.value}
        if change_type not in starts:raise ValueError('Unknown Batch invalidation type.')
        return self.items.invalidate_from(item_id,starts[change_type])
    def reset_to_stage(self,item_id:str,stage:str)->int:
        if stage not in STAGE_INDEX:raise ValueError('Unknown Batch stage.')
        return self.items.invalidate_from(item_id,stage)
    def mark_manually_modified(self,item_id:str,value:bool=True)->BatchItem:
        item=self.require_item(item_id);item.metadata['manuallyModified']=bool(value);self.items.save(item);return item
    def duplicate_batch(self,batch_id:str,*,reuse_input:bool=True)->Batch:
        source=self.require(batch_id);clone=Batch(name=f'{source.name} Copy',template_id=source.template_id,output_directory=source.output_directory,input_source_type=source.input_source_type,input_source_path=source.input_source_path,settings=dict(source.settings),template_snapshot=json.loads(json.dumps(source.template_snapshot,ensure_ascii=False)),input_snapshot=(json.loads(json.dumps(source.input_snapshot,ensure_ascii=False)) if reuse_input else []),metadata={k:v for k,v in source.metadata.items() if k not in {'completedAt','scheduler'}})
        self.batches.create(clone);maps=[]
        for m in self.batches.mappings(source.id):maps.append(BatchMapping(clone.id,m.target,m.kind_code,m.source,m.value,m.required,m.default_value,list(m.transforms),dict(m.metadata)))
        self.batches.save_mappings(clone.id,maps);v=self.batches.variant(source.id)
        if v:self.batches.save_variant(BatchVariantConfig(clone.id,list(v.languages),list(v.voices),list(v.platforms),list(v.aspect_ratios),list(v.template_options),v.source_language,v.seed,dict(v.metadata)))
        return clone
    def delete_batch(self,batch_id:str,*,delete_generated_projects:bool=False)->None:
        if delete_generated_projects:
            if self.project_service is None:raise RuntimeError('Project deletion service is unavailable.')
            for item in self.items.list_for_batch(batch_id):
                if item.project_id:
                    try:self.project_service.delete_project(item.project_id)
                    except Exception:pass
        self.batches.delete(batch_id)
    def export_results_csv(self,batch_id:str,path:str|Path)->Path:
        p=Path(path).expanduser();p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=['item_key','status','output_path','error']);w.writeheader()
            for item in self.items.list_for_batch(batch_id):w.writerow({'item_key':item.item_key,'status':item.status_code,'output_path':item.output_path,'error':item.error_message})
        return p
    def history(self):return [b.to_dict() for b in self.batches.list_all()]
    def require(self,batch_id):
        b=self.batches.get(batch_id)
        if b is None:raise KeyError('Batch not found.')
        return b
    def require_item(self,item_id):
        i=self.items.get(item_id)
        if i is None:raise KeyError('Batch item not found.')
        return i
    @staticmethod
    def item_fingerprint(input_data,template_snapshot,variant,resolved):
        payload={'input':input_data,'templateId':template_snapshot.get('id'),'templateVersion':template_snapshot.get('version'),'variant':variant,'assets':{k:v for k,v in resolved.items() if 'asset' in k.lower()},'language':resolved.get('language'),'voice':resolved.get('voice')};return hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()
    @staticmethod
    def _template_from_snapshot(snapshot):
        from domain.template import Template
        return Template.from_dict(snapshot,builtin=bool(snapshot.get('builtin',False)))
