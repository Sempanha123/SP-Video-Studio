from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class EngineCapabilities:
    name: str
    version: str | None = None
    features: set[str] = field(default_factory=set)


class Engine(ABC):
    @abstractmethod
    def capabilities(self) -> EngineCapabilities:
        raise NotImplementedError

    def is_available(self) -> bool:
        return True

    def close(self) -> None:
        pass


class TextEngine(Engine, ABC):
    @abstractmethod
    def process(self, text: str, **options: Any) -> str:
        raise NotImplementedError
