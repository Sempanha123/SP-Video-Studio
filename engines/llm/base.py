from __future__ import annotations

from abc import abstractmethod
from typing import Any

from engines.base import Engine


class LLMEngine(Engine):
    @abstractmethod
    def generate(self, prompt: str, **options: object) -> str:
        raise NotImplementedError

    def generate_structured(self, task: str, input: Any, schema: object | None = None, context: dict[str, Any] | None = None) -> Any:
        """Future structured-output entry point.

        Cloud/local generative providers may override this. Phase 14's deterministic
        Director provider uses the same contract without parsing chat text.
        """
        raise NotImplementedError
