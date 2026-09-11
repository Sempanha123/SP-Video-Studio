from __future__ import annotations
from abc import abstractmethod
from pathlib import Path
from engines.base import Engine


class TTSEngine(Engine):
    @abstractmethod
    def synthesize(self, text: str, output: Path, **options: object) -> Path:
        raise NotImplementedError
