from __future__ import annotations
from sqlite3 import Connection

def migrate(connection:Connection)->None:
    connection.executescript("""
    CREATE TABLE IF NOT EXISTS assets(
      id TEXT PRIMARY KEY,name TEXT NOT NULL,type TEXT NOT NULL,subtype TEXT NOT NULL DEFAULT 'general',
      file_path TEXT NOT NULL DEFAULT '',managed INTEGER NOT NULL DEFAULT 1,relative_path TEXT NOT NULL DEFAULT '',thumbnail_path TEXT NOT NULL DEFAULT '',
      duration_ms INTEGER,width INTEGER,height INTEGER,fps REAL,video_codec TEXT NOT NULL DEFAULT '',audio_codec TEXT NOT NULL DEFAULT '',sample_rate INTEGER,channels INTEGER,
      file_size INTEGER NOT NULL DEFAULT 0,mime_type TEXT NOT NULL DEFAULT '',extension TEXT NOT NULL DEFAULT '',fingerprint TEXT NOT NULL DEFAULT '',fingerprint_kind TEXT NOT NULL DEFAULT 'sha256',source_mtime_ns INTEGER NOT NULL DEFAULT 0,original_filename TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL,updated_at TEXT NOT NULL,last_used_at TEXT NOT NULL DEFAULT '',favorite INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'ready',notes TEXT NOT NULL DEFAULT '',spoken_language TEXT NOT NULL DEFAULT '',metadata_json TEXT NOT NULL DEFAULT '{}'
    );
    CREATE INDEX IF NOT EXISTS idx_assets_type_subtype ON assets(type,subtype);
    CREATE INDEX IF NOT EXISTS idx_assets_recent ON assets(created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_assets_used ON assets(last_used_at DESC);
    CREATE INDEX IF NOT EXISTS idx_assets_fingerprint ON assets(fingerprint,file_size);
    CREATE INDEX IF NOT EXISTS idx_assets_status ON assets(status);

    CREATE TABLE IF NOT EXISTS asset_collections(id TEXT PRIMARY KEY,name TEXT NOT NULL COLLATE NOCASE,description TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,updated_at TEXT NOT NULL,metadata_json TEXT NOT NULL DEFAULT '{}');
    CREATE UNIQUE INDEX IF NOT EXISTS idx_asset_collections_name ON asset_collections(name COLLATE NOCASE);
    CREATE TABLE IF NOT EXISTS asset_collection_items(collection_id TEXT NOT NULL,asset_id TEXT NOT NULL,PRIMARY KEY(collection_id,asset_id),FOREIGN KEY(collection_id) REFERENCES asset_collections(id) ON DELETE CASCADE,FOREIGN KEY(asset_id) REFERENCES assets(id) ON DELETE CASCADE);

    CREATE TABLE IF NOT EXISTS asset_tags(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL UNIQUE COLLATE NOCASE,normalized_name TEXT NOT NULL UNIQUE);
    CREATE TABLE IF NOT EXISTS asset_tag_items(tag_id INTEGER NOT NULL,asset_id TEXT NOT NULL,PRIMARY KEY(tag_id,asset_id),FOREIGN KEY(tag_id) REFERENCES asset_tags(id) ON DELETE CASCADE,FOREIGN KEY(asset_id) REFERENCES assets(id) ON DELETE CASCADE);
    CREATE INDEX IF NOT EXISTS idx_asset_tags_normalized ON asset_tags(normalized_name);

    CREATE TABLE IF NOT EXISTS asset_usage(id TEXT PRIMARY KEY,asset_id TEXT NOT NULL,project_id TEXT NOT NULL,project_media_id TEXT NOT NULL,used_at TEXT NOT NULL,usage_type TEXT NOT NULL DEFAULT 'other',metadata_json TEXT NOT NULL DEFAULT '{}',FOREIGN KEY(asset_id) REFERENCES assets(id) ON DELETE CASCADE,FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,FOREIGN KEY(project_media_id) REFERENCES media_assets(id) ON DELETE CASCADE);
    CREATE UNIQUE INDEX IF NOT EXISTS idx_asset_usage_media ON asset_usage(project_media_id);
    CREATE INDEX IF NOT EXISTS idx_asset_usage_asset ON asset_usage(asset_id,used_at DESC);
    CREATE INDEX IF NOT EXISTS idx_asset_usage_project ON asset_usage(project_id);

    CREATE TABLE IF NOT EXISTS asset_licenses(asset_id TEXT PRIMARY KEY,rights_status TEXT NOT NULL DEFAULT 'unknown',source_url TEXT NOT NULL DEFAULT '',license_name TEXT NOT NULL DEFAULT '',notes TEXT NOT NULL DEFAULT '',attribution_required INTEGER NOT NULL DEFAULT 0,attribution_text TEXT NOT NULL DEFAULT '',metadata_json TEXT NOT NULL DEFAULT '{}',FOREIGN KEY(asset_id) REFERENCES assets(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS asset_library_settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
    """)
