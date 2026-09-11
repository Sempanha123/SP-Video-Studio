from __future__ import annotations
from pathlib import Path
from domain.batch import BatchStatus
from domain.batch_item import BatchItemStatus

class BatchRecoveryService:
    def __init__(self,batches,items,*,output_validator=None,logger=None):self.batches=batches;self.items=items;self.output_validator=output_validator;self.logger=logger
    def recover_startup(self)->dict[str,int]:
        locks=self.batches.clear_stale_locks();interrupted=self.items.mark_running_interrupted();missing=0
        for batch in self.batches.list_all():
            changed=False
            if batch.status_code==BatchStatus.RUNNING.value:batch.status=BatchStatus.PAUSED.value;batch.metadata['recoveryReason']='Application restarted during Batch processing.';changed=True
            for item in self.items.list_for_batch(batch.id,status=BatchItemStatus.COMPLETED.value):
                if item.output_path and not Path(item.output_path).is_file():item.status=BatchItemStatus.OUTPUT_MISSING.value;item.error_code='output_missing';item.error_message='Completed output is missing.';self.items.save(item);missing+=1
                elif item.output_path and self.output_validator:
                    try:
                        if not self.output_validator(item.output_path):item.status=BatchItemStatus.OUTPUT_MISSING.value;item.error_code='output_invalid';item.error_message='Completed output did not pass validation.';self.items.save(item);missing+=1
                    except Exception:pass
            if changed:self.batches.save(batch)
        return {'clearedLocks':locks,'interruptedItems':interrupted,'missingOutputs':missing}
