from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class MigrationStep(Generic[T]):
    from_version: int
    to_version: int
    migration_id: str
    apply: Callable[[T], None]
    validate: Callable[[T], None] | None = None


class MigrationRegistry(Generic[T]):
    def __init__(self, steps: list[MigrationStep[T]] | tuple[MigrationStep[T], ...] = ()) -> None:
        self._steps: dict[int, MigrationStep[T]] = {}
        for step in steps:
            self.register(step)

    def register(self, step: MigrationStep[T]) -> None:
        if step.to_version != step.from_version + 1:
            raise ValueError("Migration steps must advance exactly one schema version.")
        if step.from_version in self._steps:
            raise ValueError(f"Duplicate migration from version {step.from_version}.")
        self._steps[step.from_version] = step

    def path(self, from_version: int, to_version: int) -> list[MigrationStep[T]]:
        if from_version > to_version:
            raise ValueError("Downgrade migrations are not supported.")
        result: list[MigrationStep[T]] = []
        current = int(from_version)
        while current < int(to_version):
            step = self._steps.get(current)
            if step is None:
                raise KeyError(f"No migration registered from version {current}.")
            result.append(step)
            current = step.to_version
        return result
