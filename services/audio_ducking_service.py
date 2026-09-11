from __future__ import annotations
import math
from domain.ducking_rule import DuckingRule


def db_to_linear(db: float) -> float:
    if db <= -60:
        return 0.0
    return 10.0 ** (float(db) / 20.0)


class AudioDuckingService:
    """Deterministic timing-based ducking; no realtime side-chain detector."""

    def trigger_regions(self, clips: list[dict], *, trigger_kind: str, trigger_id: str, tracks: dict[str, dict]) -> list[tuple[int, int]]:
        ids: set[str]
        if trigger_kind == "track":
            ids = {trigger_id}
        else:
            ids = {tid for tid, track in tracks.items() if str(track.get("busId") or "") == trigger_id}
        regions = []
        for clip in clips:
            if str(clip.get("trackId") or "") not in ids or bool(clip.get("muted", False)):
                continue
            start = max(0, int(clip.get("timelineStartMs", 0) or 0))
            end = start + max(0, int(clip.get("durationMs", 0) or 0))
            if end > start:
                regions.append((start, end))
        return self.merge_regions(regions)

    @staticmethod
    def merge_regions(regions: list[tuple[int, int]], gap_ms: int = 40) -> list[tuple[int, int]]:
        if not regions:
            return []
        rows = sorted(regions)
        out = [list(rows[0])]
        for start, end in rows[1:]:
            if start <= out[-1][1] + gap_ms:
                out[-1][1] = max(out[-1][1], end)
            else:
                out.append([start, end])
        return [(int(a), int(b)) for a, b in out]

    def volume_expression(self, rule: DuckingRule | dict, regions: list[tuple[int, int]]) -> str:
        if not regions:
            return "1"
        if isinstance(rule, dict):
            amount = float(rule.get("duckAmountDb", -12.0))
            attack = max(0, int(rule.get("attackMs", 120) or 0)) / 1000.0
            release = max(0, int(rule.get("releaseMs", 220) or 0)) / 1000.0
        else:
            amount = rule.duck_amount_db
            attack = rule.attack_ms / 1000.0
            release = rule.release_ms / 1000.0
        factor = db_to_linear(amount)
        # Piecewise timing envelope. The ramps are deterministic and derived from
        # clip regions, so the same project renders identically in Batch/final render.
        expr = "1"
        for start_ms, end_ms in reversed(regions):
            start = start_ms / 1000.0
            end = end_ms / 1000.0
            a0 = max(0.0, start - attack)
            r1 = end + release
            if attack > 0:
                attack_expr = f"(1-(1-{factor:.8f})*(t-{a0:.6f})/{attack:.6f})"
            else:
                attack_expr = f"{factor:.8f}"
            if release > 0:
                release_expr = f"({factor:.8f}+(1-{factor:.8f})*(t-{end:.6f})/{release:.6f})"
            else:
                release_expr = "1"
            expr = (
                f"if(between(t,{a0:.6f},{start:.6f}),{attack_expr},"
                f"if(between(t,{start:.6f},{end:.6f}),{factor:.8f},"
                f"if(between(t,{end:.6f},{r1:.6f}),{release_expr},{expr})))"
            )
        return expr
