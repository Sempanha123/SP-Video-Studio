from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, replace
from enum import StrEnum
from pathlib import Path
from typing import Any, Mapping

from domain.accessibility_settings import SUPPORTED_INTERFACE_TEXT_SIZES, SUPPORTED_REDUCE_MOTION_MODES
from domain.schema_version import SETTINGS_SCHEMA_VERSION

SETTINGS_VERSION = SETTINGS_SCHEMA_VERSION
SUPPORTED_SETTING_FPS = (24,25,30,50,60)
SUPPORTED_SETTING_ASPECT_RATIOS = ("9:16","16:9","1:1")

class ThemeMode(StrEnum): SYSTEM="system"; LIGHT="light"; DARK="dark"
class PerformanceProfile(StrEnum): AUTO="auto"; LOW_MEMORY="low_memory"; BALANCED="balanced"; MAXIMUM_QUALITY="maximum_quality"
class PreferredEncoder(StrEnum): AUTO="auto"

PERFORMANCE_PROFILE_GUIDANCE={
    PerformanceProfile.AUTO.value:{"memory":"adaptive","concurrency":"adaptive","caching":"adaptive","quality":"adaptive"},
    PerformanceProfile.LOW_MEMORY.value:{"memory":"low","concurrency":"low","caching":"low","quality":"efficient"},
    PerformanceProfile.BALANCED.value:{"memory":"moderate","concurrency":"moderate","caching":"moderate","quality":"normal"},
    PerformanceProfile.MAXIMUM_QUALITY.value:{"memory":"high","concurrency":"moderate","caching":"high","quality":"maximum"},
}

