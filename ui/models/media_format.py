from __future__ import annotations


def format_duration(duration_ms: int | None) -> str:
    if duration_ms is None:
        return ""
    total_seconds = max(0, int(round(duration_ms / 1000.0)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def format_file_size(size: int | None) -> str:
    if size is None:
        return ""
    value = max(0, int(size))
    units = ("B", "KB", "MB", "GB", "TB")
    amount = float(value)
    unit = units[0]
    for candidate in units:
        unit = candidate
        if amount < 1024.0 or candidate == units[-1]:
            break
        amount /= 1024.0
    if unit == "B":
        return f"{int(amount)} B"
    return f"{amount:.1f} {unit}"


def format_resolution(width: int | None, height: int | None) -> str:
    if not width or not height:
        return ""
    return f"{int(width)} × {int(height)}"


def format_fps(value: float | None) -> str:
    if value is None:
        return ""
    rounded = round(float(value), 2)
    if rounded.is_integer():
        return f"{int(rounded)} fps"
    return f"{rounded:.2f}".rstrip("0").rstrip(".") + " fps"
