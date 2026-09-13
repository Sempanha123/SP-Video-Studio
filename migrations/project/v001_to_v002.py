from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from datetime import datetime, timezone

from domain.migration_result import MigrationWarning

MIGRATION_ID = "project_001_to_002"

_LANGUAGE_ALIASES = {
    "english": "en", "en": "en", "en-us": "en", "en_us": "en", "en-gb": "en", "en_gb": "en",
    "khmer": "km", "cambodian": "km", "km": "km", "km-kh": "km", "km_kh": "km",
    "thai": "th", "th": "th", "th-th": "th", "th_th": "th",
    "vietnamese": "vi", "viet": "vi", "vi": "vi", "vi-vn": "vi", "vi_vn": "vi",
    "auto": "auto",
}


def canonical_language(value: object) -> tuple[str, str | None]:
    raw = str(value or "").strip()
    if not raw:
        return "en", None
    canonical = _LANGUAGE_ALIASES.get(raw.casefold())
    return (canonical, None) if canonical else (raw, raw)


def _tables(connection: sqlite3.Connection) -> set[str]:
    return {str(row[0]) for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}


def _merge_metadata(raw: object, **updates: object) -> str:
    try:
        value = json.loads(str(raw or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError):
        value = {}
    if not isinstance(value, dict):
        value = {"legacyValue": value}
    value.update(updates)
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _linear_to_db(value: object) -> float:
    try:
        level = float(value)
    except (TypeError, ValueError):
        return 0.0
    if level <= 0:
        return -60.0
    return max(-60.0, min(12.0, 20.0 * math.log10(level)))


def _normalize_language_table(connection: sqlite3.Connection, project_id: str, table: str, column: str, warnings: list[MigrationWarning]) -> None:
    tables = _tables(connection)
    if table not in tables or column not in _columns(connection, table):
        return
    cols = _columns(connection, table)
    project_column = "project_id" if "project_id" in cols else None
    if project_column is None:
        return
    rows = connection.execute(
        f"SELECT rowid, {column}" + (", metadata_json" if "metadata_json" in cols else "") + f" FROM {table} WHERE project_id = ?",
        (project_id,),
    ).fetchall()
    for row in rows:
        canonical, unknown = canonical_language(row[1])
        if unknown:
            warnings.append(MigrationWarning("unknown_language", f"Preserved unknown language value in {table}.{column}."))
            if "metadata_json" in cols:
                connection.execute(
                    f"UPDATE {table} SET metadata_json = ? WHERE rowid = ?",
                    (_merge_metadata(row[2], legacyLanguage=unknown), row[0]),
                )
            continue
        if canonical != str(row[1]):
            connection.execute(f"UPDATE {table} SET {column} = ? WHERE rowid = ?", (canonical, row[0]))



def _normalize_speech_blocks(connection: sqlite3.Connection, project_id: str, warnings: list[MigrationWarning]) -> None:
    tables = _tables(connection)
    if not {"speech_blocks", "script_sections", "scripts"}.issubset(tables):
        return
    rows = connection.execute(
        """SELECT sb.id,sb.language,sb.metadata_json FROM speech_blocks sb
           JOIN script_sections ss ON ss.id=sb.script_section_id JOIN scripts s ON s.id=ss.script_id
           WHERE s.project_id=?""", (project_id,)
    ).fetchall()
    for block_id, language, metadata_json in rows:
        canonical, unknown = canonical_language(language)
        if unknown:
            warnings.append(MigrationWarning("unknown_language", "Preserved unknown language value in speech_blocks.language."))
            connection.execute("UPDATE speech_blocks SET metadata_json=? WHERE id=?", (_merge_metadata(metadata_json, legacyLanguage=unknown), block_id))
        elif canonical != str(language):
            connection.execute("UPDATE speech_blocks SET language=? WHERE id=?", (canonical, block_id))

def _create_speech_blocks_from_sections(connection: sqlite3.Connection, project_id: str) -> int:
    tables = _tables(connection)
    if not {"scripts", "script_sections", "speech_blocks"}.issubset(tables):
        return 0
    rows = connection.execute(
        """
        SELECT ss.id, ss.section_order, ss.content, ss.created_at, ss.updated_at, s.language
        FROM script_sections ss
        JOIN scripts s ON s.id = ss.script_id
        WHERE s.project_id = ? AND TRIM(COALESCE(ss.content,'')) <> ''
        ORDER BY ss.section_order, ss.id
        """,
        (project_id,),
    ).fetchall()
    created = 0
    for section_id, order, content, created_at, updated_at, language in rows:
        exists = connection.execute("SELECT 1 FROM speech_blocks WHERE script_section_id = ? LIMIT 1", (section_id,)).fetchone()
        if exists:
            continue
        digest = hashlib.sha256(str(section_id).encode("utf-8")).hexdigest()[:24]
        block_id = f"legacy-speech-{digest}"
        canonical, _ = canonical_language(language)
        connection.execute(
            """
            INSERT OR IGNORE INTO speech_blocks(
              id, script_section_id, block_order, speaker_id, text, language,
              voice_override_id, speech_source_type, pause_before_ms, pause_after_ms,
              scene_id, start_offset_ms, audio_id, metadata_json, created_at, updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (block_id, section_id, 0, None, content, canonical if canonical != "auto" else "en", "", "tts", 0, 180, None, None, "",
             json.dumps({"migratedFrom": "script_section_content", "legacySectionOrder": int(order)}, sort_keys=True),
             created_at, updated_at),
        )
        created += 1
    return created


def _migrate_dub_mix(connection: sqlite3.Connection, project_id: str) -> int:
    tables = _tables(connection)
    if not {"dub_mix_settings", "audio_mix_settings", "audio_tracks"}.issubset(tables):
        return 0
    row = connection.execute("SELECT * FROM dub_mix_settings WHERE project_id = ?", (project_id,)).fetchone()
    if not row:
        return 0
    keys = [d[0] for d in connection.execute("SELECT * FROM dub_mix_settings WHERE 0").description or []]
    data = dict(zip(keys, row)) if keys else {}
    now = str(data.get("updated_at") or datetime.now(timezone.utc).isoformat())
    original = float(data.get("original_volume", 0.25) or 0.0)
    dub = float(data.get("dub_volume", 1.0) or 0.0)
    existing = connection.execute("SELECT 1 FROM audio_mix_settings WHERE project_id = ?", (project_id,)).fetchone()
    if not existing:
        connection.execute(
            """INSERT INTO audio_mix_settings(project_id,master_gain_db,limiter_enabled,limiter_limit,normalization_enabled,normalization_target_lufs,preset,metadata_json,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (project_id, 0.0, 1, 0.95, 0, -16.0, "custom", json.dumps({"legacyDubMix": data}, ensure_ascii=False, sort_keys=True), now),
        )
    tracks = (
        (f"phase38-{project_id}-source", "Source Audio", "source_audio", 0, _linear_to_db(original)),
        (f"phase38-{project_id}-dub", "Dub", "dub", 1, _linear_to_db(dub)),
    )
    for track_id, name, role, order, gain in tracks:
        if connection.execute("SELECT 1 FROM audio_tracks WHERE id = ?", (track_id,)).fetchone():
            continue
        connection.execute(
            """INSERT INTO audio_tracks(id,project_id,name,role,track_order,gain_db,pan,muted,solo,enabled,bus_id,metadata_json,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (track_id, project_id, name, role, order, gain, 0.0, 0, 0, 1, None,
             json.dumps({"migratedFrom": "dub_mix_settings"}, sort_keys=True), now, now),
        )
    return 1


def _legacy_volume_values(metadata: dict[str, object]) -> dict[str, object]:
    values: dict[str, object] = {}
    settings = metadata.get("settings")
    candidates = [metadata, settings if isinstance(settings, dict) else {}]
    aliases = {
        "source_volume": "source_volume",
        "sourceVolume": "source_volume",
        "narration_volume": "narration_volume",
        "narrationVolume": "narration_volume",
    }
    for source in candidates:
        if not isinstance(source, dict):
            continue
        for raw_key, canonical in aliases.items():
            if raw_key in source and canonical not in values:
                values[canonical] = source[raw_key]
    return values


def _migrate_legacy_project_volumes(connection: sqlite3.Connection, project_id: str, metadata: dict[str, object]) -> int:
    values = _legacy_volume_values(metadata)
    if not values:
        return 0
    tables = _tables(connection)
    if not {"audio_tracks", "audio_mix_settings"}.issubset(tables):
        return 0

    now = datetime.now(timezone.utc).isoformat()
    existing_mix = connection.execute(
        "SELECT metadata_json FROM audio_mix_settings WHERE project_id = ?", (project_id,)
    ).fetchone()
    if existing_mix:
        merged = _merge_metadata(existing_mix[0], legacyVolumeSettings=values)
        connection.execute(
            "UPDATE audio_mix_settings SET metadata_json=?, updated_at=? WHERE project_id=?",
            (merged, now, project_id),
        )
    else:
        connection.execute(
            """INSERT INTO audio_mix_settings(
                 project_id,master_gain_db,limiter_enabled,limiter_limit,
                 normalization_enabled,normalization_target_lufs,preset,metadata_json,updated_at
               ) VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                project_id, 0.0, 1, 0.95, 0, -16.0, "custom",
                json.dumps({"legacyVolumeSettings": values}, ensure_ascii=False, sort_keys=True), now,
            ),
        )

    specs = []
    if "source_volume" in values:
        specs.append((f"phase38-{project_id}-legacy-source", "Source Audio", "source_audio", 20, values["source_volume"]))
    if "narration_volume" in values:
        specs.append((f"phase38-{project_id}-legacy-narration", "Narration", "narration", 21, values["narration_volume"]))
    created = 0
    for track_id, name, role, order, level in specs:
        exists = connection.execute(
            "SELECT 1 FROM audio_tracks WHERE id=? OR (project_id=? AND role=?) LIMIT 1",
            (track_id, project_id, role),
        ).fetchone()
        if exists:
            continue
        connection.execute(
            """INSERT INTO audio_tracks(
                 id,project_id,name,role,track_order,gain_db,pan,muted,solo,enabled,
                 bus_id,metadata_json,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                track_id, project_id, name, role, order, _linear_to_db(level), 0.0, 0, 0, 1, None,
                json.dumps({"migratedFrom": "legacy_project_volume"}, sort_keys=True), now, now,
            ),
        )
        created += 1
    return created


def migrate(connection: sqlite3.Connection, project_id: str, metadata: dict[str, object], warnings: list[MigrationWarning]) -> dict[str, object]:
    canonical, unknown = canonical_language(metadata.get("language", "en"))
    if unknown:
        metadata.setdefault("migration_metadata", {})
        bucket = metadata["migration_metadata"]
        if isinstance(bucket, dict):
            bucket["legacyLanguage"] = unknown
        warnings.append(MigrationWarning("unknown_project_language", "Unknown project language was preserved without guessing."))
    else:
        metadata["language"] = canonical
        connection.execute("UPDATE projects SET language = ? WHERE id = ?", (canonical, project_id))

    # Real historical language-bearing tables. Unknown values are preserved in metadata_json when available.
    for table, column in (
        ("scripts", "language"), ("speakers", "language"),
        ("transcripts", "language"), ("translations", "source_language"), ("translations", "target_language"),
        ("subtitle_tracks", "language"), ("dubbing_projects", "source_language"), ("dubbing_projects", "target_language"),
        ("short_projects", "language"),
    ):
        _normalize_language_table(connection, project_id, table, column, warnings)

    _normalize_speech_blocks(connection, project_id, warnings)
    speech_created = _create_speech_blocks_from_sections(connection, project_id)
    dub_migrated = _migrate_dub_mix(connection, project_id)
    legacy_volume_tracks = _migrate_legacy_project_volumes(connection, project_id, metadata)
    metadata["project_schema_version"] = 2
    metadata["version"] = 2
    return {"speechBlocksCreated": speech_created, "dubMixerMigrated": dub_migrated, "legacyVolumeTracksCreated": legacy_volume_tracks}
