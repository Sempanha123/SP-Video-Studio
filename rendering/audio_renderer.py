from __future__ import annotations


def mix_filter(source_label:str|None,narration_label:str|None,*,source_volume:float=1.0,narration_volume:float=1.0,duration_seconds:float)->tuple[list[str],str]:
    """Small reusable audio-filter builder used by tests/future renderer growth."""
    filters=[]; labels=[]
    if source_label:
        filters.append(f"[{source_label}]aresample=48000,aformat=channel_layouts=stereo,volume={max(0,min(1,source_volume)):.4f},apad,atrim=duration={duration_seconds:.6f}[srcmix]"); labels.append("srcmix")
    if narration_label:
        filters.append(f"[{narration_label}]aresample=48000,aformat=channel_layouts=stereo,volume={max(0,min(1,narration_volume)):.4f},apad,atrim=duration={duration_seconds:.6f}[narrmix]"); labels.append("narrmix")
    if len(labels)==2:
        filters.append(f"[{labels[0]}][{labels[1]}]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95,atrim=duration={duration_seconds:.6f}[aout]"); return filters,"aout"
    if len(labels)==1:
        filters.append(f"[{labels[0]}]atrim=duration={duration_seconds:.6f}[aout]"); return filters,"aout"
    filters.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={duration_seconds:.6f}[aout]"); return filters,"aout"
