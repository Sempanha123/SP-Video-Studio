from __future__ import annotations


class PrivacyService:
    """Read-only privacy policy view for the current release.

    It intentionally does not add cloud providers. It describes existing local
    engines/network actions and the consent contract future providers must obey.
    """

    def provider_rows(self) -> list[dict[str, object]]:
        return [
            {"name": "VoxCPM2 Text-to-Speech", "mode": "Local", "online": False, "configured": True,
             "detail": "Runs from a managed local model when installed. Reference audio stays on this device unless a future online provider is explicitly chosen."},
            {"name": "Whisper Speech-to-Text", "mode": "Local", "online": False, "configured": True,
             "detail": "Transcription uses the managed local model when installed."},
            {"name": "Translation Models", "mode": "Local", "online": False, "configured": True,
             "detail": "Current managed translation engines run locally when installed."},
            {"name": "News Source Fetching", "mode": "Online", "online": True, "configured": True,
             "detail": "Only a URL the user explicitly fetches is requested. Automatic crawling is not enabled."},
            {"name": "Model Downloads", "mode": "Online", "online": True, "configured": True,
             "detail": "Managed model files can be downloaded from the trusted configured Hugging Face source. Project content is not sent."},
            {"name": "Cloud AI Providers", "mode": "Online", "online": True, "configured": False,
             "detail": "Not configured in this release. Any future provider must show what data may leave the device before first use."},
        ]

    @staticmethod
    def requires_first_use_notice(provider_kind: str) -> bool:
        return str(provider_kind or "").strip().lower() in {
            "cloud", "cloud_llm", "cloud_translation", "cloud_tts", "custom_online", "external_provider"
        }

    def summary(self) -> dict[str, object]:
        return {
            "providers": self.provider_rows(),
            "supportBundle": "Support bundles are created locally from an allow-list and exclude project content, media, reference voices, recovery data and credentials by default.",
            "diagnostics": "Diagnostics run locally. No diagnostic telemetry or automatic support upload is enabled.",
            "referenceVoices": "Reference voice recordings are sensitive user media. They are excluded from support bundles and template packages and are not uploaded automatically.",
            "localWorkflow": "Local editing, rendering and installed local AI workflows remain on this device. News/model downloads are explicit online actions.",
        }
