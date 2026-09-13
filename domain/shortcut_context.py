from __future__ import annotations

from enum import StrEnum


class ShortcutContext(StrEnum):
    GLOBAL = "global"
    PROJECT = "project"
    PLAYBACK = "playback"
    TIMELINE = "timeline"
    SPEECH_EDITOR = "speech_editor"
    SUBTITLE_EDITOR = "subtitle_editor"
    TEXT_EDITOR = "text_editor"
    MEDIA_LIBRARY = "media_library"
    ASSET_LIBRARY = "asset_library"
    BATCH_FACTORY = "batch_factory"
    AUDIO_MIXER = "audio_mixer"
    WORD_TIMING = "word_timing"
    SOURCE_RANGE = "source_range"


# GLOBAL intentionally overlaps every non-text context. Text editing is protected
# separately so native TextField/TextArea semantics win for editing keys.
def contexts_overlap(left: str | ShortcutContext, right: str | ShortcutContext) -> bool:
    a = ShortcutContext(str(left))
    b = ShortcutContext(str(right))
    if a == b:
        return True
    if ShortcutContext.GLOBAL in {a, b}:
        return True
    if ShortcutContext.TEXT_EDITOR in {a, b}:
        return False
    # Project/playback commands may be active beside a focused editor.
    if ShortcutContext.PROJECT in {a, b}:
        return True
    if ShortcutContext.PLAYBACK in {a, b}:
        return True
    return False


def context_priority(active: str | ShortcutContext) -> tuple[ShortcutContext, ...]:
    current = ShortcutContext(str(active))
    order = [current]
    if current not in {ShortcutContext.GLOBAL, ShortcutContext.PROJECT}:
        order.append(ShortcutContext.PROJECT)
    if ShortcutContext.GLOBAL not in order:
        order.append(ShortcutContext.GLOBAL)
    return tuple(order)
