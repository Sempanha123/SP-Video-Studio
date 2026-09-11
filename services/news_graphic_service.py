from __future__ import annotations
import hashlib
from domain.news_graphic_preset import BUILTIN_GRAPHIC_PRESETS,GRAPHIC_PRESET_BY_ID

def content_hash(text:str)->str:return hashlib.sha256((text or '').encode('utf-8')).hexdigest()
class NewsGraphicService:
    def builtin_presets(self)->list[dict]:return [x.to_dict() for x in BUILTIN_GRAPHIC_PRESETS]
    def preset(self,preset_id:str):return GRAPHIC_PRESET_BY_ID.get(preset_id)
    @staticmethod
    def quote_display(text:str,kind:str)->str:
        kind=(kind or '').casefold()
        if kind in {'exact','translated','translated_quote'}:return f'“{text.strip()}”'
        return text.strip()
    @staticmethod
    def quote_label(kind:str)->str:
        return 'Translated' if (kind or '').casefold() in {'translated','translated_quote'} else ('Paraphrase' if (kind or '').casefold()=='paraphrase' else '')
