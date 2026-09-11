from __future__ import annotations

from pathlib import Path
from typing import Callable

from domain.render_settings import RenderSettings
from media.ffmpeg import FFmpegRunner
from media.ffmpeg_escape import subtitles_filter
from media.filters import fade_filters, fit_filter
from rendering.overlay_renderer import OverlayRenderer
from workers.cancellation import CancellationToken


class SceneRenderer:
    """Renders a normalized scene intermediate (FFV1 + PCM stereo)."""

    def __init__(self, runner:FFmpegRunner, overlay_renderer:OverlayRenderer|None=None, fonts_dir:str|Path|None=None) -> None:
        self.runner=runner; self.overlay_renderer=overlay_renderer or OverlayRenderer(); self.fonts_dir=Path(fonts_dir) if fonts_dir else None

    def render(self, spec:dict, settings:RenderSettings, destination:Path, *, temp_dir:Path, cancellation:CancellationToken|None=None, progress_callback:Callable|None=None)->Path:
        args=self.build_command(spec,settings,destination,temp_dir=temp_dir)
        self.runner.run(args,expected_duration_ms=int(spec.get("durationMs",0) or 0),cancellation=cancellation,progress_callback=progress_callback)
        return destination

    def build_command(self,spec:dict,settings:RenderSettings,destination:Path,*,temp_dir:Path)->list[str]:
        duration_ms=int(spec.get("durationMs",0) or 0); duration=duration_ms/1000.0
        visual=dict(spec.get("visual",{}) or {}); audio=dict(spec.get("audio",{}) or {}); overlays=list(spec.get("overlays",[]) or [])
        inputs:list[str]=[]; visual_input=0
        media_path=str(visual.get("path","") or ""); media_type=str(visual.get("mediaType","") or "")
        bg=str(visual.get("backgroundColor","#000000") or "#000000")
        if media_path:
            if media_type=="image": inputs += ["-loop","1","-framerate",str(settings.fps),"-i",media_path]
            else:
                start=max(0,int(visual.get("sourceStartMs",0) or 0))/1000.0
                if start>0: inputs += ["-ss",f"{start:.6f}"]
                inputs += ["-i",media_path]
        else:
            color=bg if bg.startswith("#") else "#000000"
            inputs += ["-f","lavfi","-i",f"color=c={color}:s={settings.width}x{settings.height}:r={settings.fps}:d={duration:.6f}"]
        next_input=1
        logo_inputs=[]
        for overlay in overlays:
            if str(overlay.get("type",""))!="logo" or not overlay.get("visible",True): continue
            path=str(overlay.get("assetPath","") or "")
            if not path: continue
            inputs += ["-loop","1","-framerate",str(settings.fps),"-i",path]
            logo_inputs.append((next_input,overlay)); next_input+=1
        narration_index=None; narration=str(audio.get("narrationPath","") or "")
        if narration and bool(audio.get("narrationEnabled",True)):
            inputs += ["-i",narration]; narration_index=next_input; next_input+=1

        filters=[]
        base=fit_filter(settings.width,settings.height,str(visual.get("fitMode","fill")),background=bg)
        chain=[base,"fps="+str(settings.fps),f"trim=duration={duration:.6f}","setpts=PTS-STARTPTS"]
        chain += fade_filters(duration_ms,dict(spec.get("transitionIn",{}) or {}),dict(spec.get("transitionOut",{}) or {}))
        filters.append(f"[{visual_input}:v]{','.join(chain)}[v0]")
        current="v0"
        # Generic shape overlays are renderer-supported project data, not News-only drawing.
        for n,overlay in enumerate([o for o in overlays if str(o.get("type",""))=="shape" and o.get("visible",True)],1):
            x=round(float(overlay.get("x",0))*settings.width); y=round(float(overlay.get("y",0))*settings.height)
            w=max(1,round(float(overlay.get("width",.2))*settings.width)); h=max(1,round(float(overlay.get("height",.1))*settings.height))
            style=dict(overlay.get("style",{}) or {}); fill=str(style.get("fillColor") or style.get("backgroundColor") or "#000000")
            opacity=max(0,min(1,float(overlay.get("opacity",1) or 0))); start=max(0,int(overlay.get("startOffsetMs",0) or 0))/1000.0
            raw_end=int(overlay.get("endOffsetMs",-1) or -1); end=duration if raw_end<0 else min(duration,raw_end/1000.0)
            color=fill[:7] if fill.startswith("#") and len(fill)>=7 else "#000000"
            out=f"vshape{n}"; filters.append(f"[{current}]drawbox=x={x}:y={y}:w={w}:h={h}:color={color}@{opacity:.4f}:t=fill:enable='between(t,{start:.6f},{end:.6f})'[{out}]"); current=out
        for n,(idx,overlay) in enumerate(logo_inputs,1):
            w=max(2,round(float(overlay.get("width",.1))*settings.width)); h=max(2,round(float(overlay.get("height",.1))*settings.height))
            x=round(float(overlay.get("x",0))*settings.width); y=round(float(overlay.get("y",0))*settings.height); opacity=max(0,min(1,float(overlay.get("opacity",1) or 0)))
            filters.append(f"[{idx}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,format=rgba,colorchannelmixer=aa={opacity:.4f}[logo{n}]")
            start=max(0,int(overlay.get("startOffsetMs",0) or 0))/1000.0; raw_end=int(overlay.get("endOffsetMs",-1) or -1); end=duration if raw_end<0 else min(duration,raw_end/1000.0)
            out=f"vlogo{n}"; filters.append(f"[{current}][logo{n}]overlay={x}:{y}:format=auto:enable='between(t,{start:.6f},{end:.6f})'[{out}]"); current=out
        ass_path=self.overlay_renderer.write_ass(overlays,temp_dir/f"{spec.get('sceneId','scene')}-overlays.ass",width=settings.width,height=settings.height,duration_ms=duration_ms)
        if ass_path:
            expr=subtitles_filter(ass_path,fonts_dir=self.fonts_dir); filters.append(f"[{current}]{expr}[vout]"); current="vout"

        audio_labels=[]
        if media_path and media_type=="video" and bool(audio.get("sourceAudioEnabled",False)) and bool(visual.get("hasAudio",False)):
            vol=max(0,min(1,float(audio.get("sourceAudioVolume",1) or 0))); filters.append(f"[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume={vol:.4f},apad,atrim=duration={duration:.6f}[asrc]"); audio_labels.append("asrc")
        if narration_index is not None:
            vol=max(0,min(1,float(audio.get("narrationVolume",1) or 0))); filters.append(f"[{narration_index}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume={vol:.4f},apad,atrim=duration={duration:.6f}[anarr]"); audio_labels.append("anarr")
        if len(audio_labels)==2:
            filters.append(f"[{audio_labels[0]}][{audio_labels[1]}]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95,atrim=duration={duration:.6f}[aout]")
        elif len(audio_labels)==1:
            filters.append(f"[{audio_labels[0]}]atrim=duration={duration:.6f}[aout]")
        else:
            filters.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={duration:.6f}[aout]")

        return [*inputs,"-filter_complex",";".join(filters),"-map",f"[{current}]","-map","[aout]","-t",f"{duration:.6f}","-r",str(settings.fps),"-c:v","ffv1","-level","3","-g","1","-pix_fmt","yuv420p","-c:a","pcm_s16le","-ar","48000","-ac","2",str(destination)]
