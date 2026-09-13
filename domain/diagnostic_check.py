from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from domain.diagnostic_result import DiagnosticResult


@dataclass(frozen=True, slots=True)
class DiagnosticCheck:
    id: str
    category: str
    name: str
    runner: Callable[[], DiagnosticResult]
    full_only: bool = False
