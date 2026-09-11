from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DirectorProviderMetadata:
    provider_id: str
    name: str
    requires_network: bool
    requires_credentials: bool
    supports_structured_output: bool
    supports_multilingual: bool
    privacy_description: str
