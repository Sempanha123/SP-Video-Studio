from __future__ import annotations

from pathlib import Path
from typing import Callable

from domain.phase22_errors import ChromaKeyUnavailable, CompositionError
from media.ffmpeg_escape import subtitles_filter
from media.filters import fade_filters, fit_filter


def build_layered_scene_command(scene_renderer, original: Callable, spec: dict, settings, destination: Path, *, temp_dir: Path) -> list[str]:
    """Build one deterministic filter graph for the canonical Scene spec.

    Falls back to the Phase15 SceneRenderer when no Phase22 visual/audio layers are present.
    """
    layers=[dict(x) for x in list(spec.get("layers",[]) or []) if x.get("visible",True) and x.get("assetPath")]
    manual_audio=[dict(x) for x in list(spec.get("manualAudio",[]) or []) if not x.get("muted",False) and x.get("assetPath")]
    visual=dict(spec.get("visual",{}) or {}); reframe=dict(visual.get("reframe",{}) or {})
    if not layers and not manual_audio and not reframe:
        return original(spec,settings,destination,temp_dir=temp_dir)

    duration_ms=int(spec.get("durationMs",0) or 0); duration=max(.001,duration_ms/1000.0)
    audio=dict(spec.get("audio",{}) or {}); overlays=list(spec.get("overlays",[]) or [])
    caps=scene_renderer.runner.discover_capabilities(); available=set(caps.filters)
    inputs:list[str]=[]; media_path=str(visual.get("path","") or ""); media_type=str(visual.get("mediaType","") or ""); bg=str(visual.get("backgroundColor","#000000") or "#000000")
    if media_path:
        if media_type=="image": inputs += ["-loop","1","-framerate",str(settings.fps),"-i",media_path]
        else:
            source_start=max(0,int(visual.get("sourceStartMs",0) or 0))/1000.0
            if source_start: inputs += ["-ss",f"{source_start:.6f}"]
            inputs += ["-i",media_path]
    else:
        inputs += ["-f","lavfi","-i",f"color=c={bg if bg.startswith('#') else '#000000'}:s={settings.width}x{settings.height}:r={settings.fps}:d={duration:.6f}"]
    next_input=1; layer_inputs=[]
    for layer in sorted(layers,key=lambda x:(int(x.get("zOrder",x.get("order",0)) or 0),int(x.get("order",0) or 0))):
        source_in=max(0,int(layer.get("sourceInMs",0) or 0))/1000.0
        if source_in: inputs += ["-ss",f"{source_in:.6f}"]
        if str(layer.get("mediaType",""))=="image": inputs += ["-loop","1","-framerate",str(settings.fps),"-i",str(layer["assetPath"])]
        else: inputs += ["-i",str(layer["assetPath"])]
        layer_inputs.append((next_input,layer)); next_input+=1
    logo_inputs=[]
    for overlay in overlays:
        if str(overlay.get("type",""))!="logo" or not overlay.get("visible",True) or not overlay.get("assetPath"): continue
        inputs += ["-loop","1","-framerate",str(settings.fps),"-i",str(overlay["assetPath"])]
        logo_inputs.append((next_input,overlay)); next_input+=1
    narration_index=None; narration=str(audio.get("narrationPath","") or "")
    if narration and bool(audio.get("narrationEnabled",True)):
        inputs += ["-i",narration]; narration_index=next_input; next_input+=1
    manual_inputs=[]
    for item in manual_audio:
        source_in=max(0,int(item.get("sourceInMs",0) or 0))/1000.0
        if source_in: inputs += ["-ss",f"{source_in:.6f}"]
        inputs += ["-i",str(item["assetPath"])]
        manual_inputs.append((next_input,item)); next_input+=1

    filters=[]
    if reframe:
        crop_l=max(0,min(.95,float(reframe.get("cropLeft",0) or 0))); crop_t=max(0,min(.95,float(reframe.get("cropTop",0) or 0)))
        crop_r=max(0,min(.95,float(reframe.get("cropRight",0) or 0))); crop_b=max(0,min(.95,float(reframe.get("cropBottom",0) or 0)))
        if crop_l+crop_r>=.98 or crop_t+crop_b>=.98: raise CompositionError("Short reframe crop removes the whole image.")
        fit=str(reframe.get("fitMode",visual.get("fitMode","fill")) or "fill"); scale=max(.1,min(8.0,float(reframe.get("scale",1) or 1)))
        ox=max(-1.0,min(1.0,float(reframe.get("offsetX",0) or 0))); oy=max(-1.0,min(1.0,float(reframe.get("offsetY",0) or 0)))
        primary=[]
        if crop_l or crop_t or crop_r or crop_b:
            primary.append(f"crop=iw*{1-crop_l-crop_r:.8f}:ih*{1-crop_t-crop_b:.8f}:iw*{crop_l:.8f}:ih*{crop_t:.8f}")
        if fit=="fit":
            primary.append(f"scale={settings.width}:{settings.height}:force_original_aspect_ratio=decrease")
            if abs(scale-1)>.0001: primary.append(f"scale=iw*{scale:.6f}:ih*{scale:.6f}")
            primary.append(f"pad={settings.width}:{settings.height}:(ow-iw)/2:(oh-ih)/2:color={bg}")
        elif fit=="stretch":
            primary.append(f"scale={settings.width}:{settings.height}")
        else:
            primary.append(f"scale={settings.width}:{settings.height}:force_original_aspect_ratio=increase")
            if abs(scale-1)>.0001: primary.append(f"scale=iw*{scale:.6f}:ih*{scale:.6f}")
            primary.append(f"crop={settings.width}:{settings.height}:x='max(0,min(iw-ow,(iw-ow)/2+({ox:.6f})*(iw-ow)/2))':y='max(0,min(ih-oh,(ih-oh)/2+({oy:.6f})*(ih-oh)/2))'")
        base=",".join(primary)
    else:
        base=fit_filter(settings.width,settings.height,str(visual.get("fitMode","fill")),background=bg)
    chain=[base,"fps="+str(settings.fps),f"trim=duration={duration:.6f}","setpts=PTS-STARTPTS"]
    chain += fade_filters(duration_ms,dict(spec.get("transitionIn",{}) or {}),dict(spec.get("transitionOut",{}) or {}))
    filters.append(f"[0:v]{','.join(chain)}[vbase]"); current="vbase"

    for n,(idx,layer) in enumerate(layer_inputs,1):
        start=max(0,int(layer.get("startMs",0) or 0))/1000.0
        raw_d=int(layer.get("durationMs",0) or 0); ld=max(.001,(raw_d if raw_d>0 else duration_ms-int(start*1000))/1000.0)
        target_w=max(2,round(float(layer.get("width",1))*settings.width)); target_h=max(2,round(float(layer.get("height",1))*settings.height))
        x=round(float(layer.get("x",0))*settings.width); y=round(float(layer.get("y",0))*settings.height)
        crop_l=max(0,min(.95,float(layer.get("cropLeft",0) or 0))); crop_t=max(0,min(.95,float(layer.get("cropTop",0) or 0)))
        crop_r=max(0,min(.95,float(layer.get("cropRight",0) or 0))); crop_b=max(0,min(.95,float(layer.get("cropBottom",0) or 0)))
        if crop_l+crop_r>=1 or crop_t+crop_b>=1: raise CompositionError("Layer crop removes the whole image.")
        parts=[f"trim=duration={ld:.6f}","setpts=PTS-STARTPTS"]
        if crop_l or crop_t or crop_r or crop_b:
            parts.append(f"crop=iw*{1-crop_l-crop_r:.8f}:ih*{1-crop_t-crop_b:.8f}:iw*{crop_l:.8f}:ih*{crop_t:.8f}")
        chroma=dict(layer.get("chromaKey") or {})
        if chroma.get("enabled"):
            filter_name="chromakey" if "chromakey" in available else ("colorkey" if "colorkey" in available else "")
            if not filter_name: raise ChromaKeyUnavailable()
            color=str(chroma.get("keyColor","#00FF00") or "#00FF00").replace("#","0x")
            similarity=max(.01,min(1,float(chroma.get("similarity",.18) or .18))); blend=max(0,min(1,float(chroma.get("blend",.08) or .08)))
            parts += ["format=rgba",f"{filter_name}={color}:{similarity:.4f}:{blend:.4f}"]
        if layer.get("flipHorizontal"): parts.append("hflip")
        if layer.get("flipVertical"): parts.append("vflip")
        rotation=float(layer.get("rotation",0) or 0)
        if abs(rotation)>.001: parts.append(f"rotate={rotation:.6f}*PI/180:ow=rotw(iw):oh=roth(ih):c=none")
        fit=str(layer.get("fitMode","contain") or "contain")
        if fit in {"fit","contain"}: parts += [f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease",f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:color=black@0"]
        elif fit=="stretch": parts += [f"scale={target_w}:{target_h}"]
        else: parts += [f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase",f"crop={target_w}:{target_h}"]
        opacity=max(0,min(1,float(layer.get("opacity",1) or 0)))
        parts += ["format=rgba",f"colorchannelmixer=aa={opacity:.4f}",f"setpts=PTS+{start:.6f}/TB"]
        lname=f"layer{n}"; filters.append(f"[{idx}:v]{','.join(parts)}[{lname}]")
        out=f"vlay{n}"; filters.append(f"[{current}][{lname}]overlay={x}:{y}:format=auto:enable='between(t,{start:.6f},{min(duration,start+ld):.6f})'[{out}]"); current=out

    # Existing shape/logo/text overlays remain part of the same graph.
    for n,overlay in enumerate([o for o in overlays if str(o.get("type",""))=="shape" and o.get("visible",True)],1):
        x=round(float(overlay.get("x",0))*settings.width); y=round(float(overlay.get("y",0))*settings.height); w=max(1,round(float(overlay.get("width",.2))*settings.width)); h=max(1,round(float(overlay.get("height",.1))*settings.height))
        style=dict(overlay.get("style",{}) or {}); fill=str(style.get("fillColor") or style.get("backgroundColor") or "#000000"); opacity=max(0,min(1,float(overlay.get("opacity",1) or 0))); start=max(0,int(overlay.get("startOffsetMs",0) or 0))/1000.0; raw_end=int(overlay.get("endOffsetMs",-1) or -1); end=duration if raw_end<0 else min(duration,raw_end/1000.0); color=fill[:7] if fill.startswith("#") and len(fill)>=7 else "#000000"; out=f"vshape{n}"; filters.append(f"[{current}]drawbox=x={x}:y={y}:w={w}:h={h}:color={color}@{opacity:.4f}:t=fill:enable='between(t,{start:.6f},{end:.6f})'[{out}]"); current=out
    for n,(idx,overlay) in enumerate(logo_inputs,1):
        w=max(2,round(float(overlay.get("width",.1))*settings.width)); h=max(2,round(float(overlay.get("height",.1))*settings.height)); x=round(float(overlay.get("x",0))*settings.width); y=round(float(overlay.get("y",0))*settings.height); opacity=max(0,min(1,float(overlay.get("opacity",1) or 0))); filters.append(f"[{idx}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,format=rgba,colorchannelmixer=aa={opacity:.4f}[logo{n}]"); start=max(0,int(overlay.get("startOffsetMs",0) or 0))/1000.0; raw_end=int(overlay.get("endOffsetMs",-1) or -1); end=duration if raw_end<0 else min(duration,raw_end/1000.0); out=f"vlogo{n}"; filters.append(f"[{current}][logo{n}]overlay={x}:{y}:format=auto:enable='between(t,{start:.6f},{end:.6f})'[{out}]"); current=out
    ass_path=scene_renderer.overlay_renderer.write_ass(overlays,temp_dir/f"{spec.get('sceneId','scene')}-overlays.ass",width=settings.width,height=settings.height,duration_ms=duration_ms)
    if ass_path:
        expr=subtitles_filter(ass_path,fonts_dir=scene_renderer.fonts_dir); filters.append(f"[{current}]{expr}[vtext]"); current="vtext"

    audio_labels=[]
    if media_path and media_type=="video" and bool(audio.get("sourceAudioEnabled",False)) and bool(visual.get("hasAudio",False)):
        vol=max(0,min(2,float(audio.get("sourceAudioVolume",1) or 0))); filters.append(f"[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume={vol:.4f},apad,atrim=duration={duration:.6f}[asrc]"); audio_labels.append("asrc")
    if narration_index is not None:
        vol=max(0,min(2,float(audio.get("narrationVolume",1) or 0))); filters.append(f"[{narration_index}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume={vol:.4f},apad,atrim=duration={duration:.6f}[anarr]"); audio_labels.append("anarr")
    for n,(idx,layer) in enumerate(layer_inputs,1):
        if not layer.get("useAudio") or not layer.get("hasAudio") or str(layer.get("mediaType"))!="video": continue
        start=max(0,int(layer.get("startMs",0) or 0)); raw_d=max(1,int(layer.get("durationMs",duration_ms-start) or 1)); vol=max(0,min(2,float(layer.get("audioVolume",1) or 0))); label=f"alayer{n}"; delay=f"adelay={start}|{start}," if start else ""; filters.append(f"[{idx}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,atrim=duration={raw_d/1000.0:.6f},volume={vol:.4f},{delay}apad,atrim=duration={duration:.6f}[{label}]"); audio_labels.append(label)
    for n,(idx,item) in enumerate(manual_inputs,1):
        start=max(0,int(item.get("startMs",0) or 0)); dur=max(1,int(item.get("durationMs",1) or 1)); vol=max(0,min(2,float(item.get("volume",1) or 0))); chain=["aresample=48000","aformat=sample_fmts=fltp:channel_layouts=stereo",f"atrim=duration={dur/1000.0:.6f}",f"volume={vol:.4f}"]
        fin=max(0,int(item.get("fadeInMs",0) or 0)); fout=max(0,int(item.get("fadeOutMs",0) or 0))
        if fin: chain.append(f"afade=t=in:st=0:d={min(fin,dur)/1000.0:.6f}")
        if fout: chain.append(f"afade=t=out:st={max(0,dur-fout)/1000.0:.6f}:d={min(fout,dur)/1000.0:.6f}")
        if start: chain.append(f"adelay={start}|{start}")
        chain += ["apad",f"atrim=duration={duration:.6f}"]; label=f"amanual{n}"; filters.append(f"[{idx}:a]{','.join(chain)}[{label}]"); audio_labels.append(label)
    if len(audio_labels)>1:
        joined="".join(f"[{x}]" for x in audio_labels); filters.append(f"{joined}amix=inputs={len(audio_labels)}:duration=longest:normalize=0,alimiter=limit=0.95,atrim=duration={duration:.6f}[aout]")
    elif audio_labels: filters.append(f"[{audio_labels[0]}]atrim=duration={duration:.6f}[aout]")
    else: filters.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={duration:.6f}[aout]")
    return [*inputs,"-filter_complex",";".join(filters),"-map",f"[{current}]","-map","[aout]","-t",f"{duration:.6f}","-r",str(settings.fps),"-c:v","ffv1","-level","3","-g","1","-pix_fmt","yuv420p","-c:a","pcm_s16le","-ar","48000","-ac","2",str(destination)]
