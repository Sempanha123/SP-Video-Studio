from __future__ import annotations

from pathlib import Path

from media.subtitles.ass_exporter import escape_ass_text
from media.subtitles.ass_style_builder import ass_color


class OverlayRenderer:
    """Render scene text overlays through ASS/libass for reliable Unicode shaping."""

    def __init__(self, default_font: str = "Noto Sans Khmer") -> None:
        self.default_font = default_font

    def write_ass(
        self,
        overlays: list[dict],
        destination: Path,
        *,
        width: int,
        height: int,
        duration_ms: int,
    ) -> Path | None:
        events: list[str] = []
        for item in sorted(overlays, key=lambda value: int(value.get("order", 0) or 0)):
            if not item.get("visible", True) or str(item.get("type", "")) in {"logo", "shape"}:
                continue
            text = str(item.get("text", "") or "")
            secondary = str(item.get("secondaryText", "") or "")
            if secondary:
                text += "\n" + secondary
            if not text:
                continue

            style = dict(item.get("style", {}) or {})
            font = str(style.get("fontFamily") or self.default_font)
            font_size = max(8, round(float(style.get("fontSize", 48) or 48) * height / 1080.0))
            weight = int(style.get("fontWeight", 600) or 600)
            color = str(style.get("color", "#FFFFFFFF"))
            try:
                ass_value = ass_color(color)
            except ValueError:
                ass_value = ass_color("#FFFFFFFF")
            # Override color tags use BGR; alpha is applied separately so opacity stays predictable.
            bgr = ass_value[4:-1]
            color_alpha = int(ass_value[2:4], 16)

            x = round(float(item.get("x", 0.1)) * width)
            y = round(float(item.get("y", 0.1)) * height)
            start = max(0, int(item.get("startOffsetMs", 0) or 0))
            raw_end = int(item.get("endOffsetMs", -1) or -1)
            end = duration_ms if raw_end < 0 else min(duration_ms, raw_end)
            if end <= start:
                continue

            opacity = max(0.0, min(1.0, float(item.get("opacity", 1.0) or 0)))
            overlay_alpha = round((1.0 - opacity) * 255)
            combined_alpha = min(255, color_alpha + overlay_alpha - round(color_alpha * overlay_alpha / 255))
            tags = (
                f"{{\\an7\\pos({x},{y})\\fn{escape_ass_text(font)}\\fs{font_size}"
                f"\\b{1 if weight >= 700 else 0}\\1c&H{bgr}&\\1a&H{combined_alpha:02X}&}}"
            )
            events.append(
                f"Dialogue: 0,{self._time(start)},{self._time(end)},Default,,0,0,0,,"
                f"{tags}{escape_ass_text(text)}"
            )

        if not events:
            return None
        destination.parent.mkdir(parents=True, exist_ok=True)
        header = (
            f"[Script Info]\nScriptType: v4.00+\nPlayResX: {width}\nPlayResY: {height}\n"
            "ScaledBorderAndShadow: yes\nWrapStyle: 0\n\n"
            "[V4+ Styles]\n"
            "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,"
            "Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,"
            "Alignment,MarginL,MarginR,MarginV,Encoding\n"
            f"Style: Default,{self.default_font},48,&H00FFFFFF,&H00FFFFFF,&H00101010,&H00000000,"
            "-1,0,0,0,100,100,0,0,1,2,1,7,20,20,20,1\n\n"
            "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
        )
        destination.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
        return destination

    @staticmethod
    def _time(ms: int) -> str:
        value = max(0, int(ms))
        hours, rem = divmod(value, 3_600_000)
        minutes, rem = divmod(rem, 60_000)
        seconds, rem = divmod(rem, 1000)
        centiseconds = round(rem / 10)
        if centiseconds >= 100:
            seconds += 1
            centiseconds = 0
        if seconds >= 60:
            minutes += seconds // 60
            seconds %= 60
        if minutes >= 60:
            hours += minutes // 60
            minutes %= 60
        return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"
