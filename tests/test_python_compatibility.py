from pathlib import Path

from packaging.specifiers import SpecifierSet
from packaging.version import Version


def test_project_metadata_accepts_python_314():
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'requires-python = ">=3.11,<3.15"' in text
    spec = SpecifierSet(">=3.11,<3.15")
    assert Version("3.11") in spec
    assert Version("3.14.7") in spec
    assert Version("3.15") not in spec


def test_python_314_compatible_dependency_floor_is_declared():
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert '"PySide6>=6.10.2,<7"' in text
    assert '"psutil>=7.2,<8"' in text
    assert '"Pillow>=12,<13"' in text
