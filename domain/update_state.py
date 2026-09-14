from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum


class UpdateStateCode(str, Enum):
    IDLE = "idle"
    CHECKING = "checking"
    UP_TO_DATE = "up_to_date"
    AVAILABLE = "available"
    DOWNLOADING = "downloading"
    VALIDATING = "validating"
    READY = "ready"
    INSTALLING = "installing"
    ERROR = "error"


@dataclass(slots=True)
class UpdateState:
    current_version: str
    channel: str = "stable"
    automatic_check: bool = True
    state: str = UpdateStateCode.IDLE.value
    available_version: str = ""
    last_check_at: str = ""
    last_error: str = ""
    progress: float = 0.0
    staged_installer: str = ""
    installer_validated: bool = False
    last_installed_version: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
