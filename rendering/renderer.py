from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from domain.render_settings import RenderSettings
from media.ffmpeg import FFmpegProcessError, FFmpegRunner
from media.ffmpeg_escape import subtitles_filter
from rendering.encoder_registry import EncoderRegistry
from rendering.errors import RenderCancelled, RenderProcessError
from rendering.overlay_renderer import OverlayRenderer
from rendering.progress import RenderProgressMapper, RenderProgressState
from rendering.render_graph import RenderGraph
from rendering.render_plan import RenderPlan
from rendering.scene_renderer import SceneRenderer
from rendering.subtitle_renderer import SubtitleRenderer
from rendering.transition_renderer import TransitionRenderer
from workers.cancellation import CancellationToken


@dataclass(frozen=True, slots=True)
class RenderExecutionResult:
    output_path: Path
    encoder: str
    graph: dict


class FFmpegRenderer:
    def __init__(
        self,
        runner:FFmpegRunner,
        encoders:EncoderRegistry,
        subtitle_renderer:SubtitleRenderer|None=None,
        *,
        fonts_dir:str|Path|None=None,
        logger:logging.Logger|None=None,
    ) -> None:
        self.runner=runner; self.encoders=encoders; self.subtitle_renderer=subtitle_renderer
        self.fonts_dir=Path(fonts_dir) if fonts_dir else None; self.logger=logger or logging.getLogger("sp_video_studio.rendering")
        self.scene_renderer=SceneRenderer(runner,OverlayRenderer(),self.fonts_dir); self.transition_renderer=TransitionRenderer(runner)

    def render(self,plan:RenderPlan,*,cancellation:CancellationToken|None=None,progress_callback:Callable[[RenderProgressState],None]|None=None)->RenderExecutionResult:
        plan.validate(); temp=Path(plan.temp_directory); temp.mkdir(parents=True,exist_ok=True); output=Path(plan.output_path); output.parent.mkdir(parents=True,exist_ok=True)
        partial=output.with_name(output.stem+".part"+output.suffix); partial.unlink(missing_ok=True)
        mapper=RenderProgressMapper(len(plan.scenes)); graph=RenderGraph(); scene_files=[]
        try:
            for i,spec in enumerate(plan.scenes):
                if cancellation and cancellation.is_cancelled: raise RenderCancelled("Render cancelled.")
                path=temp/f"scene-{i:04d}.nut"; graph.add(f"scene-{i}","scene_render",sceneId=spec.get("sceneId"),destination=str(path))
                def scene_progress(info,fraction,index=i):
                    if progress_callback: progress_callback(mapper.scene(index,fraction,info.out_time_ms,info.speed))
                self.scene_renderer.render(spec,plan.settings,path,temp_dir=temp,cancellation=cancellation,progress_callback=scene_progress); scene_files.append(path)
            combined=temp/"combined.nut"; graph.add("combine","transition_composition",inputs=[str(p) for p in scene_files],destination=str(combined))
            def combine_progress(info,fraction):
                if progress_callback: progress_callback(mapper.combine(fraction,info.out_time_ms,info.speed))
            self.transition_renderer.combine(scene_files,plan.scenes,combined,expected_duration_ms=plan.expected_duration_ms,fps=plan.settings.fps,cancellation=cancellation,progress_callback=combine_progress)
            encoder=self.encoders.resolve(plan.settings.encoder,allow_fallback=plan.settings.allow_hardware_fallback)
            final_args=["-i",str(combined)]
            vf=[]
            if plan.subtitle_track_id and self.subtitle_renderer:
                ass=self.subtitle_renderer.prepare_ass(plan.project_id,plan.subtitle_track_id,temp/"project-subtitles.ass",width=plan.settings.width,height=plan.settings.height)
                vf.append(subtitles_filter(ass,fonts_dir=self.fonts_dir)); graph.add("subtitles","subtitle_burn",inputs=["combine"],trackId=plan.subtitle_track_id,file=str(ass))
            vf.append("format="+plan.settings.pixel_format)
            final_args += ["-vf",",".join(vf),"-map","0:v:0","-map","0:a:0","-c:v",encoder,*self.encoders.quality_args(encoder,plan.settings.quality_code),"-pix_fmt",plan.settings.pixel_format,"-r",str(plan.settings.fps),"-c:a",plan.settings.audio_codec,"-b:a",plan.settings.audio_bitrate,"-ar","48000","-ac","2","-movflags","+faststart",str(partial)]
            graph.add("encode","final_encode",inputs=["subtitles" if plan.subtitle_track_id else "combine"],encoder=encoder,destination=str(output))
            def final_progress(info,fraction):
                if progress_callback: progress_callback(mapper.final(fraction,info.out_time_ms,info.speed))
            self.runner.run(final_args,expected_duration_ms=plan.expected_duration_ms,cancellation=cancellation,progress_callback=final_progress)
            if cancellation and cancellation.is_cancelled: raise RenderCancelled("Render cancelled.")
            partial.replace(output)
            if progress_callback: progress_callback(mapper.final(1.0,plan.expected_duration_ms,0.0))
            return RenderExecutionResult(output,encoder,graph.to_dict())
        except FFmpegProcessError as exc:
            partial.unlink(missing_ok=True)
            if cancellation and cancellation.is_cancelled: raise RenderCancelled("Render cancelled.") from exc
            raise RenderProcessError(f"FFmpeg failed while rendering. {exc.stderr_tail[-1200:]}") from exc
        except RenderCancelled:
            self.runner.cancel_active(); partial.unlink(missing_ok=True); raise
        except Exception:
            partial.unlink(missing_ok=True); raise
