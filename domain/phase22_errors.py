from __future__ import annotations


class Phase22Error(RuntimeError):
    user_message = "SP Video Studio could not complete this editor action."


class LanguageUnsupported(Phase22Error):
    user_message = "The selected language is not available in this project."


class LanguageModelMissing(Phase22Error):
    user_message = "The selected language model is not installed."


class VisualLayerInvalid(Phase22Error):
    user_message = "This visual layer contains invalid settings."


class ChromaKeyUnavailable(Phase22Error):
    user_message = "Your FFmpeg build does not support the required chroma-key filter."


class ChromaKeyInvalid(Phase22Error):
    user_message = "Green-screen settings are invalid."


class SpeakerNotFound(Phase22Error):
    user_message = "The selected speaker could not be found."


class SpeechBlockInvalid(Phase22Error):
    user_message = "This speech block is incomplete or invalid."


class VoiceLanguageMismatch(Phase22Error):
    user_message = "The selected voice engine does not support this speech language."


class CompositionError(Phase22Error):
    user_message = "The layered video composition could not be rendered."
