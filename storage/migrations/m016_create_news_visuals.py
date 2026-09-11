from __future__ import annotations
from sqlite3 import Connection

def migrate(connection:Connection)->None:
    connection.executescript('''
    CREATE TABLE IF NOT EXISTS news_visual_themes(
      id TEXT PRIMARY KEY, project_id TEXT NOT NULL, name TEXT NOT NULL, preset_id TEXT NOT NULL DEFAULT 'clean_news', active INTEGER NOT NULL DEFAULT 1,
      primary_color TEXT NOT NULL, secondary_color TEXT NOT NULL, accent_color TEXT NOT NULL, background_color TEXT NOT NULL, surface_color TEXT NOT NULL,
      text_primary TEXT NOT NULL, text_secondary TEXT NOT NULL, font_heading TEXT NOT NULL, font_body TEXT NOT NULL, font_numbers TEXT NOT NULL,
      corner_radius REAL NOT NULL DEFAULT 10, spacing_scale REAL NOT NULL DEFAULT 1, logo_media_id TEXT NOT NULL DEFAULT '', default_animation_style TEXT NOT NULL DEFAULT 'none',
      metadata_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_news_visual_theme_project ON news_visual_themes(project_id,active,updated_at);
    CREATE TABLE IF NOT EXISTS news_scene_layouts(
      id TEXT PRIMARY KEY, project_id TEXT NOT NULL, scene_id TEXT NOT NULL UNIQUE, preset_id TEXT NOT NULL, preset_version INTEGER NOT NULL DEFAULT 1,
      theme_id TEXT, status TEXT NOT NULL DEFAULT 'current', customized INTEGER NOT NULL DEFAULT 0, metadata_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE, FOREIGN KEY(scene_id) REFERENCES scenes(id) ON DELETE CASCADE,
      FOREIGN KEY(theme_id) REFERENCES news_visual_themes(id) ON DELETE SET NULL
    );
    CREATE INDEX IF NOT EXISTS idx_news_layout_project ON news_scene_layouts(project_id,scene_id);
    CREATE TABLE IF NOT EXISTS news_visual_elements(
      id TEXT PRIMARY KEY, project_id TEXT NOT NULL, scene_id TEXT NOT NULL, scene_overlay_id TEXT NOT NULL UNIQUE, graphic_type TEXT NOT NULL,
      claim_id TEXT, source_id TEXT, quote_type TEXT NOT NULL DEFAULT '', follow_theme INTEGER NOT NULL DEFAULT 1, status TEXT NOT NULL DEFAULT 'current', source_hash TEXT NOT NULL DEFAULT '',
      metadata_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE, FOREIGN KEY(scene_id) REFERENCES scenes(id) ON DELETE CASCADE,
      FOREIGN KEY(scene_overlay_id) REFERENCES scene_overlays(id) ON DELETE CASCADE, FOREIGN KEY(claim_id) REFERENCES news_claims(id) ON DELETE SET NULL,
      FOREIGN KEY(source_id) REFERENCES news_sources(id) ON DELETE SET NULL
    );
    CREATE INDEX IF NOT EXISTS idx_news_visual_element_project ON news_visual_elements(project_id,scene_id,status);
    ''')
