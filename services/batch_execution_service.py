from __future__ import annotations
import hashlib,json
from dataclasses import dataclass
from typing import Any,Callable
from domain.batch_errors import BatchCancelled,BatchItemFailed
from domain.batch_item import BatchItemStatus
from domain.batch_stage import BatchStage,BatchStageState,BatchStageStatus,STAGE_ORDER,STAGE_INDEX,STAGE_WEIGHTS
from domain.project import utc_now_iso

StageHandler=Callable[...,dict[str,Any]|None]

@dataclass(slots=True)
class StageExecution:
    stage:str; status:str; progress:float; skipped:bool=False; output_reference:str=''

class BatchExecutionService:
    """Checkpointed orchestrator. Existing Template/TTS/Subtitle/Render/Export services are injected as handlers."""
    OPTIONAL={BatchStage.TRANSLATE.value,BatchStage.GENERATE_TTS.value,BatchStage.GENERATE_SUBTITLES.value,BatchStage.RESOLVE_SPEAKERS.value,BatchStage.PREPARE_SCRIPT.value}
    CORE_NOOP={BatchStage.VALIDATE_INPUT.value,BatchStage.RESOLVE_TEMPLATE.value,BatchStage.RESOLVE_LANGUAGE.value,BatchStage.RESOLVE_ASSETS.value,BatchStage.PREPARE_SCENES.value,BatchStage.FINALIZE.value}
    def __init__(self,batches,items,*,handlers:dict[str,StageHandler]|None=None,logger=None):self.batches=batches;self.items=items;self.handlers=dict(handlers or {});self.logger=logger
    def register_handler(self,stage:str|BatchStage,handler:StageHandler)->None:self.handlers[stage.value if isinstance(stage,BatchStage) else str(stage)]=handler
    def next_stage(self,item,batch)->str|None:
        for stage in STAGE_ORDER:
            state=self.items.stage_state(item.id,stage.value)
            if state and state.status_code in {BatchStageStatus.COMPLETED.value,BatchStageStatus.SKIPPED.value}:continue
            if not self.stage_required(stage.value,item,batch):
                skip=BatchStageState(item.id,stage.value,BatchStageStatus.SKIPPED,1.0,completed_at=utc_now_iso(),fingerprint=self.stage_fingerprint(stage.value,item,batch));self.items.checkpoint(item,skip);continue
            return stage.value
        return None
    def stage_required(self,stage:str,item,batch)->bool:
        req=batch.settings.get('stage_requirements') if isinstance(batch.settings,dict) else None
        if isinstance(req,dict) and stage in req:return bool(req[stage])
        if stage==BatchStage.TRANSLATE.value:return str(item.resolved_data.get('source_language') or '') not in {'',str(item.resolved_data.get('language') or '')} and str(batch.settings.get('translation_policy') or 'reviewed_only')!='skip_translation'
        if stage==BatchStage.GENERATE_TTS.value:return bool(batch.settings.get('enable_tts') or item.resolved_data.get('voice') or item.resolved_data.get('voice_id'))
        if stage==BatchStage.GENERATE_SUBTITLES.value:return bool(batch.settings.get('generate_subtitles') or batch.template_snapshot.get('metadata',{}).get('subtitlePresetId'))
        if stage==BatchStage.RESOLVE_SPEAKERS.value:return any(p.get('type') in {'speaker','voice'} for p in batch.template_snapshot.get('placeholders',[]))
        if stage==BatchStage.PREPARE_SCRIPT.value:return any(item.resolved_data.get(k) for k in ('script','body','text','reporter_text','guest_text'))
        return True
    def execute_next(self,item,batch,*,cancellation=None,progress_callback=None)->StageExecution|None:
        stage=self.next_stage(item,batch)
        if stage is None:return None
        if cancellation is not None and cancellation.is_cancelled:raise BatchCancelled()
        fingerprint=self.stage_fingerprint(stage,item,batch);existing=self.items.stage_state(item.id,stage)
        if existing and existing.status_code==BatchStageStatus.COMPLETED.value and existing.fingerprint==fingerprint:return StageExecution(stage,'completed',1.0,True,existing.output_reference)
        state=existing or BatchStageState(item.id,stage);state.status=BatchStageStatus.RUNNING;state.started_at=state.started_at or utc_now_iso();state.progress=max(0,float(state.progress));state.attempt_count+=1;state.fingerprint=fingerprint
        item.current_stage=stage;item.status=self._item_status(stage);item.progress=self.overall_progress(item.id,active_stage=stage,active_progress=state.progress);item.error_code='';item.error_message='';self.items.checkpoint(item,state)
        def progress(value:float,message:str=''):
            state.progress=max(0,min(1,float(value)));state.metadata['message']=str(message or '');item.progress=self.overall_progress(item.id,active_stage=stage,active_progress=state.progress);self.items.checkpoint(item,state)
            if progress_callback:progress_callback(item,stage,state.progress,message)
        try:
            handler=self.handlers.get(stage)
            if handler is None:
                if stage in self.CORE_NOOP or stage in self.OPTIONAL:result={}
                else:raise BatchItemFailed(f'No existing-system handler is configured for required Batch stage: {stage}')
            else:result=handler(batch,item,cancellation=cancellation,progress=progress) or {}
            if cancellation is not None and cancellation.is_cancelled:raise BatchCancelled()
            if isinstance(result.get('resolved'),dict):item.resolved_data.update(result['resolved'])
            if result.get('project_id'):item.project_id=str(result['project_id'])
            if result.get('output_path'):item.output_path=str(result['output_path'])
            if isinstance(result.get('metadata'),dict):item.metadata.update(result['metadata'])
            state.status=BatchStageStatus.COMPLETED;state.progress=1.0;state.completed_at=utc_now_iso();state.output_reference=str(result.get('output_reference') or item.output_path or item.project_id or '')
            item.progress=self.overall_progress(item.id,active_stage=stage,active_progress=1.0);self.items.checkpoint(item,state)
            return StageExecution(stage,'completed',1.0,False,state.output_reference)
        except BatchCancelled:
            state.status=BatchStageStatus.CANCELLED;state.error_code='cancelled';state.error_message='Stage cancelled.';item.status=BatchItemStatus.CANCELLED.value;item.error_code='cancelled';item.error_message='Batch item cancelled.';self.items.checkpoint(item,state);raise
        except Exception as exc:
            state.status=BatchStageStatus.FAILED;state.error_code=exc.__class__.__name__;state.error_message=str(exc)[-2000:];item.status=BatchItemStatus.FAILED.value;item.error_code=state.error_code;item.error_message=state.error_message;item.attempt_count+=1;self.items.checkpoint(item,state);raise
    def finalize_if_done(self,item,batch)->bool:
        if self.next_stage(item,batch) is not None:return False
        item.status=BatchItemStatus.COMPLETED.value;item.progress=1.0;item.completed_at=utc_now_iso();self.items.save(item);return True
    def stage_fingerprint(self,stage,item,batch)->str:
        relevant={'itemFingerprint':item.fingerprint,'stage':stage,'templateVersion':batch.metadata.get('templateVersion') or batch.template_snapshot.get('version'),'projectId':item.project_id}
        if STAGE_INDEX[stage]>=STAGE_INDEX[BatchStage.TRANSLATE.value]:relevant['language']=item.resolved_data.get('language');relevant['sourceLanguage']=item.resolved_data.get('source_language')
        if STAGE_INDEX[stage]>=STAGE_INDEX[BatchStage.GENERATE_TTS.value]:relevant['voice']=item.resolved_data.get('voice') or item.resolved_data.get('voice_id')
        if STAGE_INDEX[stage]>=STAGE_INDEX[BatchStage.PREPARE_SCENES.value]:relevant['assets']={k:v for k,v in item.resolved_data.items() if 'asset' in k.casefold() or 'background' in k.casefold() or 'broll' in k.casefold()}
        return hashlib.sha256(json.dumps(relevant,ensure_ascii=False,sort_keys=True,separators=(',',':'),default=str).encode('utf-8')).hexdigest()
    def overall_progress(self,item_id:str,*,active_stage:str='',active_progress:float=0.0)->float:
        states={s.stage_code:s for s in self.items.stage_states(item_id)};total=0.0
        for stage,weight in STAGE_WEIGHTS.items():
            state=states.get(stage)
            if stage==active_stage:total+=weight*max(0,min(1,active_progress))
            elif state and state.status_code in {BatchStageStatus.COMPLETED.value,BatchStageStatus.SKIPPED.value}:total+=weight
            elif state:total+=weight*max(0,min(1,state.progress))
        return min(1.0,total)
    @staticmethod
    def _item_status(stage:str)->str:
        return {BatchStage.VALIDATE_INPUT.value:BatchItemStatus.VALIDATING.value,BatchStage.CREATE_PROJECT.value:BatchItemStatus.PROJECT_SETUP.value,BatchStage.TRANSLATE.value:BatchItemStatus.TRANSLATION.value,BatchStage.GENERATE_TTS.value:BatchItemStatus.TTS.value,BatchStage.GENERATE_SUBTITLES.value:BatchItemStatus.SUBTITLES.value,BatchStage.PREPARE_SCENES.value:BatchItemStatus.SCENE_SETUP.value,BatchStage.RENDER.value:BatchItemStatus.RENDERING.value,BatchStage.EXPORT.value:BatchItemStatus.EXPORTING.value}.get(stage,BatchItemStatus.PROJECT_SETUP.value)
