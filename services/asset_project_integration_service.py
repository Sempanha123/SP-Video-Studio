from __future__ import annotations

class AssetProjectIntegrationService:
    """One-operation helpers used by News/Story/Shorts/normal Timeline drop targets."""
    def __init__(self,usage,universal_video_service=None):self.usage=usage;self.universal=universal_video_service
    def add_at_playhead(self,project_id:str,asset_id:str,playhead_ms:int=0,track:str='auto'):
        media=self.usage.add_to_project(project_id,asset_id,'timeline')
        if self.universal is not None:
            return self.universal.add_media_at_playhead(project_id,media.id,int(playhead_ms),track)
        return media.id
    def add_to_scene(self,project_id:str,scene_id:str,asset_id:str,role:str='broll',speaker_id:str=''):
        return self.usage.add_visual_layer(project_id,scene_id,asset_id,role=role,speaker_id=speaker_id)
