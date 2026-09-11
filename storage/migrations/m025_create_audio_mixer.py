from __future__ import annotations
from sqlite3 import Connection


def migrate(connection: Connection) -> None:
    connection.executescript('''
    CREATE TABLE IF NOT EXISTS audio_buses(
      id TEXT PRIMARY KEY,
      project_id TEXT NOT NULL,
      name TEXT NOT NULL,
      role TEXT NOT NULL,
      bus_order INTEGER NOT NULL DEFAULT 0,
      gain_db REAL NOT NULL DEFAULT 0,
      muted INTEGER NOT NULL DEFAULT 0,
      metadata_json TEXT NOT NULL DEFAULT '{}',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_audio_buses_project ON audio_buses(project_id,bus_order);

    CREATE TABLE IF NOT EXISTS audio_tracks(
      id TEXT PRIMARY KEY,
      project_id TEXT NOT NULL,
      name TEXT NOT NULL,
      role TEXT NOT NULL,
      track_order INTEGER NOT NULL DEFAULT 0,
      gain_db REAL NOT NULL DEFAULT 0,
      pan REAL NOT NULL DEFAULT 0,
      muted INTEGER NOT NULL DEFAULT 0,
      solo INTEGER NOT NULL DEFAULT 0,
      enabled INTEGER NOT NULL DEFAULT 1,
      bus_id TEXT,
      metadata_json TEXT NOT NULL DEFAULT '{}',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
      FOREIGN KEY(bus_id) REFERENCES audio_buses(id) ON DELETE SET NULL
    );
    CREATE INDEX IF NOT EXISTS idx_audio_tracks_project ON audio_tracks(project_id,track_order);
    CREATE INDEX IF NOT EXISTS idx_audio_tracks_role ON audio_tracks(project_id,role);

    CREATE TABLE IF NOT EXISTS audio_clip_mix(
      project_id TEXT NOT NULL,
      clip_id TEXT NOT NULL,
      source_kind TEXT NOT NULL DEFAULT 'timeline',
      track_id TEXT,
      gain_db REAL NOT NULL DEFAULT 0,
      pan REAL NOT NULL DEFAULT 0,
      fade_in_ms INTEGER NOT NULL DEFAULT 0,
      fade_out_ms INTEGER NOT NULL DEFAULT 0,
      muted INTEGER NOT NULL DEFAULT 0,
      effects_json TEXT NOT NULL DEFAULT '[]',
      metadata_json TEXT NOT NULL DEFAULT '{}',
      updated_at TEXT NOT NULL,
      PRIMARY KEY(project_id,clip_id),
      FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
      FOREIGN KEY(track_id) REFERENCES audio_tracks(id) ON DELETE SET NULL
    );
    CREATE INDEX IF NOT EXISTS idx_audio_clip_mix_track ON audio_clip_mix(project_id,track_id);

    CREATE TABLE IF NOT EXISTS audio_effects(
      id TEXT PRIMARY KEY,
      project_id TEXT NOT NULL,
      owner_type TEXT NOT NULL,
      owner_id TEXT NOT NULL,
      effect_type TEXT NOT NULL,
      effect_order INTEGER NOT NULL DEFAULT 0,
      enabled INTEGER NOT NULL DEFAULT 1,
      settings_json TEXT NOT NULL DEFAULT '{}',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_audio_effects_owner ON audio_effects(project_id,owner_type,owner_id,effect_order);

    CREATE TABLE IF NOT EXISTS audio_ducking_rules(
      id TEXT PRIMARY KEY,
      project_id TEXT NOT NULL,
      trigger_kind TEXT NOT NULL,
      trigger_id TEXT NOT NULL,
      target_kind TEXT NOT NULL,
      target_id TEXT NOT NULL,
      duck_amount_db REAL NOT NULL DEFAULT -12,
      attack_ms INTEGER NOT NULL DEFAULT 120,
      release_ms INTEGER NOT NULL DEFAULT 220,
      threshold REAL,
      enabled INTEGER NOT NULL DEFAULT 1,
      metadata_json TEXT NOT NULL DEFAULT '{}',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_audio_duck_project ON audio_ducking_rules(project_id,enabled);

    CREATE TABLE IF NOT EXISTS audio_mix_settings(
      project_id TEXT PRIMARY KEY,
      master_gain_db REAL NOT NULL DEFAULT 0,
      limiter_enabled INTEGER NOT NULL DEFAULT 1,
      limiter_limit REAL NOT NULL DEFAULT 0.95,
      normalization_enabled INTEGER NOT NULL DEFAULT 0,
      normalization_target_lufs REAL NOT NULL DEFAULT -16,
      preset TEXT NOT NULL DEFAULT 'custom',
      metadata_json TEXT NOT NULL DEFAULT '{}',
      updated_at TEXT NOT NULL,
      FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
    );
    ''')
