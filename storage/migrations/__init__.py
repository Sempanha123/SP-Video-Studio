from __future__ import annotations

from dataclasses import dataclass
from sqlite3 import Connection
from collections.abc import Callable

from .m001_create_projects import migrate as create_projects
from .m002_create_media_assets import migrate as create_media_assets
from .m003_create_scripts import migrate as create_scripts
from .m004_create_model_installations import migrate as create_model_installations
from .m005_create_generated_audio import migrate as create_generated_audio
from .m006_create_voice_studio import migrate as create_voice_studio
from .m007_create_transcripts import migrate as create_transcripts
from .m008_create_translations import migrate as create_translations
from .m009_create_subtitles import migrate as create_subtitles
from .m010_create_scenes import migrate as create_scenes
from .m011_create_director import migrate as create_director
from .m012_create_rendering import migrate as create_rendering
from .m013_create_export_presets import migrate as create_export_presets
from .m014_create_timeline import migrate as create_timeline
from .m015_create_news_studio import migrate as create_news_studio
from .m016_create_news_visuals import migrate as create_news_visuals
from .m017_create_story_studio import migrate as create_story_studio
from .m018_create_dubbing import migrate as create_dubbing
from .m019_create_universal_video_studio import migrate as create_universal_video_studio
from .m020_create_shorts import migrate as create_shorts


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    apply: Callable[[Connection], None]


MIGRATIONS: tuple[Migration, ...] = (
    Migration(1, "create_projects", create_projects),
    Migration(2, "create_media_assets", create_media_assets),
    Migration(3, "create_scripts", create_scripts),
    Migration(4, "create_model_installations", create_model_installations),
    Migration(5, "create_generated_audio", create_generated_audio),
    Migration(6, "create_voice_studio", create_voice_studio),
    Migration(7, "create_transcripts", create_transcripts),
    Migration(8, "create_translations", create_translations),
    Migration(9, "create_subtitles", create_subtitles),
    Migration(10, "create_scenes", create_scenes),
    Migration(11, "create_director", create_director),
    Migration(12, "create_rendering", create_rendering),
    Migration(13, "create_export_presets", create_export_presets),
    Migration(14, "create_timeline", create_timeline),
    Migration(15, "create_news_studio", create_news_studio),
    Migration(16, "create_news_visuals", create_news_visuals),
    Migration(17, "create_story_studio", create_story_studio),
    Migration(18, "create_dubbing", create_dubbing),
    Migration(19, "create_universal_video_studio", create_universal_video_studio),
    Migration(20, "create_shorts", create_shorts),
)
