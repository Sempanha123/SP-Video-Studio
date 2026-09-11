class TTSError(RuntimeError):
    user_message = "Text-to-speech could not complete this request."


class TTSDependencyMissing(TTSError):
    user_message = "VoxCPM2 dependencies are not available."


class TTSModelNotInstalled(TTSError):
    user_message = "VoxCPM2 is not installed."


class TTSModelLoadError(TTSError):
    user_message = "VoxCPM2 could not be loaded."


class TTSGenerationError(TTSError):
    user_message = "VoxCPM2 could not generate this audio."


class TTSOutOfMemory(TTSGenerationError):
    user_message = "VoxCPM2 ran out of GPU memory."


class TTSInvalidRequest(TTSError):
    user_message = "Please check the narration settings."


class TTSUnsupportedDevice(TTSError):
    user_message = "The selected TTS device is unavailable."


class TTSCancelled(TTSError):
    user_message = "Narration generation was cancelled."
