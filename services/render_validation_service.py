from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from domain.render_settings import RenderSettings
from rendering.encoder_registry import EncoderRegistry
from rendering.errors import RenderEncoderUnavailable, RenderInsufficientDisk, RenderMissingAsset, RenderValidationError


@dataclass(frozen=True,slots=True)
class RenderIssue:
    severity:str
    code:str
    message:str
    scene_id:str=""


class RenderValidationService:
    def __init__(self, disk_usage=shutil.disk_usage) -> None: self.disk_usage=disk_usage

    def validate(self,*,project_path:Path,scenes:list[dict],settings:RenderSettings,encoders:EncoderRegistry,output_path:Path,ffmpeg_filters:set[str]|frozenset[str]|None=None,project_aspect_ratio:str="")->list[RenderIssue]:
        issues=[]
        try: settings.validate()
        except ValueError as exc: issues.append(RenderIssue("error","invalid_settings",str(exc)))
        if not scenes: issues.append(RenderIssue("error","no_scenes","Add at least one enabled scene before rendering."))
        for spec in scenes:
            sid=str(spec.get("sceneId","") or ""); dur=int(spec.get("durationMs",0) or 0); visual=dict(spec.get("visual",{}) or {}); audio=dict(spec.get("audio",{}) or {})
            if dur<=0: issues.append(RenderIssue("error","invalid_duration","Scene duration must be greater than zero.",sid))
            media_path=str(visual.get("path","") or "")
            if media_path and not Path(media_path).is_file(): issues.append(RenderIssue("error","missing_media","The visual used by this scene is no longer available.",sid))
            if not media_path and not bool(visual.get("backgroundEnabled",False)): issues.append(RenderIssue("error","missing_visual","Scene has no visual or background.",sid))
            if str(visual.get("mediaType",""))=="video":
                source_duration=int(visual.get("durationMs",0) or 0); start=int(visual.get("sourceStartMs",0) or 0); end=int(visual.get("sourceEndMs",-1) or -1); available=(end-start) if end>start else max(0,source_duration-start)
                if source_duration>0 and available<dur: issues.append(RenderIssue("error","video_too_short","Scene is longer than the selected video range.",sid))
                w=int(visual.get("width",0) or 0); h=int(visual.get("height",0) or 0)
                if w and h and w*h < settings.width*settings.height*.40: issues.append(RenderIssue("warning","low_resolution","This video may appear soft at the selected output resolution.",sid))
            elif str(visual.get("mediaType",""))=="image":
                w=int(visual.get("width",0) or 0); h=int(visual.get("height",0) or 0)
                if w and h and w*h < settings.width*settings.height*.40: issues.append(RenderIssue("warning","low_resolution","This image may appear soft at the selected output resolution.",sid))
            narr=str(audio.get("narrationPath","") or "")
            if audio.get("narrationAudioId") and bool(audio.get("narrationEnabled",True)) and (not narr or not Path(narr).is_file()): issues.append(RenderIssue("error","missing_narration","Narration file could not be found.",sid))
            narr_dur=int(audio.get("narrationDurationMs",0) or 0)
            if bool(audio.get("narrationEnabled",True)) and narr_dur>dur+100: issues.append(RenderIssue("error","narration_too_long","Narration is longer than the scene.",sid))
            for overlay in spec.get("overlays",[]) or []:
                if str(overlay.get("type",""))=="logo" and overlay.get("visible",True):
                    p=str(overlay.get("assetPath","") or "")
                    if not p or not Path(p).is_file(): issues.append(RenderIssue("error","missing_logo","A logo used by this scene is missing.",sid))
        if ffmpeg_filters is not None:
            needs_ass=bool(settings.subtitle_track_id) or any(any(str(o.get("type",""))!="logo" and o.get("visible",True) for o in s.get("overlays",[]) or []) for s in scenes)
            if needs_ass and "subtitles" not in ffmpeg_filters and "ass" not in ffmpeg_filters: issues.append(RenderIssue("error","libass_missing","This FFmpeg build does not include libass subtitle rendering."))
        try: encoders.resolve(settings.encoder,allow_fallback=settings.allow_hardware_fallback)
        except ValueError as exc: issues.append(RenderIssue("error","encoder_unavailable",str(exc)))
        ratio=settings.width/settings.height; project_ratio=self._ratio_value(project_aspect_ratio)
        if project_ratio and abs(ratio-project_ratio)>0.03: issues.append(RenderIssue("warning","aspect_mismatch","Output resolution does not match the project aspect ratio."))
        try:
            target=self._existing_ancestor(output_path.parent); usage=self.disk_usage(target); required=self.estimate_required_bytes(scenes,settings)
            if usage.free<required: issues.append(RenderIssue("error","insufficient_disk",f"Rendering requires approximately {required/1024**3:.1f} GB of free space."))
        except OSError: issues.append(RenderIssue("error","output_unavailable","Render output location is not writable."))
        return issues

    @staticmethod
    def estimate_required_bytes(scenes:list[dict],settings:RenderSettings)->int:
        seconds=sum(max(0,int(s.get("durationMs",0) or 0)) for s in scenes)/1000.0
        intermediate=settings.width*settings.height*settings.fps*seconds*.25
        return int(intermediate*1.8 + 128*1024**2)

    @staticmethod
    def blocking(issues:list[RenderIssue])->list[RenderIssue]: return [i for i in issues if i.severity=="error"]

    @staticmethod
    def _existing_ancestor(path:Path)->Path:
        current=path
        while not current.exists() and current.parent!=current: current=current.parent
        return current

    @staticmethod
    def _ratio_value(value:str)->float|None:
        try:
            left,right=str(value).split(":",1); result=float(left)/float(right)
            return result if result>0 else None
        except (ValueError,ZeroDivisionError):
            return None
