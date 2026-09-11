from __future__ import annotations
from copy import deepcopy
from domain.news_visual_theme import NewsVisualTheme
from services.news_visual_errors import NewsVisualPresetNotFound

_THEME_DATA={
'clean_news':dict(name='Clean News',primary_color='#18212B',secondary_color='#253241',accent_color='#D8A84E',background_color='#0F141A',surface_color='#D9161D24',text_primary='#FFFFFFFF',text_secondary='#D9E2ECFF'),
'modern_news':dict(name='Modern News',primary_color='#172331',secondary_color='#26394B',accent_color='#4DA3A8',background_color='#0C1218',surface_color='#E61A2633',text_primary='#FFFFFFFF',text_secondary='#D9E7EEFF'),
'breaking_news':dict(name='Breaking News',primary_color='#2B171A',secondary_color='#3A2024',accent_color='#D84A4A',background_color='#130C0D',surface_color='#E629171A',text_primary='#FFFFFFFF',text_secondary='#FFE1E1FF'),
'documentary_news':dict(name='Documentary News',primary_color='#282720',secondary_color='#3B392E',accent_color='#B7A66D',background_color='#15140F',surface_color='#E62A2921',text_primary='#FFFDF4FF',text_secondary='#E5DEC5FF'),
'minimal_news':dict(name='Minimal News',primary_color='#202327',secondary_color='#30353B',accent_color='#9AA5B1',background_color='#111315',surface_color='#E6202327',text_primary='#FFFFFFFF',text_secondary='#D5DAE0FF'),
'tech_news':dict(name='Tech News',primary_color='#14252A',secondary_color='#1F3840',accent_color='#48A6A7',background_color='#0B1518',surface_color='#E6152B31',text_primary='#F5FFFFFF',text_secondary='#CFE9EAFF'),
}

class NewsBrandingService:
    def builtin_themes(self)->list[dict]:
        return [{"id":k,**v} for k,v in _THEME_DATA.items()]
    def make_theme(self,project_id:str,preset_id:str)->NewsVisualTheme:
        data=_THEME_DATA.get(preset_id)
        if data is None:raise NewsVisualPresetNotFound('News visual theme could not be found.')
        return NewsVisualTheme(project_id=project_id,preset_id=preset_id,**deepcopy(data))
    def apply_preset(self,theme:NewsVisualTheme,preset_id:str)->NewsVisualTheme:
        data=_THEME_DATA.get(preset_id)
        if data is None:raise NewsVisualPresetNotFound('News visual theme could not be found.')
        for key,value in data.items():setattr(theme,key,value)
        theme.preset_id=preset_id;return theme
