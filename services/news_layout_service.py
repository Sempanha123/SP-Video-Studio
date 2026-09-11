from __future__ import annotations
from domain.news_scene_layout import BUILTIN_LAYOUTS,LAYOUT_BY_ID
from services.news_visual_errors import NewsVisualInvalidLayout

_RATIOS={'16:9':'wide','9:16':'vertical','1:1':'square'}
# Geometry is normalized and renderer-neutral. Text/background content is supplied separately.
_GEOMETRY={
'headline_focus':{
 'wide':dict(card=(.08,.58,.84,.27),text=(.11,.61,.78,.19),source=(.11,.82,.56,.06)),
 'vertical':dict(card=(.07,.56,.86,.30),text=(.11,.60,.78,.20),source=(.11,.82,.68,.05)),
 'square':dict(card=(.08,.57,.84,.29),text=(.12,.61,.76,.19),source=(.12,.82,.65,.05))},
'media_headline':{
 'wide':dict(card=(.05,.69,.90,.22),text=(.08,.72,.84,.14),source=(.08,.87,.62,.04)),
 'vertical':dict(card=(.06,.62,.88,.28),text=(.10,.66,.80,.17),source=(.10,.85,.70,.04)),
 'square':dict(card=(.06,.64,.88,.25),text=(.10,.68,.80,.15),source=(.10,.85,.70,.04))},
'media_lower_third':{
 'wide':dict(card=(.05,.76,.65,.15),text=(.08,.79,.58,.09),source=(.73,.84,.20,.04)),
 'vertical':dict(card=(.07,.72,.86,.17),text=(.11,.75,.78,.10),source=(.11,.88,.65,.035)),
 'square':dict(card=(.06,.74,.80,.16),text=(.10,.77,.72,.09),source=(.10,.89,.60,.035))},
'fact_focus':{
 'wide':dict(card=(.12,.20,.76,.56),text=(.18,.29,.64,.33),source=(.18,.67,.58,.05)),
 'vertical':dict(card=(.08,.24,.84,.52),text=(.14,.32,.72,.31),source=(.14,.68,.68,.05)),
 'square':dict(card=(.10,.22,.80,.55),text=(.16,.31,.68,.31),source=(.16,.69,.64,.05))},
'quote_focus':{
 'wide':dict(card=(.10,.16,.80,.62),text=(.17,.24,.66,.38),source=(.17,.67,.60,.06)),
 'vertical':dict(card=(.07,.18,.86,.62),text=(.13,.25,.74,.40),source=(.13,.70,.70,.06)),
 'square':dict(card=(.09,.18,.82,.60),text=(.15,.25,.70,.37),source=(.15,.68,.66,.06))},
'number_focus':{
 'wide':dict(card=(.14,.18,.72,.58),text=(.19,.25,.62,.36),source=(.19,.68,.55,.05)),
 'vertical':dict(card=(.08,.22,.84,.55),text=(.14,.29,.72,.35),source=(.14,.69,.68,.05)),
 'square':dict(card=(.10,.20,.80,.57),text=(.16,.28,.68,.35),source=(.16,.69,.64,.05))},
'source_focus':{
 'wide':dict(card=(.14,.24,.72,.46),text=(.20,.33,.60,.22),source=(.20,.58,.60,.06)),
 'vertical':dict(card=(.10,.28,.80,.42),text=(.16,.36,.68,.20),source=(.16,.59,.68,.06)),
 'square':dict(card=(.12,.26,.76,.44),text=(.18,.34,.64,.21),source=(.18,.59,.64,.06))},
'split_visual':{
 'wide':dict(card=(.52,.08,.43,.84),text=(.57,.18,.33,.44),source=(.57,.80,.32,.05)),
 'vertical':dict(card=(.06,.55,.88,.39),text=(.11,.61,.78,.22),source=(.11,.86,.70,.04)),
 'square':dict(card=(.48,.08,.46,.84),text=(.54,.18,.34,.45),source=(.54,.81,.32,.05))},
'full_media':{
 'wide':dict(card=(.05,.06,.30,.10),text=(.07,.08,.26,.06),source=(.68,.90,.27,.035)),
 'vertical':dict(card=(.07,.08,.44,.09),text=(.10,.10,.38,.05),source=(.10,.91,.70,.03)),
 'square':dict(card=(.06,.07,.38,.09),text=(.09,.09,.32,.05),source=(.61,.91,.33,.03))},
'intro':{
 'wide':dict(card=(.10,.25,.80,.48),text=(.16,.34,.68,.25),source=(.16,.64,.50,.05)),
 'vertical':dict(card=(.08,.30,.84,.40),text=(.14,.37,.72,.22),source=(.14,.63,.60,.05)),
 'square':dict(card=(.10,.28,.80,.43),text=(.16,.36,.68,.23),source=(.16,.64,.55,.05))},
'outro':{
 'wide':dict(card=(.12,.29,.76,.42),text=(.18,.37,.64,.20),source=(.18,.61,.58,.05)),
 'vertical':dict(card=(.09,.32,.82,.38),text=(.15,.39,.70,.19),source=(.15,.62,.66,.05)),
 'square':dict(card=(.11,.30,.78,.40),text=(.17,.38,.66,.20),source=(.17,.62,.62,.05))},
}
class NewsLayoutService:
    def builtin_layouts(self)->list[dict]:return [x.to_dict() for x in BUILTIN_LAYOUTS]
    def resolve_layout(self,preset_id:str,aspect_ratio:str,content:dict|None=None)->dict:
        if preset_id not in LAYOUT_BY_ID:raise NewsVisualInvalidLayout('News scene layout could not be found.')
        ratio=_RATIOS.get(aspect_ratio,'wide');g=_GEOMETRY[preset_id][ratio]
        return {'presetId':preset_id,'aspectRatio':aspect_ratio,'card':g['card'],'text':g['text'],'source':g['source'],'content':dict(content or {})}
    def recommended(self,role:str='',claim_type:str='')->str:
        role=(role or '').casefold();claim_type=(claim_type or '').casefold()
        if claim_type in {'quote'} or role=='quote':return 'quote_focus'
        if claim_type in {'number','date'} or role=='number':return 'number_focus'
        if role in {'lead','headline'}:return 'headline_focus'
        if role in {'intro'}:return 'intro'
        if role in {'outro'}:return 'outro'
        if role in {'background','context'}:return 'media_headline'
        return 'fact_focus'
