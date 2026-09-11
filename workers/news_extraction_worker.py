from __future__ import annotations
from workers.base import WorkerTask
class NewsExtractionWorker(WorkerTask):
    def __init__(self,service,project_id:str,source_id:str)->None:self.service=service;self.project_id=project_id;self.source_id=source_id
    def run(self):return self.service.extract_candidates(self.project_id,self.source_id)
