from __future__ import annotations
from sqlite3 import Connection


def _columns(connection:Connection,name:str)->set[str]:
    return {str(r[1]) for r in connection.execute(f"PRAGMA table_info({name})").fetchall()}


def migrate(connection:Connection)->None:
    indexes=(
        ("assets","idx_assets_created_perf",("created_at","id"),"created_at DESC,id"),
        ("assets","idx_assets_last_used_perf",("last_used_at","created_at"),"last_used_at DESC,created_at DESC"),
        ("asset_usage","idx_asset_usage_asset_project_perf",("asset_id","project_id"),"asset_id,project_id"),
        ("batch_items","idx_batch_items_batch_row_perf",("batch_id","row_index","item_key"),"batch_id,row_index,item_key"),
        ("batch_items","idx_batch_items_batch_status_perf",("batch_id","status","row_index"),"batch_id,status,row_index"),
        ("subtitle_cues","idx_subtitle_cues_playback_perf",("track_id","start_ms","end_ms"),"track_id,start_ms,end_ms"),
        ("subtitle_words","idx_subtitle_words_cue_order_perf",("cue_id","word_order"),"cue_id,word_order"),
        ("scenes","idx_scenes_project_order_perf",("project_id","scene_order"),"project_id,scene_order"),
        ("speech_blocks","idx_speech_blocks_section_order_perf",("script_section_id","block_order"),"script_section_id,block_order"),
        ("transcript_segments","idx_transcript_segments_track_time_perf",("transcript_id","start_ms","end_ms"),"transcript_id,start_ms,end_ms"),
    )
    for table,name,required,sql_columns in indexes:
        cols=_columns(connection,table)
        if cols and set(required).issubset(cols):
            connection.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table}({sql_columns})")
