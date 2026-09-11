from __future__ import annotations
from domain.batch_item import BatchItemStatus
from domain.batch_errors import BatchCancelled

class BatchWorker:
    def __init__(self,execution,items,logger=None):self.execution=execution;self.items=items;self.logger=logger
    def run_item(self,batch,item,*,cancellation=None,progress_callback=None,max_stages:int|None=None):
        ran=0
        while item.status_code not in {BatchItemStatus.COMPLETED.value,BatchItemStatus.CANCELLED.value,BatchItemStatus.SKIPPED.value,BatchItemStatus.FAILED.value}:
            if cancellation is not None and cancellation.is_cancelled:raise BatchCancelled()
            result=self.execution.execute_next(item,batch,cancellation=cancellation,progress_callback=progress_callback)
            item=self.items.get(item.id) or item
            if result is None:self.execution.finalize_if_done(item,batch);break
            ran+=1
            if max_stages is not None and ran>=max_stages:break
        return self.items.get(item.id) or item
