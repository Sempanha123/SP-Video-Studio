from __future__ import annotations
from services.news_claim_service import NewsClaimService
class NewsReviewService:
    def __init__(self,claims:NewsClaimService)->None:self.claims=claims
    def approve(self,project_id:str,claim_id:str,override_note:str=""):return self.claims.approve(project_id,claim_id,override_note=override_note)
    def reject(self,project_id:str,claim_id:str):return self.claims.reject(project_id,claim_id)
    def lock(self,project_id:str,claim_id:str,locked:bool):return self.claims.set_locked(project_id,claim_id,locked)
