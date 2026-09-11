from __future__ import annotations


class STTError(RuntimeError):
    user_message = "Speech recognition could not complete this request."


class STTDependencyMissing(STTError):
    user_message = "The faster-whisper speech recognition dependencies are not installed."


class STTModelNotInstalled(STTError):
    user_message = "The selected Whisper model is not installed."


class STTModelLoadError(STTError):
    user_message = "The Whisper model could not be loaded."


class STTUnsupportedDevice(STTError):
    user_message = "The selected speech recognition device is not available."


class STTTranscriptionError(STTError):
    user_message = "This media could not be transcribed."


class STTOutOfMemory(STTError):
    user_message = "Whisper ran out of memory while transcribing this media."


class STTInvalidMedia(STTError):
    user_message = "This file could not be prepared for transcription."


class STTCancelled(STTError):
    user_message = "Transcription cancelled."


class STTInvalidRequest(STTError):
    user_message = "The transcription settings are invalid."


class STTResourceConflict(STTError):
    user_message = "Another AI model is currently using the resources required for transcription."
