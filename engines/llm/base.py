from abc import abstractmethod
from engines.base import Engine


class LLMEngine(Engine):
    @abstractmethod
    def generate(self, prompt: str, **options: object) -> str:
        raise NotImplementedError
