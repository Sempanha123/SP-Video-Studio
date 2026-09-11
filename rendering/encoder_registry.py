from __future__ import annotations

from dataclasses import dataclass

from media.ffmpeg import FFmpegCapabilities, FFmpegRunner


@dataclass(frozen=True, slots=True)
class EncoderInfo:
    encoder_id: str
    name: str
    hardware: bool
    available: bool
    runtime_ready: bool | None = None


class EncoderRegistry:
    ORDER = ("h264_nvenc","h264_qsv","h264_amf","libx264")
    NAMES = {"libx264":"Software H.264 (libx264)","h264_nvenc":"NVIDIA NVENC H.264","h264_qsv":"Intel Quick Sync H.264","h264_amf":"AMD AMF H.264"}

    def __init__(self, runner: FFmpegRunner, capabilities: FFmpegCapabilities|None=None) -> None:
        self.runner=runner; self.capabilities=capabilities or runner.discover_capabilities(); self._runtime:dict[str,bool]={}

    def list(self, *, validate_hardware: bool=False) -> list[EncoderInfo]:
        result=[]
        for enc in self.ORDER:
            available=self.capabilities.has_encoder(enc); ready=None
            if available and enc!="libx264" and validate_hardware:
                ready=self._runtime.setdefault(enc,self.runner.validate_encoder(enc))
            elif available and enc=="libx264": ready=True
            result.append(EncoderInfo(enc,self.NAMES[enc],enc!="libx264",available,ready))
        return result

    def resolve(self, requested: str="auto", *, allow_fallback: bool=True) -> str:
        requested=requested or "auto"
        if requested!="auto":
            if not self.capabilities.has_encoder(requested):
                raise ValueError(f"Encoder {requested} is not available in this FFmpeg build.")
            if requested!="libx264" and not self._runtime.setdefault(requested,self.runner.validate_encoder(requested)):
                if allow_fallback and self.capabilities.has_encoder("libx264"): return "libx264"
                raise ValueError(f"Encoder {requested} is listed by FFmpeg but is not usable on this system.")
            return requested
        for enc in ("h264_nvenc","h264_qsv","h264_amf"):
            if self.capabilities.has_encoder(enc) and self._runtime.setdefault(enc,self.runner.validate_encoder(enc)):
                return enc
        if self.capabilities.has_encoder("libx264"): return "libx264"
        raise ValueError("No supported H.264 encoder is available.")

    @staticmethod
    def quality_args(encoder: str, quality: str) -> list[str]:
        quality=str(quality)
        if encoder=="libx264":
            preset={"fast":"faster","balanced":"medium","high":"slow"}.get(quality,"medium")
            crf={"fast":"25","balanced":"21","high":"18"}.get(quality,"21")
            return ["-preset",preset,"-crf",crf]
        if encoder=="h264_nvenc":
            preset={"fast":"p3","balanced":"p5","high":"p7"}.get(quality,"p5")
            cq={"fast":"25","balanced":"21","high":"18"}.get(quality,"21")
            return ["-preset",preset,"-rc","vbr","-cq",cq,"-b:v","0"]
        if encoder=="h264_qsv":
            global_quality={"fast":"27","balanced":"23","high":"19"}.get(quality,"23")
            return ["-global_quality",global_quality]
        if encoder=="h264_amf":
            usage={"fast":"transcoding","balanced":"transcoding","high":"high_quality"}.get(quality,"transcoding")
            quality_flag={"fast":"speed","balanced":"balanced","high":"quality"}.get(quality,"balanced")
            return ["-usage",usage,"-quality",quality_flag]
        return []
