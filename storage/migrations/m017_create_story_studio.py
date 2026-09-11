from __future__ import annotations
from sqlite3 import Connection

def migrate(connection: Connection) -> None:
    connection.executescript('''
    CREATE TABLE IF NOT EXISTS story_projects(
      project_id TEXT PRIMARY KEY, title TEXT NOT NULL DEFAULT '', idea TEXT NOT NULL DEFAULT '', story_type TEXT NOT NULL DEFAULT 'short_story',
      language TEXT NOT NULL DEFAULT 'en', target_duration_ms INTEGER NOT NULL DEFAULT 60000, audience TEXT NOT NULL DEFAULT 'general', tone TEXT NOT NULL DEFAULT 'warm',
      pace TEXT NOT NULL DEFAULT 'balanced', status TEXT NOT NULL DEFAULT 'draft', narrator_voice_id TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
      source_fingerprint TEXT NOT NULL DEFAULT '', metadata_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS story_outlines(
      id TEXT PRIMARY KEY, project_id TEXT NOT NULL, title TEXT NOT NULL DEFAULT 'Story Outline', summary TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'draft',
      outline_version INTEGER NOT NULL DEFAULT 1, source_fingerprint TEXT NOT NULL DEFAULT '', metadata_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_story_outlines_project ON story_outlines(project_id,updated_at);
    CREATE TABLE IF NOT EXISTS story_characters(
      id TEXT PRIMARY KEY, project_id TEXT NOT NULL, name TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'other', description TEXT NOT NULL DEFAULT '', voice_id TEXT NOT NULL DEFAULT '',
      notes TEXT NOT NULL DEFAULT '', metadata_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_story_characters_project ON story_characters(project_id,updated_at);
    CREATE TABLE IF NOT EXISTS story_beats(
      id TEXT PRIMARY KEY, outline_id TEXT NOT NULL, beat_order INTEGER NOT NULL, beat_type TEXT NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
      target_duration_ms INTEGER NOT NULL DEFAULT 5000, emotion TEXT NOT NULL DEFAULT 'neutral', visual_direction TEXT NOT NULL DEFAULT '', script_section_id TEXT,
      locked INTEGER NOT NULL DEFAULT 0, user_modified INTEGER NOT NULL DEFAULT 0, chapter_title TEXT NOT NULL DEFAULT '', character_id TEXT, voice_override_id TEXT NOT NULL DEFAULT '',
      notes TEXT NOT NULL DEFAULT '', metadata_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      FOREIGN KEY(outline_id) REFERENCES story_outlines(id) ON DELETE CASCADE,
      FOREIGN KEY(script_section_id) REFERENCES script_sections(id) ON DELETE SET NULL,
      FOREIGN KEY(character_id) REFERENCES story_characters(id) ON DELETE SET NULL
    );
    CREATE INDEX IF NOT EXISTS idx_story_beats_outline_order ON story_beats(outline_id,beat_order);
    CREATE TABLE IF NOT EXISTS story_mappings(
      id TEXT PRIMARY KEY, project_id TEXT NOT NULL, beat_id TEXT NOT NULL, mapping_type TEXT NOT NULL, target_id TEXT NOT NULL,
      source_hash TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'current', metadata_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
      FOREIGN KEY(beat_id) REFERENCES story_beats(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_story_mappings_project_beat ON story_mappings(project_id,beat_id,mapping_type);
    CREATE INDEX IF NOT EXISTS idx_story_mappings_target ON story_mappings(project_id,mapping_type,target_id);
    ''')
