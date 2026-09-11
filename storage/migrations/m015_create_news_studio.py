from __future__ import annotations
from sqlite3 import Connection


def migrate(connection: Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS news_projects (
            project_id TEXT PRIMARY KEY,
            topic TEXT NOT NULL DEFAULT '',
            angle TEXT NOT NULL DEFAULT 'general_update',
            region TEXT NOT NULL DEFAULT '',
            language TEXT NOT NULL DEFAULT 'en',
            target_audience TEXT NOT NULL DEFAULT 'general',
            target_duration_ms INTEGER NOT NULL DEFAULT 60000,
            platform TEXT NOT NULL DEFAULT 'generic',
            status TEXT NOT NULL DEFAULT 'draft',
            source_fingerprint TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS news_sources (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            source_type TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            url TEXT NOT NULL DEFAULT '',
            publisher TEXT NOT NULL DEFAULT '',
            author TEXT NOT NULL DEFAULT '',
            published_at TEXT,
            accessed_at TEXT,
            language TEXT NOT NULL DEFAULT 'auto',
            status TEXT NOT NULL DEFAULT 'pending',
            source_path TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL DEFAULT 'other',
            notes TEXT NOT NULL DEFAULT '',
            latest_snapshot_id TEXT,
            source_updated INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_news_sources_project_status ON news_sources(project_id, status, updated_at);

        CREATE TABLE IF NOT EXISTS news_source_snapshots (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            retrieved_at TEXT NOT NULL,
            content_text TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            author TEXT NOT NULL DEFAULT '',
            published_at TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(source_id) REFERENCES news_sources(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_news_snapshots_source_time ON news_source_snapshots(source_id, retrieved_at);
        CREATE INDEX IF NOT EXISTS idx_news_snapshots_hash ON news_source_snapshots(content_hash);

        CREATE TABLE IF NOT EXISTS news_claims (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            text TEXT NOT NULL,
            claim_type TEXT NOT NULL DEFAULT 'fact',
            status TEXT NOT NULL DEFAULT 'candidate',
            importance TEXT NOT NULL DEFAULT 'supporting',
            uncertainty TEXT NOT NULL DEFAULT 'reported',
            user_modified INTEGER NOT NULL DEFAULT 0,
            locked INTEGER NOT NULL DEFAULT 0,
            notes TEXT NOT NULL DEFAULT '',
            quote_text TEXT NOT NULL DEFAULT '',
            speaker TEXT NOT NULL DEFAULT '',
            quote_kind TEXT NOT NULL DEFAULT '',
            original_quote TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_news_claims_project_status ON news_claims(project_id, status, updated_at);

        CREATE TABLE IF NOT EXISTS news_evidence (
            id TEXT PRIMARY KEY,
            claim_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            snapshot_id TEXT NOT NULL,
            evidence_text TEXT NOT NULL,
            source_start_offset INTEGER NOT NULL DEFAULT -1,
            source_end_offset INTEGER NOT NULL DEFAULT -1,
            evidence_type TEXT NOT NULL DEFAULT 'support',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY(claim_id) REFERENCES news_claims(id) ON DELETE CASCADE,
            FOREIGN KEY(source_id) REFERENCES news_sources(id) ON DELETE CASCADE,
            FOREIGN KEY(snapshot_id) REFERENCES news_source_snapshots(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_news_evidence_claim ON news_evidence(claim_id);
        CREATE INDEX IF NOT EXISTS idx_news_evidence_source ON news_evidence(source_id, snapshot_id);

        CREATE TABLE IF NOT EXISTS news_briefs (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT 'News Brief',
            summary TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'draft',
            source_fingerprint TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_news_briefs_project ON news_briefs(project_id, updated_at);

        CREATE TABLE IF NOT EXISTS news_brief_items (
            id TEXT PRIMARY KEY,
            brief_id TEXT NOT NULL,
            section_key TEXT NOT NULL,
            claim_id TEXT,
            editor_note TEXT NOT NULL DEFAULT '',
            item_order INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(brief_id) REFERENCES news_briefs(id) ON DELETE CASCADE,
            FOREIGN KEY(claim_id) REFERENCES news_claims(id) ON DELETE SET NULL
        );
        CREATE INDEX IF NOT EXISTS idx_news_brief_items_order ON news_brief_items(brief_id, section_key, item_order);

        CREATE TABLE IF NOT EXISTS news_script_mappings (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            script_id TEXT NOT NULL,
            script_section_id TEXT NOT NULL,
            sentence_key TEXT NOT NULL DEFAULT '',
            text_snapshot TEXT NOT NULL,
            claim_ids_json TEXT NOT NULL DEFAULT '[]',
            mapping_type TEXT NOT NULL DEFAULT 'factual',
            status TEXT NOT NULL DEFAULT 'grounded',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY(script_id) REFERENCES scripts(id) ON DELETE CASCADE,
            FOREIGN KEY(script_section_id) REFERENCES script_sections(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_news_script_mapping_project ON news_script_mappings(project_id, script_id, script_section_id);
        """
    )
