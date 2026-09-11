from abc import abstractmethod
from pathlib import Path
from engines.base import Engine


class ImageGenerationEngine(Engine):
    @abstractmethod
    def generate_image(self, prompt: str, output: Path, **options: object) -> Path:
        raise NotImplementedError
