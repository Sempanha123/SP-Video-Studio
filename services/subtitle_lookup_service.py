from __future__ import annotations

from bisect import bisect_right
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class _CueIndex:
    starts: list[int]
    cues: list[Any]
    version: object


@dataclass(frozen=True, slots=True)
class _CueRange:
    cue_id: str
    start_ms: int
    end_ms: int


class SubtitleLookupService:
    """Indexed active-cue lookup for playback instead of full-list scans.

    The repository-assisted path deliberately indexes only id/start/end rows.
    Full cue text/word timing is loaded lazily for the active cue and held in a
    small bounded cache, avoiding the old N+1 word load for 1,000+ cue tracks.
    """
    def __init__(self, max_tracks: int = 32, max_active_cues: int = 96):
        self.max_tracks = max(4, int(max_tracks))
        self.max_active_cues = max(16, int(max_active_cues))
        self._indexes: dict[str, _CueIndex] = {}
        self._order: list[str] = []
        self._cue_cache: OrderedDict[tuple[str, str, str], Any] = OrderedDict()

    def build(self, track_id: str, cues: list[Any], version: object = None) -> None:
        ordered = sorted(cues, key=lambda x: (self._start(x), self._end(x)))
        self._store_index(str(track_id), ordered, version)

    def build_repository(self, repository, track_id: str, version: object = None) -> None:
        """Build a lightweight timing index in one SQL query when available."""
        database = getattr(repository, "database", None)
        if database is None:
            self.build(track_id, repository.cues(track_id), version)
            return
        with database.connect() as connection:
            rows = connection.execute(
                "SELECT id,start_ms,end_ms FROM subtitle_cues WHERE track_id=? ORDER BY start_ms,end_ms,id",
                (str(track_id),),
            ).fetchall()
        ranges = [_CueRange(str(row["id"]), int(row["start_ms"]), int(row["end_ms"])) for row in rows]
        self._store_index(str(track_id), ranges, version)

    def active(self, track_id: str, time_ms: int) -> list[Any]:
        index = self._indexes.get(str(track_id))
        if not index:
            return []
        value = int(time_ms)
        pos = bisect_right(index.starts, value)
        # Subtitle overlaps are normally sparse. Walk backwards only while end may overlap.
        out = []
        for i in range(pos - 1, -1, -1):
            cue = index.cues[i]
            start = self._start(cue); end = self._end(cue)
            if end <= value:
                if value - end > 10_000:
                    break
                continue
            if start <= value < end:
                out.append(cue)
        out.reverse()
        return out

    def active_repository(self, repository, track_id: str, time_ms: int, version: object = None) -> list[Any]:
        key = str(track_id)
        index = self._indexes.get(key)
        if index is None or index.version != version:
            self.build_repository(repository, key, version)
        ranges = self.active(key, time_ms)
        result = []
        for item in ranges:
            cue_id = str(getattr(item, "cue_id", "") or getattr(item, "id", "") or "")
            if not cue_id:
                result.append(item); continue
            cache_key = (key, str(version), cue_id)
            cue = self._cue_cache.get(cache_key)
            if cue is None:
                cue = repository.cue(cue_id)
                if cue is None:
                    continue
                self._cue_cache[cache_key] = cue
                while len(self._cue_cache) > self.max_active_cues:
                    self._cue_cache.popitem(last=False)
            else:
                self._cue_cache.move_to_end(cache_key)
            result.append(cue)
        return result

    def invalidate(self, track_id: str) -> None:
        key = str(track_id)
        self._indexes.pop(key, None)
        try:self._order.remove(key)
        except ValueError:pass
        for cache_key in [x for x in self._cue_cache if x[0] == key]:
            self._cue_cache.pop(cache_key, None)

    def _store_index(self, track_id: str, cues: list[Any], version: object) -> None:
        starts = [self._start(x) for x in cues]
        self._indexes[track_id] = _CueIndex(starts, cues, version)
        if track_id in self._order:
            self._order.remove(track_id)
        self._order.append(track_id)
        while len(self._order) > self.max_tracks:
            old = self._order.pop(0); self._indexes.pop(old, None)
            for cache_key in [x for x in self._cue_cache if x[0] == old]:
                self._cue_cache.pop(cache_key, None)

    @staticmethod
    def _start(cue: Any) -> int:
        if isinstance(cue, dict): return int(cue.get("startMs", cue.get("start_ms", 0)) or 0)
        return int(getattr(cue, "start_ms", 0) or 0)

    @staticmethod
    def _end(cue: Any) -> int:
        if isinstance(cue, dict): return int(cue.get("endMs", cue.get("end_ms", 0)) or 0)
        return int(getattr(cue, "end_ms", 0) or 0)
