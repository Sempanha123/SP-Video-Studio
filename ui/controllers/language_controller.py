from __future__ import annotations
from PySide6.QtCore import QObject, Property, Slot


class LanguageController(QObject):
    def __init__(self, service, parent=None): super().__init__(parent); self.service=service
    @Property('QVariantList', constant=True)
    def languages(self): return self.service.list_languages()
    @Slot(str,result='QVariantList')
    def search(self,query): return self.service.list_languages(query)
    @Slot(str,str,result='QVariantList')
    def translationTargets(self,source,engine_id=""):
        pairs=self.service.translation_pairs(engine_id or None); targets={target for src,target in pairs if src==source}
        return [row for row in self.service.list_languages() if row.get("code") in targets]
    @Slot(str,str,result=bool)
    def supportsTts(self,code,engine_id="voxcpm2"): return self.service.supports_tts(code,engine_id)
    @Slot(str,str,str,result=bool)
    def supportsTranslation(self,source,target,engine_id=""): return self.service.supports_translation_pair(source,target,engine_id or None)
