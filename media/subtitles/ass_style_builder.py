from __future__ import annotations

from domain.subtitle_style import SubtitleStyle


def ass_color(value: str) -> str:
    raw=value.lstrip("#")
    if len(raw)==6:
        rr,gg,bb=raw[0:2],raw[2:4],raw[4:6]; aa="00"
    elif len(raw)==8:
        rr,gg,bb,opacity=raw[0:2],raw[2:4],raw[4:6],raw[6:8]
        aa=f"{255-int(opacity,16):02X}"
    else:
        raise ValueError("ASS color requires #RRGGBB or #RRGGBBAA.")
    return f"&H{aa}{bb}{gg}{rr}&"


def ass_alignment(style: SubtitleStyle) -> int:
    vertical={"bottom":0,"middle":3,"top":6}[style.vertical_position]
    horizontal={"left":1,"center":2,"right":3}[style.alignment]
    return vertical+horizontal


def build_ass_style(style: SubtitleStyle, *, canvas_width: int = 1920, canvas_height: int = 1080) -> str:
    scale=canvas_height/1080.0
    font_size=max(8, round(style.font_size*scale))
    margin_lr=max(0,round(style.horizontal_margin*canvas_width))
    margin_v=max(0,round(style.vertical_margin*canvas_height))
    border=3 if style.background_enabled else 1
    back=ass_color(style.background_color + f"{round(style.background_opacity*255):02X}" if len(style.background_color)==7 else style.background_color)
    return ",".join([
        "Default", style.font_family, str(font_size), ass_color(style.text_color), ass_color(style.secondary_text_color),
        ass_color(style.outline_color), back, "-1" if style.font_weight >= 700 else "0", "-1" if style.italic else "0",
        "0", "0", "100", "100", "0", "0", str(border), f"{style.outline_width:g}", f"{style.shadow_offset if style.shadow_enabled else 0:g}",
        str(ass_alignment(style)), str(margin_lr), str(margin_lr), str(margin_v), "1"
    ])
