from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from ui.controllers.playback_controller import PlaybackController


def test_local_path_to_qurl_handles_spaces_and_khmer(tmp_path: Path):
    path = tmp_path / "ព័ត៌មានថ្មី (1).mp4"
    value = PlaybackController.local_path_to_url(path)
    assert value.startswith("file:")
    assert "%20" in value or " " not in value
    assert "ព័ត៌មានថ្មី" in value or "%" in value
