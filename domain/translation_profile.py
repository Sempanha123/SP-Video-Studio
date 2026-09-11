from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TranslationProfile:
    source_language: str = "en"
    target_language: str = "km"
    engine_id: str = "local-marian"
    model_id: str = ""
    keep_terms: tuple[str, ...] = ()
    device: str = "auto"
    settings: dict[str, Any] = field(default_factory=dict)
