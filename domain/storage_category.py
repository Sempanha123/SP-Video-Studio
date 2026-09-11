from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class StorageSafety(str, Enum):
    SAFE_TO_CLEAR = "safe_to_clear"
    REGENERATABLE = "regeneratable"
    PROTECTED = "protected"
    USER_DATA = "user_data"
    EXTERNAL = "external"


class StorageCategory(str, Enum):
    PROJECT_DATA = "project_data"
    PROJECT_MEDIA = "project_media"
    GENERATED_AUDIO = "generated_audio"
    PREVIEW_CACHE = "preview_cache"
    THUMBNAIL_CACHE = "thumbnail_cache"
    RENDER_TEMP = "render_temp"
    TRANSCRIPTION_TEMP = "transcription_temp"
    TRANSLATION_CACHE = "translation_cache"
    ASSET_LIBRARY = "asset_library"
    ASSET_THUMBNAIL_CACHE = "asset_thumbnail_cache"
    TEMPLATE_CACHE = "template_cache"
    BATCH_INTERMEDIATE = "batch_intermediate"
    RECOVERY_DATA = "recovery_data"
    AI_MODELS = "ai_models"
    FINAL_EXPORTS = "final_exports"
    LOGS = "logs"
    EXTERNAL_REFERENCES = "external_references"


@dataclass(frozen=True, slots=True)
class CategoryDefinition:
    category: StorageCategory
    label: str
    safety: StorageSafety
    description: str
    cache: bool = False


CATEGORY_DEFINITIONS: dict[StorageCategory, CategoryDefinition] = {
    StorageCategory.PROJECT_DATA: CategoryDefinition(StorageCategory.PROJECT_DATA, "Project Data", StorageSafety.USER_DATA, "Scripts, scenes, timelines, subtitles and project databases."),
    StorageCategory.PROJECT_MEDIA: CategoryDefinition(StorageCategory.PROJECT_MEDIA, "Project Media", StorageSafety.USER_DATA, "Project-owned source media copies."),
    StorageCategory.GENERATED_AUDIO: CategoryDefinition(StorageCategory.GENERATED_AUDIO, "Generated Audio", StorageSafety.REGENERATABLE, "Unreferenced generated speech may be rebuilt; active project audio is protected.", True),
    StorageCategory.PREVIEW_CACHE: CategoryDefinition(StorageCategory.PREVIEW_CACHE, "Preview Cache", StorageSafety.SAFE_TO_CLEAR, "Low-resolution composition and playback previews.", True),
    StorageCategory.THUMBNAIL_CACHE: CategoryDefinition(StorageCategory.THUMBNAIL_CACHE, "Thumbnail Cache", StorageSafety.SAFE_TO_CLEAR, "Regeneratable project and media thumbnails.", True),
    StorageCategory.RENDER_TEMP: CategoryDefinition(StorageCategory.RENDER_TEMP, "Render Temporary Files", StorageSafety.SAFE_TO_CLEAR, "Intermediate render files not owned by active jobs.", True),
    StorageCategory.TRANSCRIPTION_TEMP: CategoryDefinition(StorageCategory.TRANSCRIPTION_TEMP, "Transcription Temporary Files", StorageSafety.SAFE_TO_CLEAR, "Temporary extracted audio and speech-recognition working files.", True),
    StorageCategory.TRANSLATION_CACHE: CategoryDefinition(StorageCategory.TRANSLATION_CACHE, "Translation Cache", StorageSafety.SAFE_TO_CLEAR, "Reproducible provider/local translation response cache.", True),
    StorageCategory.ASSET_LIBRARY: CategoryDefinition(StorageCategory.ASSET_LIBRARY, "Asset Library", StorageSafety.USER_DATA, "Managed reusable source assets."),
    StorageCategory.ASSET_THUMBNAIL_CACHE: CategoryDefinition(StorageCategory.ASSET_THUMBNAIL_CACHE, "Asset Thumbnail Cache", StorageSafety.SAFE_TO_CLEAR, "Regeneratable Asset Library thumbnails.", True),
    StorageCategory.TEMPLATE_CACHE: CategoryDefinition(StorageCategory.TEMPLATE_CACHE, "Template Cache", StorageSafety.SAFE_TO_CLEAR, "Generated template previews and import staging.", True),
    StorageCategory.BATCH_INTERMEDIATE: CategoryDefinition(StorageCategory.BATCH_INTERMEDIATE, "Batch Intermediate Data", StorageSafety.SAFE_TO_CLEAR, "Temporary Batch Factory working files, not persistent Batch projects.", True),
    StorageCategory.RECOVERY_DATA: CategoryDefinition(StorageCategory.RECOVERY_DATA, "Recovery Data", StorageSafety.PROTECTED, "Phase 27 recovery snapshots managed by recovery retention rules."),
    StorageCategory.AI_MODELS: CategoryDefinition(StorageCategory.AI_MODELS, "AI Models", StorageSafety.PROTECTED, "Installed application-owned AI models; managed by Model Manager."),
    StorageCategory.FINAL_EXPORTS: CategoryDefinition(StorageCategory.FINAL_EXPORTS, "Final Exports", StorageSafety.USER_DATA, "Finished user outputs; never removed by cache cleanup."),
    StorageCategory.LOGS: CategoryDefinition(StorageCategory.LOGS, "Logs", StorageSafety.SAFE_TO_CLEAR, "Old application logs; the current active log is excluded.", True),
    StorageCategory.EXTERNAL_REFERENCES: CategoryDefinition(StorageCategory.EXTERNAL_REFERENCES, "External References", StorageSafety.EXTERNAL, "Referenced files outside MMO Video Studio-managed storage."),
}


def definition(category: StorageCategory | str) -> CategoryDefinition:
    key = category if isinstance(category, StorageCategory) else StorageCategory(str(category))
    return CATEGORY_DEFINITIONS[key]


def cache_categories() -> tuple[StorageCategory, ...]:
    return tuple(item.category for item in CATEGORY_DEFINITIONS.values() if item.cache)
