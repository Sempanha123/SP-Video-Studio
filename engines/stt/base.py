from __future__ import annotations
from abc import abstractmethod
from pathlib import Path
from engines.base import Engine


class STTEngine(Engine):
    @abstractmethod
    def transcribe(self, media: Path, **options: object) -> list[dict[str, object]]:
        raise NotImplementedError
