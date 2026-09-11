from __future__ import annotations
import logging
from pathlib import Path
try:
    from PySide6.QtCore import QObject,Property,Signal,Slot
except ImportError:
    class QObject:
        def __init__(self,*a,**k):pass
    class Signal:
        def __init__(self,*a,**k):pass
        def emit(self,*a,**k):pass
    def Slot(*a,**k):return lambda fn:fn
    def Property(*a,**k):return lambda fn:property(fn)

class AudioMixerController(QObject):
    mixerChanged=Signal();selectionChanged=Signal();operationSucceeded=Signal(str);operationFailed=Signal(str);previewReady=Signal(str)
    def __init__(self,mixer,waveforms,analysis,renderer,validation,*,worker_pool=None,logger=None,parent=None):
        super().__init__(parent);self.mixer=mixer;self.waveforms=waveforms;self.analysis=analysis;self.renderer=renderer;self.validation=validation;self.worker_pool=worker_pool;self.logger=logger or logging.getLogger('sp_video_studio.audio_mixer');self._project_id='';self._workflow='video';self._state={'tracks':[],'buses':[],'effects':[],'duckingRules':[],'master':{}};self._selected_track='';self._timeline_clips=[];self._duration_ms=0
    @Property(str,notify=mixerChanged)
    def currentProjectId(self):return self._project_id
    @Property('QVariantList',notify=mixerChanged)
    def tracks(self):return list(self._state.get('tracks') or [])
    @Property('QVariantList',notify=mixerChanged)
    def buses(self):return list(self._state.get('buses') or [])
    @Property('QVariantList',notify=mixerChanged)
    def duckingRules(self):return list(self._state.get('duckingRules') or [])
    @Property('QVariantList',notify=mixerChanged)
    def effects(self):return list(self._state.get('effects') or [])
    @Property('QVariantMap',notify=mixerChanged)
    def master(self):return dict(self._state.get('master') or {})
    @Property('QVariantMap',notify=selectionChanged)
    def selectedTrack(self):
        return next((dict(x) for x in self.tracks if str(x.get('id') or '')==self._selected_track),{})
    @Property(str,notify=selectionChanged)
    def selectedTrackId(self):return self._selected_track
    @Slot(str,str)
    def setProject(self,project_id,workflow='video'):
        self._project_id=str(project_id or '');self._workflow=str(workflow or 'video');self.refresh()
    @Slot()
    def refresh(self):
        if not self._project_id:self._state={'tracks':[],'buses':[],'effects':[],'duckingRules':[],'master':{}};self.mixerChanged.emit();return
        try:self._state=self.mixer.ensure_project(self._project_id,self._workflow);self.mixerChanged.emit()
        except Exception as exc:self._fail(exc)
    @Slot('QVariantList',int)
    def setTimelineState(self,clips,duration_ms):self._timeline_clips=[dict(x) for x in list(clips or [])];self._duration_ms=max(0,int(duration_ms or 0))
    @Slot(str)
    def selectTrack(self,track_id):self._selected_track=str(track_id or '');self.selectionChanged.emit()
    @Slot(str,float,result=bool)
    def setTrackGain(self,track_id,value):return self._update_track(track_id,gainDb=float(value))
    @Slot(str,float,result=bool)
    def setTrackPan(self,track_id,value):return self._update_track(track_id,pan=float(value))
    @Slot(str,bool,result=bool)
    def setTrackMuted(self,track_id,value):return self._update_track(track_id,muted=bool(value))
    @Slot(str,bool,result=bool)
    def setTrackSolo(self,track_id,value):return self._update_track(track_id,solo=bool(value))
    @Slot(str,str,result=bool)
    def renameTrack(self,track_id,name):return self._update_track(track_id,name=str(name))
    @Slot(float,result=bool)
    def setMasterGain(self,value):
        try:self.mixer.set_master_gain(self._project_id,float(value));self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(bool,result=bool)
    def setMasterLimiter(self,value):
        try:self.mixer.update_master(self._project_id,limiterEnabled=bool(value));self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(bool,float,result=bool)
    def setNormalization(self,enabled,target_lufs=-16.0):
        try:self.mixer.update_master(self._project_id,normalizationEnabled=bool(enabled),normalizationTargetLufs=float(target_lufs));self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,float,result=bool)
    def setBusGain(self,bus_id,value):
        try:self.mixer.update_bus(self._project_id,str(bus_id),gainDb=float(value));self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,bool,result=bool)
    def setBusMuted(self,bus_id,value):
        try:self.mixer.update_bus(self._project_id,str(bus_id),muted=bool(value));self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,str,result=bool)
    def addTrackEffectPreset(self,track_id,preset):
        try:self.mixer.add_voice_effect_preset(self._project_id,str(track_id),str(preset));self.refresh();self.operationSucceeded.emit('Audio effect preset added.');return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,result=bool)
    def applyPreset(self,name):
        try:self._state=self.mixer.apply_preset(self._project_id,str(name));self.mixerChanged.emit();self.operationSucceeded.emit('Audio preset applied.');return True
        except Exception as exc:self._fail(exc);return False
    @Slot(bool,float,result=bool)
    def setMusicDucking(self,enabled,amount_db=-12.0):
        try:self.mixer.set_music_ducking(self._project_id,bool(enabled),float(amount_db));self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    @Slot(str,str,result='QVariantMap')
    def addTrack(self,name,role):
        try:x=self.mixer.add_track(self._project_id,str(name),str(role));self.refresh();return x.to_dict()
        except Exception as exc:self._fail(exc);return {}
    @Slot(str,result='QVariantMap')
    def waveform(self,path):
        try:return self.waveforms.generate(str(path),buckets=900)
        except Exception:return {'buckets':[],'cacheHit':False}
    @Slot(result='QVariantMap')
    def mixSpec(self):
        try:return self._resolved_mix_spec()
        except Exception as exc:self._fail(exc);return {}
    @Slot(result='QVariantList')
    def validateMix(self):
        try:return self.validation.validate_mix(self._resolved_mix_spec(),project_duration_ms=self._duration_ms)
        except Exception as exc:self._fail(exc);return []
    @Slot(result=str)
    def renderPreview(self):
        try:
            spec=self._resolved_mix_spec();target=self.renderer.preview_path(spec,self._project_id)
            if target is None:return ''
            if not target.exists():self.renderer.render_mix(spec,target)
            self.previewReady.emit(str(target));return str(target)
        except Exception as exc:self._fail(exc);return ''
    def _resolved_mix_spec(self):
        if self._timeline_clips:
            return self.mixer.build_mix_spec(self._project_id,self._timeline_clips,self._duration_ms)
        return self.mixer.build_project_mix_spec(self._project_id,self._duration_ms)
    def _update_track(self,track_id,**updates):
        try:self.mixer.update_track(self._project_id,str(track_id),**updates);self.refresh();return True
        except Exception as exc:self._fail(exc);return False
    def _fail(self,exc):
        if self.logger:self.logger.exception('Audio mixer operation failed')
        self.operationFailed.emit(str(exc).strip() or 'Audio mixer action could not be completed.')
