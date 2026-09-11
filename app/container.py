from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


class DependencyContainer:
    """Small explicit service registry used until a larger DI need appears."""

    def __init__(self) -> None:
        self._instances: dict[object, Any] = {}
        self._factories: dict[object, Callable[["DependencyContainer"], Any]] = {}

    def register_instance(self, key: object, instance: T) -> T:
        self._instances[key] = instance
        return instance

    def register_factory(self, key: object, factory: Callable[["DependencyContainer"], T]) -> None:
        self._factories[key] = factory

    def resolve(self, key: object) -> Any:
        if key in self._instances:
            return self._instances[key]
        if key not in self._factories:
            raise KeyError(f"No dependency registered for {key!r}")
        instance = self._factories[key](self)
        self._instances[key] = instance
        return instance