@dataclass(slots=True)
class AppSettings:
    settings_version:int=SETTINGS_VERSION
    language:str="en"; theme:str=ThemeMode.SYSTEM.value; open_last_project:bool=False; show_welcome_home:bool=True
    default_projects_folder:str=""; performance_profile:str=PerformanceProfile.AUTO.value
    default_fps:int=30; default_aspect_ratio:str="16:9"; preferred_encoder:str=PreferredEncoder.AUTO.value
    ffmpeg_mode:str="auto"; ffmpeg_path:str=""; ffprobe_path:str=""; debug_logging:bool=False
    show_technical_error_details:bool=False; readiness_check_on_startup:bool=True
    shortcut_overrides:dict[str,str]=field(default_factory=dict)
    reduce_motion:str="system"; interface_text_size:str="default"; stronger_focus_indicator:bool=False
    # Original payload is retained so unknown future/third-party settings are never silently discarded.
    extra_payload:dict[str,Any]=field(default_factory=dict,repr=False)

    @classmethod
    def defaults(cls,project_root:Path)->"AppSettings": return cls(default_projects_folder=str(Path(project_root).expanduser()))

    def validate(self)->None:
        if self.settings_version!=SETTINGS_VERSION:raise ValueError("Unsupported settings version.")
        if self.language not in {"en","km"}:raise ValueError("Unsupported application language.")
        if self.theme not in {x.value for x in ThemeMode}:raise ValueError("Unsupported theme setting.")
        if self.performance_profile not in {x.value for x in PerformanceProfile}:raise ValueError("Unsupported performance profile.")
        if self.default_fps not in SUPPORTED_SETTING_FPS:raise ValueError("Unsupported default FPS.")
        if self.default_aspect_ratio not in SUPPORTED_SETTING_ASPECT_RATIOS:raise ValueError("Unsupported default aspect ratio.")
        if self.preferred_encoder!=PreferredEncoder.AUTO.value:raise ValueError("Unsupported encoder preference.")
        if self.ffmpeg_mode not in {"auto","custom"}:raise ValueError("Unsupported FFmpeg discovery mode.")
        if not self.default_projects_folder.strip():raise ValueError("Default projects folder is required.")
        if not isinstance(self.shortcut_overrides,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in self.shortcut_overrides.items()):raise ValueError("Keyboard shortcut overrides must use command IDs and key sequences.")
        if self.reduce_motion not in SUPPORTED_REDUCE_MOTION_MODES:raise ValueError("Unsupported Reduce Motion preference.")
        if self.interface_text_size not in SUPPORTED_INTERFACE_TEXT_SIZES:raise ValueError("Unsupported interface text size.")

    def with_changes(self,**changes:Any)->"AppSettings":
        updated=replace(self,**changes);updated.validate();return updated

    def to_dict(self)->dict[str,Any]:
        result=deepcopy(self.extra_payload) if isinstance(self.extra_payload,dict) else {}
        result["settings_version"]=self.settings_version
        def section(name:str)->dict[str,Any]:
            value=result.get(name);return dict(value) if isinstance(value,Mapping) else {}
        general=section("general");general.update(language=self.language,open_last_project=self.open_last_project,show_welcome_home=self.show_welcome_home);result["general"]=general
        appearance=section("appearance");appearance["theme"]=self.theme;result["appearance"]=appearance
        projects=section("projects");projects["default_projects_folder"]=self.default_projects_folder;result["projects"]=projects
        performance=section("performance");performance["profile"]=self.performance_profile;result["performance"]=performance
        rendering=section("rendering");rendering.update(default_fps=self.default_fps,default_aspect_ratio=self.default_aspect_ratio,preferred_encoder=self.preferred_encoder);result["rendering"]=rendering
        media=section("media_tools");media.update(ffmpeg_mode=self.ffmpeg_mode,ffmpeg_path=self.ffmpeg_path,ffprobe_path=self.ffprobe_path);result["media_tools"]=media
        advanced=section("advanced");advanced.update(debug_logging=self.debug_logging,show_technical_error_details=self.show_technical_error_details,readiness_check_on_startup=self.readiness_check_on_startup);result["advanced"]=advanced
        shortcuts=section("keyboard_shortcuts");shortcuts["overrides"]=dict(self.shortcut_overrides);result["keyboard_shortcuts"]=shortcuts
        access=section("accessibility");access.update(reduce_motion=self.reduce_motion,interface_text_size=self.interface_text_size,stronger_focus_indicator=self.stronger_focus_indicator);result["accessibility"]=access
        return result

    @classmethod
    def from_dict(cls,payload:Mapping[str,Any],default_project_root:Path)->"AppSettings":
        general=_mapping(payload.get("general"));appearance=_mapping(payload.get("appearance"));projects=_mapping(payload.get("projects"));performance=_mapping(payload.get("performance"));rendering=_mapping(payload.get("rendering"));media_tools=_mapping(payload.get("media_tools"));advanced=_mapping(payload.get("advanced"));keyboard=_mapping(payload.get("keyboard_shortcuts"));access=_mapping(payload.get("accessibility"));overrides=_mapping(keyboard.get("overrides"))
        settings=cls(
            settings_version=int(payload.get("settings_version",SETTINGS_VERSION)),language=str(general.get("language","en")),theme=str(appearance.get("theme",ThemeMode.SYSTEM.value)),open_last_project=bool(general.get("open_last_project",False)),show_welcome_home=bool(general.get("show_welcome_home",True)),default_projects_folder=str(projects.get("default_projects_folder",str(default_project_root))),performance_profile=str(performance.get("profile",PerformanceProfile.AUTO.value)),default_fps=int(rendering.get("default_fps",30)),default_aspect_ratio=str(rendering.get("default_aspect_ratio","16:9")),preferred_encoder=str(rendering.get("preferred_encoder","auto")),ffmpeg_mode=str(media_tools.get("ffmpeg_mode","auto")),ffmpeg_path=str(media_tools.get("ffmpeg_path","")),ffprobe_path=str(media_tools.get("ffprobe_path","")),debug_logging=bool(advanced.get("debug_logging",False)),show_technical_error_details=bool(advanced.get("show_technical_error_details",False)),readiness_check_on_startup=bool(advanced.get("readiness_check_on_startup",True)),shortcut_overrides={str(k):str(v) for k,v in overrides.items() if str(k).strip()},reduce_motion=str(access.get("reduce_motion","system")),interface_text_size=str(access.get("interface_text_size","default")),stronger_focus_indicator=bool(access.get("stronger_focus_indicator",False)),extra_payload=deepcopy(dict(payload)),
        );settings.validate();return settings

def _mapping(value:Any)->Mapping[str,Any]:return value if isinstance(value,Mapping) else {}
