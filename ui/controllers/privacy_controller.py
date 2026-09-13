from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal, Slot

from services.privacy_service import PrivacyService


class PrivacyController(QObject):
    changed = Signal()

    def __init__(self, service: PrivacyService, parent=None) -> None:
        super().__init__(parent)
        self.service = service

    @Property("QVariantList", notify=changed)
    def providerRows(self):
        return self.service.provider_rows()

    @Property("QVariantMap", notify=changed)
    def summary(self):
        return self.service.summary()

    @Slot(str, result=bool)
    def requiresFirstUseNotice(self, provider_kind: str) -> bool:
        return self.service.requires_first_use_notice(provider_kind)
