from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.windows


def test_windows_unicode_and_space_paths_roundtrip(tmp_path):
    if os.name != "nt":
        pytest.skip("Windows-specific filesystem acceptance runs on Windows 11 release QA")
    root = tmp_path / "QA Path ខ្មែរ ไทย Việt"
    root.mkdir()
    for name, text in {
        "ខ្មែរ file.txt": "ខ្មែរ",
        "ไทย file.txt": "ไทย",
        "Việt file.txt": "Tiếng Việt",
    }.items():
        path = root / name
        path.write_text(text, encoding="utf-8")
        assert path.read_text(encoding="utf-8") == text
        assert root.resolve() in path.resolve().parents
