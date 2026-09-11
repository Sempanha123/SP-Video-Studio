from abc import abstractmethod
from pathlib import Path
from engines.base import Engine


class VideoGenerationEngine(Engine):
    @abstractmethod
    def generate_video(self, prompt: str, output: Path, **options: object) -> Path:
        raise NotImplementedError
