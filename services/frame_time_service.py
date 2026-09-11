from __future__ import annotations


class FrameTimeService:
    @staticmethod
    def frame_duration_ms(fps: float) -> float:
        value = float(fps)
        if value <= 0:
            raise ValueError("FPS must be positive.")
        return 1000.0 / value

    @classmethod
    def snap_ms(cls, milliseconds: int | float, fps: float) -> int:
        frame = cls.frame_duration_ms(fps)
        return max(0, int(round(round(float(milliseconds) / frame) * frame)))

    @staticmethod
    def frames_to_ms(frame_number: int, fps: float) -> int:
        if fps <= 0:
            raise ValueError("FPS must be positive.")
        return max(0, int(round(int(frame_number) * 1000.0 / float(fps))))

    @staticmethod
    def ms_to_frame(milliseconds: int | float, fps: float) -> int:
        if fps <= 0:
            raise ValueError("FPS must be positive.")
        return max(0, int(round(float(milliseconds) * float(fps) / 1000.0)))

    @classmethod
    def timecode(cls, milliseconds: int, fps: float) -> str:
        fps_int = max(1, int(round(fps)))
        total_frames = cls.ms_to_frame(milliseconds, fps)
        frames = total_frames % fps_int
        total_seconds = total_frames // fps_int
        seconds = total_seconds % 60
        minutes = (total_seconds // 60) % 60
        hours = total_seconds // 3600
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
