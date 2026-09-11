from __future__ import annotations

from typing import Any, Protocol


class StoryWritingProvider(Protocol):
    """Optional future Story writing provider contract.

    Phase 20 does not ship a cloud implementation. Providers must return structured
    records so Story services can validate IDs/types before applying changes.
    """

    def generate_outline(self, *, story: dict[str, Any]) -> list[dict[str, Any]]: ...
    def expand_beat(self, *, story: dict[str, Any], beat: dict[str, Any]) -> dict[str, Any]: ...
    def generate_script_section(self, *, story: dict[str, Any], beat: dict[str, Any]) -> dict[str, Any]: ...
