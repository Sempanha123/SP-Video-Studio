from __future__ import annotations

from dataclasses import dataclass
from sqlite3 import Connection
from collections.abc import Callable

from .m001_create_projects import migrate as create_projects


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    apply: Callable[[Connection], None]


MIGRATIONS: tuple[Migration, ...] = (
    Migration(1, "create_projects", create_projects),
)
