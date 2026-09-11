from __future__ import annotations


class TranslationError(RuntimeError):
    user_message = "Translation could not be completed."


class TranslationDependencyMissing(TranslationError):
    user_message = "Local translation dependencies are not installed."


class TranslationModelNotInstalled(TranslationError):
    user_message = "The required translation model is not installed."


class TranslationUnsupportedLanguagePair(TranslationError):
    user_message = "The selected translation engine does not support this language pair."


class TranslationModelLoadError(TranslationError):
    user_message = "The translation model could not be loaded."


class TranslationOutOfMemory(TranslationError):
    user_message = "Translation could not continue because available memory is low."


class TranslationInvalidRequest(TranslationError):
    user_message = "Please check the translation settings and try again."


class TranslationProviderError(TranslationError):
    user_message = "The translation provider could not complete this request."


class TranslationCancelled(TranslationError):
    user_message = "Translation stopped."
