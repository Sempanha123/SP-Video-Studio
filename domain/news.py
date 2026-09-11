from dataclasses import dataclass, field


@dataclass(slots=True)
class NewsSource:
    title: str
    publisher: str
    url: str
    publication_date: str | None = None
    retrieved_date: str | None = None
    author: str | None = None


@dataclass(slots=True)
class NewsClaim:
    claim: str
    supporting_sources: list[str] = field(default_factory=list)
    confidence: float | None = None
    review_status: str = "pending"
