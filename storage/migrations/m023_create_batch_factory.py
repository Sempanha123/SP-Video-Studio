from __future__ import annotations
from sqlite3 import Connection


def migrate(connection: Connection) -> None:
    connection.executescript("""
    CREATE TABLE IF NOT EXISTS batches(
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      template_id TEXT NOT NULL,
      status TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      started_at TEXT NOT NULL DEFAULT '',
      completed_at TEXT NOT NULL DEFAULT '',
      input_source_type TEXT NOT NULL DEFAULT 'manual',
      input_source_path TEXT NOT NULL DEFAULT '',
      settings_json TEXT NOT NULL DEFAULT '{}',
      output_directory TEXT NOT NULL,
      total_items INTEGER NOT NULL DEFAULT 0,
      completed_items INTEGER NOT NULL DEFAULT 0,
      failed_items INTEGER NOT NULL DEFAULT 0,
      cancelled_items INTEGER NOT NULL DEFAULT 0,
      template_snapshot_json TEXT NOT NULL DEFAULT '{}',
      input_snapshot_json TEXT NOT NULL DEFAULT '[]',
      metadata_json TEXT NOT NULL DEFAULT '{}',
      scheduler_owner TEXT NOT NULL DEFAULT '',
      scheduler_heartbeat_at TEXT NOT NULL DEFAULT '',
      pause_reason TEXT NOT NULL DEFAULT ''
    );
    CREATE INDEX IF NOT EXISTS idx_batches_updated ON batches(updated_at DESC);
    CREATE INDEX IF NOT EXISTS idx_batches_status ON batches(status,updated_at DESC);

    CREATE TABLE IF NOT EXISTS batch_items(
      id TEXT PRIMARY KEY,
      batch_id TEXT NOT NULL,
      row_index INTEGER NOT NULL,
      item_key TEXT NOT NULL,
      status TEXT NOT NULL,
      current_stage TEXT NOT NULL,
      progress REAL NOT NULL DEFAULT 0,
      project_id TEXT NOT NULL DEFAULT '',
      variant_key TEXT NOT NULL DEFAULT '',
      output_path TEXT NOT NULL DEFAULT '',
      error_code TEXT NOT NULL DEFAULT '',
      error_message TEXT NOT NULL DEFAULT '',
      attempt_count INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      started_at TEXT NOT NULL DEFAULT '',
      completed_at TEXT NOT NULL DEFAULT '',
      input_data_json TEXT NOT NULL DEFAULT '{}',
      resolved_data_json TEXT NOT NULL DEFAULT '{}',
      metadata_json TEXT NOT NULL DEFAULT '{}',
      fingerprint TEXT NOT NULL DEFAULT '',
      FOREIGN KEY(batch_id) REFERENCES batches(id) ON DELETE CASCADE,
      UNIQUE(batch_id,item_key)
    );
    CREATE INDEX IF NOT EXISTS idx_batch_items_queue ON batch_items(batch_id,status,row_index,item_key);
    CREATE INDEX IF NOT EXISTS idx_batch_items_stage ON batch_items(batch_id,current_stage,status);
    CREATE INDEX IF NOT EXISTS idx_batch_items_project ON batch_items(project_id);

    CREATE TABLE IF NOT EXISTS batch_mappings(
      id TEXT PRIMARY KEY,
      batch_id TEXT NOT NULL,
      target TEXT NOT NULL,
      kind TEXT NOT NULL,
      source TEXT NOT NULL DEFAULT '',
      value_json TEXT NOT NULL DEFAULT '""',
      required INTEGER NOT NULL DEFAULT 0,
      default_json TEXT NOT NULL DEFAULT '""',
      transforms_json TEXT NOT NULL DEFAULT '[]',
      metadata_json TEXT NOT NULL DEFAULT '{}',
      FOREIGN KEY(batch_id) REFERENCES batches(id) ON DELETE CASCADE,
      UNIQUE(batch_id,target)
    );
    CREATE INDEX IF NOT EXISTS idx_batch_mappings_batch ON batch_mappings(batch_id,target);

    CREATE TABLE IF NOT EXISTS batch_variants(
      id TEXT PRIMARY KEY,
      batch_id TEXT NOT NULL UNIQUE,
      config_json TEXT NOT NULL DEFAULT '{}',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      FOREIGN KEY(batch_id) REFERENCES batches(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS batch_stage_state(
      item_id TEXT NOT NULL,
      stage TEXT NOT NULL,
      status TEXT NOT NULL,
      progress REAL NOT NULL DEFAULT 0,
      started_at TEXT NOT NULL DEFAULT '',
      completed_at TEXT NOT NULL DEFAULT '',
      fingerprint TEXT NOT NULL DEFAULT '',
      error_code TEXT NOT NULL DEFAULT '',
      error_message TEXT NOT NULL DEFAULT '',
      output_reference TEXT NOT NULL DEFAULT '',
      attempt_count INTEGER NOT NULL DEFAULT 0,
      metadata_json TEXT NOT NULL DEFAULT '{}',
      PRIMARY KEY(item_id,stage),
      FOREIGN KEY(item_id) REFERENCES batch_items(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_batch_stage_status ON batch_stage_state(stage,status);
    """)
