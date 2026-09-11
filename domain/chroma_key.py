from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from domain.phase22_errors import ChromaKeyInvalid


PRESET_KEY_COLORS = {
    "green": "#00FF00",
    "blue": "#0000FF",
}


@dataclass(slots=True)
class ChromaKeySettings:
    enabled: bool = False
    key_color: str = "#00FF00"
    similarity: float = 0.28
    blend: float = 0.08
    spill_reduction: float = 0.0
    edge_softness: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        value = self.key_color.strip().upper()
        if len(value) != 7 or not value.startswith("#"):
            raise ChromaKeyInvalid("Key color must use #RRGGBB.")
        try:
            int(value[1:], 16)
        except ValueError as exc:
            raise ChromaKeyInvalid("Key color must use #RRGGBB.") from exc
        self.key_color = value
        for name in ("similarity", "blend", "spill_reduction", "edge_softness"):
            number = float(getattr(self, name))
            if not 0.0 <= number <= 1.0:
                raise ChromaKeyInvalid(f"{name.replace('_', ' ').title()} must be between 0 and 1.")
            setattr(self, name, number)

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "enabled": self.enabled,
            "keyColor": self.key_color,
            "similarity": self.similarity,
            "blend": self.blend,
            "spillReduction": self.spill_reduction,
            "edgeSoftness": self.edge_softness,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any] | None) -> "ChromaKeySettings":
        data = dict(raw or {})
        item = cls(
            enabled=bool(data.get("enabled", False)),
            key_color=str(data.get("keyColor", data.get("key_color", "#00FF00"))),
            similarity=float(data.get("similarity", 0.28) or 0.0),
            blend=float(data.get("blend", 0.08) or 0.0),
            spill_reduction=float(data.get("spillReduction", data.get("spill_reduction", 0.0)) or 0.0),
            edge_softness=float(data.get("edgeSoftness", data.get("edge_softness", 0.0)) or 0.0),
            metadata=dict(data.get("metadata") or {}),
        )
        item.validate()
        return item
