from __future__ import annotations


class DubbingApplyService:
    """Adapters into existing Timeline/Subtitle/Render/Export systems; no second editor/renderer."""

    def __init__(self, dubbing_repository, subtitle_service=None, timeline_service=None) -> None:
        self.repository=dubbing_repository; self.subtitle_service=subtitle_service; self.timeline_service=timeline_service

    def render_audio_override(self, project_id: str) -> dict[str, object]:
        output=self.repository.latest_output(project_id,"final_mix")
        if output is None or output.status_code != "ready": return {}
        return {"primaryAudioOverride": output.file_path, "dubbingOutputId": output.id, "durationMs": output.duration_ms}

    def apply_render_settings(self, project_id: str, settings):
        data=self.render_audio_override(project_id)
        if not data: raise ValueError("Rebuild the dubbed audio mix before export.")
        settings.metadata=dict(settings.metadata); settings.metadata["primaryAudioOverride"]=str(data["primaryAudioOverride"])
        project=self.repository.get_project(project_id)
        if project and project.subtitle_track_id: settings.subtitle_track_id=project.subtitle_track_id
        return settings

    def timeline_blocks(self, project_id: str) -> list[dict[str, object]]:
        return [{"id":s.id,"track":"Dub Voice","kind":"audio","startMs":s.effective_start_ms,
                 "durationMs":s.effective_duration_ms,"sourcePath":s.generated_audio_path,"locked":s.locked,
                 "translationSegmentId":s.translation_segment_id} for s in self.repository.segments(project_id) if s.generated_audio_path]

    def create_subtitles(self, project_id: str, *, bilingual: bool=False, preset_id: str="clean"):
        if self.subtitle_service is None: raise ValueError("Subtitle service is unavailable.")
        project=self.repository.get_project(project_id)
        if project is None or not project.translation_id: raise ValueError("Translation is required before creating dub subtitles.")
        if bilingual:
            if not project.transcript_id: raise ValueError("Transcript is required for bilingual subtitles.")
            track=self.subtitle_service.create_bilingual(project_id,project.transcript_id,project.translation_id,name="Dub Bilingual Subtitles",preset_id=preset_id)
        else:
            track=self.subtitle_service.create_from_translation(project_id,project.translation_id,name=f"{project.target_language.upper()} Dub Subtitles",preset_id=preset_id)
        project.subtitle_track_id=getattr(track,"track_id",getattr(track,"id","")); self.repository.save_project(project)
        return track

    def subtitle_request(self, project_id: str, *, bilingual: bool=False) -> dict[str, object]:
        project=self.repository.get_project(project_id)
        if project is None or not project.translation_id: raise ValueError("Translation is required before creating dub subtitles.")
        return {"projectId":project_id,"translationId":project.translation_id,"targetLanguage":project.target_language,
                "sourceLanguage":project.source_language,"mode":"bilingual" if bilingual else "target"}

    def apply_subtitle_track(self, project_id: str, subtitle_track_id: str) -> None:
        project=self.repository.get_project(project_id)
        if project is None: raise KeyError("Dubbing project not found.")
        project.subtitle_track_id=subtitle_track_id; self.repository.save_project(project)
