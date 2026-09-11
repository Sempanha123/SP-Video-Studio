from __future__ import annotations

import mimetypes
from pathlib import Path

from domain.media import MediaType


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
SUPPORTED_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS | IMAGE_EXTENSIONS


class FileClassifier:
    def classify(self, path: str | Path) -> str | None:
        extension = Path(path).suffix.lower()
        if extension in VIDEO_EXTENSIONS:
            return MediaType.VIDEO.value
        if extension in AUDIO_EXTENSIONS:
            return MediaType.AUDIO.value
        if extension in IMAGE_EXTENSIONS:
            return MediaType.IMAGE.value
        return None

    @staticmethod
    def mime_type(path: str | Path) -> str | None:
        mime, _ = mimetypes.guess_type(str(path))
        return mime

    @staticmethod
    def file_dialog_filter() -> str:
        ordered = sorted(SUPPORTED_EXTENSIONS)
        return " ".join(f"*{extension}" for extension in ordered)
