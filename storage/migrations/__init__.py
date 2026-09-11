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
)
