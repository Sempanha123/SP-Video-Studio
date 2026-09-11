# Phase 23 — Shorts Maker

Phase 23 adds a manual-first Shorts workflow without introducing a second editor, renderer, timeline, subtitle engine, or speaker system.

## Architecture

`shorts_projects`, `short_candidates`, and `short_segments` store workflow metadata and immutable source relationships. Once a candidate is approved, the authoritative `ProjectService.duplicate_project()` path creates an independent project. Selected ranges are then represented as ordinary Scenes and edited in the existing Timeline.

Source projects are not cropped or rewritten. Video clips continue to reference project-managed MediaAssets and source in/out ranges.

## Highlight selection

The Shorts panel supports manual In/Out points from the Timeline playhead, multiple manual ranges, exact transcript-segment selection, existing Scene selection, and deterministic timing-boundary suggestions. Suggestions are not semantic rankings and never display viral/retention/engagement predictions.

## Reframe and layered visuals

Vertical framing is stored as non-destructive Scene metadata and resolved by the existing Phase 22 compositor. 9:16 is recommended, while 1:1 and 16:9 remain available. Manual center/left/right/top/bottom positioning, zoom/crop, B-roll, PIP, presenter/character layers and chroma key continue to use the Phase 22 visual model.

There is no face tracking. Moving subjects can be split on the normal Timeline and reframed per clip.

## Captions and languages

Short caption tracks are normal Phase 12 subtitle tracks. Creator/Bold/Karaoke/Clean presets are exposed. Cues can be regrouped non-destructively from real TranscriptWord timestamps. Thai/Khmer use existing tokens rather than character slicing; Vietnamese Unicode/diacritics are preserved. Translated word timing is never fabricated.

The language picker and capability model come from the Phase 22 Language Registry.

## Dub and multi-speaker

Derived projects use existing Phase 22 SpeakerProfile/SpeechBlock duplication. A ready Phase 21 dub mix can be range-assembled to a project-owned Short audio track; the generic primary-audio override remains the renderer integration point. Duplicated timed subtitle tracks are trimmed/re-timed for ranged Shorts.

## Silence helper

Long silence ranges are inferred from existing transcript/VAD gaps. The app only suggests them. Accepting a suggestion uses existing Timeline split/delete commands, keeping Undo/Redo and ripple behavior in the Phase 17 command stack. Transcript words are not used as destructive video-edit instructions.

## Export

Shorts resolves recommended IDs from the existing Phase 16 export preset registry (`tiktok`, `youtube_shorts`, `instagram_reels`, Facebook vertical, and generic presets). Rendering/export remains the standard pipeline.

## Limitations

Real-time Qt multi-layer preview is best-effort; FFmpeg render is authoritative. Phase 23 does not upload to social networks, download copyrighted music, perform face tracking, create engagement scores, or add Batch Factory behavior.
