"""Compatibility exports for the Phase 18 source-grounded News domain."""
from domain.news_project import NewsProjectMetadata, NewsProjectStatus
from domain.news_source import NewsSource, NewsSourceSnapshot, NewsSourceStatus, NewsSourceType
from domain.news_claim import NewsClaim, NewsClaimStatus, NewsEvidence
from domain.news_brief import NewsBrief, NewsBriefItem
from domain.news_script_mapping import NewsScriptMapping

__all__ = [
    "NewsProjectMetadata", "NewsProjectStatus", "NewsSource", "NewsSourceSnapshot",
    "NewsSourceStatus", "NewsSourceType", "NewsClaim", "NewsClaimStatus", "NewsEvidence",
    "NewsBrief", "NewsBriefItem", "NewsScriptMapping",
]
