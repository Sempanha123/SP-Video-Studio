from __future__ import annotations

from dataclasses import dataclass

from domain.dub_segment import DubSegment, DubTimingMode, DubTimingStatus
from domain.dub_timing import DubTimingAnalysis


@dataclass(frozen=True, slots=True)
class DubbingAlignmentConfig:
    safe_min_tempo: float = 0.85
    safe_max_tempo: float = 1.20
    fit_tolerance_ms: int = 180
    very_long_ratio: float = 1.50
    long_gap_warning_ms: int = 2500


class DubbingAlignmentService:
    def __init__(self, config: DubbingAlignmentConfig | None = None) -> None:
        self.config = config or DubbingAlignmentConfig()

    def analyze(self, segment: DubSegment) -> DubTimingAnalysis:
        target = segment.target_duration_ms
        generated = max(0, segment.generated_duration_ms)
        if target <= 0:
            return DubTimingAnalysis(target, generated, generated, 0.0, 1.0, DubTimingStatus.NEEDS_REVIEW.value, False, True)
        if generated <= 0:
            return DubTimingAnalysis(target, 0, -target, 0.0, 1.0, DubTimingStatus.NOT_GENERATED.value, False, False)
        diff = generated - target
        ratio = generated / target
        tempo = ratio
        safe = self.config.safe_min_tempo <= tempo <= self.config.safe_max_tempo
        if abs(diff) <= self.config.fit_tolerance_ms:
            status = DubTimingStatus.FITS.value
        elif generated < target:
            status = DubTimingStatus.SHORT.value
        elif ratio >= self.config.very_long_ratio:
            status = DubTimingStatus.VERY_LONG.value
        else:
            status = DubTimingStatus.LONG.value
        return DubTimingAnalysis(target, generated, diff, ratio, tempo, status, safe, not safe)

    def apply_analysis(self, segment: DubSegment) -> DubTimingAnalysis:
        analysis = self.analyze(segment)
        segment.timing_status = analysis.status
        if segment.timing_mode_code == DubTimingMode.FIT_SEGMENT.value:
            if analysis.safe_to_fit and analysis.generated_duration_ms > 0:
                segment.stretch_factor = analysis.required_tempo
                segment.timing_status = DubTimingStatus.ADJUSTED
            elif analysis.generated_duration_ms > 0:
                segment.stretch_factor = 1.0
                segment.timing_status = DubTimingStatus.NEEDS_REVIEW
        elif segment.timing_mode_code == DubTimingMode.NATURAL.value:
            segment.stretch_factor = 1.0
        return analysis

    def fit_compatible(self, segments: list[DubSegment]) -> list[str]:
        changed: list[str] = []
        for segment in segments:
            if segment.locked:
                continue
            analysis = self.analyze(segment)
            if analysis.safe_to_fit and analysis.generated_duration_ms > 0:
                segment.timing_mode = DubTimingMode.FIT_SEGMENT
                segment.stretch_factor = analysis.required_tempo
                segment.timing_status = DubTimingStatus.ADJUSTED
                changed.append(segment.id)
        return changed

    @staticmethod
    def atempo_chain(tempo: float) -> list[float]:
        if tempo <= 0:
            raise ValueError("Tempo must be positive.")
        values: list[float] = []
        remaining = float(tempo)
        while remaining > 2.0:
            values.append(2.0)
            remaining /= 2.0
        while remaining < 0.5:
            values.append(0.5)
            remaining /= 0.5
        if abs(remaining - 1.0) > 1e-6 or not values:
            values.append(remaining)
        return values

    def detect_overlaps(self, segments: list[DubSegment]) -> list[dict[str, object]]:
        placed = [s for s in sorted(segments, key=lambda item: (item.effective_start_ms, item.order)) if s.effective_duration_ms > 0]
        result: list[dict[str, object]] = []
        for left, right in zip(placed, placed[1:]):
            overlap = left.effective_end_ms - right.effective_start_ms
            if overlap > 0:
                result.append({"leftSegmentId": left.id, "rightSegmentId": right.id, "overlapMs": overlap})
        return result

    def analyze_gaps(self, segments: list[DubSegment]) -> list[dict[str, object]]:
        placed = [s for s in sorted(segments, key=lambda item: (item.effective_start_ms, item.order)) if s.effective_duration_ms > 0]
        result: list[dict[str, object]] = []
        for left, right in zip(placed, placed[1:]):
            gap = right.effective_start_ms - left.effective_end_ms
            if gap >= self.config.long_gap_warning_ms:
                result.append({"leftSegmentId": left.id, "rightSegmentId": right.id, "gapMs": gap})
        return result

    def validate_offset(self, segment: DubSegment, offset_ms: int, *, allow_overlap: bool = False) -> int:
        start = segment.source_start_ms + int(offset_ms)
        if start < 0:
            raise ValueError("Dub segment cannot begin before zero.")
        if not allow_overlap and start > segment.source_end_ms:
            raise ValueError("Offset moves the dub outside its source window.")
        return int(offset_ms)
