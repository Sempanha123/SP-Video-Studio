from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class StorageSafety(str,Enum):SAFE_TO_CLEAR='safe_to_clear';REGENERATABLE='regeneratable';PROTECTED='protected';USER_DATA='user_data';EXTERNAL='external'
class StorageCategory(str,Enum):
    PROJECT_DATA='project_data';PROJECT_MEDIA='project_media';GENERATED_AUDIO='generated_audio';AUDIO_WAVEFORM_CACHE='audio_waveform_cache';PREVIEW_CACHE='preview_cache';THUMBNAIL_CACHE='thumbnail_cache';RENDER_TEMP='render_temp';TRANSCRIPTION_TEMP='transcription_temp';TRANSLATION_CACHE='translation_cache';UPDATE_TEMP='update_temp';ASSET_LIBRARY='asset_library';ASSET_THUMBNAIL_CACHE='asset_thumbnail_cache';TEMPLATE_CACHE='template_cache';BATCH_INTERMEDIATE='batch_intermediate';RECOVERY_DATA='recovery_data';MIGRATION_BACKUPS='migration_backups';AI_MODELS='ai_models';FINAL_EXPORTS='final_exports';LOGS='logs';EXTERNAL_REFERENCES='external_references'
@dataclass(frozen=True,slots=True)
class CategoryDefinition:category:StorageCategory;label:str;safety:StorageSafety;description:str;cache:bool=False
CATEGORY_DEFINITIONS={
StorageCategory.PROJECT_DATA:CategoryDefinition(StorageCategory.PROJECT_DATA,'Project Data',StorageSafety.USER_DATA,'Scripts, scenes, timelines, subtitles and project databases.'),
StorageCategory.PROJECT_MEDIA:CategoryDefinition(StorageCategory.PROJECT_MEDIA,'Project Media',StorageSafety.USER_DATA,'Project-owned source media copies.'),
StorageCategory.GENERATED_AUDIO:CategoryDefinition(StorageCategory.GENERATED_AUDIO,'Generated Audio',StorageSafety.REGENERATABLE,'Unreferenced generated speech may be rebuilt; active project audio is protected.',True),
StorageCategory.AUDIO_WAVEFORM_CACHE:CategoryDefinition(StorageCategory.AUDIO_WAVEFORM_CACHE,'Audio Waveforms',StorageSafety.SAFE_TO_CLEAR,'Downsampled waveform peak summaries; regenerated on demand.',True),
StorageCategory.PREVIEW_CACHE:CategoryDefinition(StorageCategory.PREVIEW_CACHE,'Preview Cache',StorageSafety.SAFE_TO_CLEAR,'Low-resolution composition and playback previews.',True),
StorageCategory.THUMBNAIL_CACHE:CategoryDefinition(StorageCategory.THUMBNAIL_CACHE,'Thumbnail Cache',StorageSafety.SAFE_TO_CLEAR,'Regeneratable project and media thumbnails.',True),
StorageCategory.RENDER_TEMP:CategoryDefinition(StorageCategory.RENDER_TEMP,'Render Temporary Files',StorageSafety.SAFE_TO_CLEAR,'Intermediate render files not owned by active jobs.',True),
StorageCategory.TRANSCRIPTION_TEMP:CategoryDefinition(StorageCategory.TRANSCRIPTION_TEMP,'Transcription Temporary Files',StorageSafety.SAFE_TO_CLEAR,'Temporary extracted audio and speech-recognition working files.',True),
StorageCategory.TRANSLATION_CACHE:CategoryDefinition(StorageCategory.TRANSLATION_CACHE,'Translation Cache',StorageSafety.SAFE_TO_CLEAR,'Reproducible provider/local translation response cache.',True),
StorageCategory.UPDATE_TEMP:CategoryDefinition(StorageCategory.UPDATE_TEMP,'Update Temporary Files',StorageSafety.SAFE_TO_CLEAR,'Incomplete or superseded validated-update staging files; active update files are excluded by the update service.',True),
StorageCategory.ASSET_LIBRARY:CategoryDefinition(StorageCategory.ASSET_LIBRARY,'Asset Library',StorageSafety.USER_DATA,'Managed reusable source assets.'),
StorageCategory.ASSET_THUMBNAIL_CACHE:CategoryDefinition(StorageCategory.ASSET_THUMBNAIL_CACHE,'Asset Thumbnail Cache',StorageSafety.SAFE_TO_CLEAR,'Regeneratable Asset Library thumbnails.',True),
StorageCategory.TEMPLATE_CACHE:CategoryDefinition(StorageCategory.TEMPLATE_CACHE,'Template Cache',StorageSafety.SAFE_TO_CLEAR,'Generated template previews and import staging.',True),
StorageCategory.BATCH_INTERMEDIATE:CategoryDefinition(StorageCategory.BATCH_INTERMEDIATE,'Batch Intermediate Data',StorageSafety.SAFE_TO_CLEAR,'Temporary Batch Factory working files, not persistent Batch projects.',True),
StorageCategory.RECOVERY_DATA:CategoryDefinition(StorageCategory.RECOVERY_DATA,'Recovery Data',StorageSafety.PROTECTED,'Recovery snapshots managed by recovery retention rules.'),
StorageCategory.MIGRATION_BACKUPS:CategoryDefinition(StorageCategory.MIGRATION_BACKUPS,'Migration Backups',StorageSafety.PROTECTED,'Database/project metadata backups retained until migrations are verified.'),
StorageCategory.AI_MODELS:CategoryDefinition(StorageCategory.AI_MODELS,'AI Models',StorageSafety.PROTECTED,'Installed application-owned AI models; managed by Model Manager.'),
StorageCategory.FINAL_EXPORTS:CategoryDefinition(StorageCategory.FINAL_EXPORTS,'Final Exports',StorageSafety.USER_DATA,'Finished user outputs; never removed by cache cleanup.'),
StorageCategory.LOGS:CategoryDefinition(StorageCategory.LOGS,'Logs',StorageSafety.SAFE_TO_CLEAR,'Old application logs; the current active log is excluded.',True),
StorageCategory.EXTERNAL_REFERENCES:CategoryDefinition(StorageCategory.EXTERNAL_REFERENCES,'External References',StorageSafety.EXTERNAL,'Referenced files outside SP Video Studio-managed storage.'),}
def definition(category:StorageCategory|str)->CategoryDefinition:return CATEGORY_DEFINITIONS[category if isinstance(category,StorageCategory) else StorageCategory(str(category))]
def cache_categories()->tuple[StorageCategory,...]:return tuple(x.category for x in CATEGORY_DEFINITIONS.values() if x.cache)
