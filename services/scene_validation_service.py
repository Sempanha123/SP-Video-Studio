from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from domain.scene import Scene
from domain.scene_overlay import SceneOverlay
from storage.repositories.generated_audio_repository import GeneratedAudioRepository
from storage.repositories.media_repository import MediaRepository
from storage.repositories.subtitle_repository import SubtitleRepository


@dataclass(frozen=True, slots=True)
class SceneIssue:
    severity: str
    code: str
    message: str
    scene_id: str = ""
    overlay_id: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"severity":self.severity,"code":self.code,"message":self.message,"sceneId":self.scene_id,"overlayId":self.overlay_id}


class SceneValidationService:
    def __init__(self, media_repository: MediaRepository, audio_repository: GeneratedAudioRepository, subtitle_repository: SubtitleRepository) -> None:
        self.media_repository=media_repository; self.audio_repository=audio_repository; self.subtitle_repository=subtitle_repository

    def validate(self, scene: Scene, overlays: list[SceneOverlay]) -> list[SceneIssue]:
        issues: list[SceneIssue]=[]
        if scene.duration_ms <= 0: issues.append(SceneIssue("error","invalid_duration","Scene duration must be greater than zero.",scene.id))
        elif scene.duration_ms < 500: issues.append(SceneIssue("warning","very_short","Scene is shorter than 0.5 seconds.",scene.id))
        elif scene.duration_ms > 300_000: issues.append(SceneIssue("warning","very_long","Scene is longer than 5 minutes.",scene.id))
        media=None
        if scene.primary_media_id:
            media=self.media_repository.get_by_id(scene.primary_media_id)
            if media is None or media.project_id != scene.project_id or not Path(media.project_path).is_file():
                issues.append(SceneIssue("error","missing_media","The visual used by this scene is no longer available.",scene.id))
            elif media.type == "audio":
                issues.append(SceneIssue("error","invalid_visual","Audio cannot be used as primary scene visual.",scene.id))
            elif media.type == "video":
                end=scene.source_end_ms if scene.source_end_ms is not None else scene.source_start_ms+scene.duration_ms
                if media.duration_ms and end > media.duration_ms:
                    issues.append(SceneIssue("warning","video_too_short","Scene is longer than the selected video range.",scene.id))
        if not scene.primary_media_id and not bool(scene.metadata.get("backgroundEnabled", False)):
            issues.append(SceneIssue("warning","no_visual","Add a visual or background to this scene.",scene.id))
        if scene.narration_audio_id:
            audio=self.audio_repository.get(scene.narration_audio_id)
            if audio is None or audio.project_id != scene.project_id or not Path(audio.file_path).is_file():
                issues.append(SceneIssue("warning","missing_narration","Assigned narration could not be found.",scene.id))
            elif audio.duration_ms > scene.duration_ms:
                issues.append(SceneIssue("warning","narration_too_long",f"Narration is {(audio.duration_ms-scene.duration_ms)/1000:.1f} seconds longer than the scene.",scene.id))
        if scene.subtitle_track_id:
            track=self.subtitle_repository.get_track(scene.subtitle_track_id)
            if track is None or track.project_id != scene.project_id:
                issues.append(SceneIssue("warning","missing_subtitle","Assigned subtitle track could not be found.",scene.id))
        for transition in (scene.transition_in,scene.transition_out):
            if transition.duration_ms > scene.duration_ms // 2:
                issues.append(SceneIssue("warning","transition_too_long","Transition duration is too long for this scene.",scene.id))
        for overlay in overlays:
            try: overlay.validate(scene.duration_ms)
            except ValueError as exc: issues.append(SceneIssue("error","invalid_overlay",str(exc),scene.id,overlay.id)); continue
            if overlay.x < .03 or overlay.y < .03 or overlay.x+overlay.width > .97 or overlay.y+overlay.height > .97:
                issues.append(SceneIssue("warning","safe_area","Overlay reaches outside the recommended safe area.",scene.id,overlay.id))
            if overlay.type_code=="logo" and overlay.asset_id:
                asset=self.media_repository.get_by_id(overlay.asset_id)
                if asset is None or asset.project_id!=scene.project_id or asset.type!="image":
                    issues.append(SceneIssue("error","missing_logo","Logo image could not be found.",scene.id,overlay.id))
        return issues
