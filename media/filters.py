from __future__ import annotations


def fit_filter(width: int, height: int, mode: str, *, background: str = "#000000") -> str:
    w,h=int(width),int(height)
    mode=str(mode or "fill").lower()
    if mode == "fit":
        return (
            f"scale={w}:{h}:force_original_aspect_ratio=decrease," 
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color={background},setsar=1"
        )
    if mode == "stretch":
        return f"scale={w}:{h},setsar=1"
    return f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1"


def fade_filters(duration_ms: int, transition_in: dict, transition_out: dict) -> list[str]:
    total=max(0.001,duration_ms/1000.0); result=[]
    if str(transition_in.get("type", "cut")) == "fade":
        d=min(total/2,max(0.0,float(transition_in.get("durationMs",0))/1000.0))
        if d>0: result.append(f"fade=t=in:st=0:d={d:.6f}")
    if str(transition_out.get("type", "cut")) == "fade":
        d=min(total/2,max(0.0,float(transition_out.get("durationMs",0))/1000.0))
        if d>0: result.append(f"fade=t=out:st={max(0,total-d):.6f}:d={d:.6f}")
    return result
