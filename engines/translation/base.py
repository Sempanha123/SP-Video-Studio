from abc import abstractmethod
from engines.base import Engine


class TranslationEngine(Engine):
    @abstractmethod
    def translate(self, text: str, source_language: str, target_language: str) -> str:
        raise NotImplementedError
