from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class MediaAsset:
    asset_id: str
    path: Path
    media_type: str
    source: str = "imported"
