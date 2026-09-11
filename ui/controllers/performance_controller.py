from __future__ import annotations

try:
    from PySide6.QtCore import QObject, Property, Signal, Slot
except ImportError:  # test fallback
    class QObject:
        def __init__(self,*a,**k):pass
    class Signal:
        def __init__(self,*a):pass
        def emit(self,*a):pass
    def Slot(*a,**k):return lambda f:f
    def Property(*a,**k):return property


class PerformanceController(QObject):
    changed=Signal(); telemetryChanged=Signal()
    def __init__(self,profiles,telemetry,ai_resources=None,worker_pool=None,parent=None):
        super().__init__(parent);self.profiles=profiles;self.telemetry=telemetry;self.ai_resources=ai_resources;self.worker_pool=worker_pool
        if self.worker_pool and hasattr(self.worker_pool,"set_active_limit"):
            self.worker_pool.set_active_limit(self.profiles.worker_limit)
    @Property(str,notify=changed)
    def profile(self):return self.profiles.profile
    @Property(str,notify=changed)
    def effectiveProfile(self):return self.profiles.effective_profile()
    @Property(str,notify=changed)
    def previewQuality(self):return self.profiles.preview_quality
    @Property(int,notify=changed)
    def workerLimit(self):return self.profiles.worker_limit
    @Property('QVariantMap',notify=telemetryChanged)
    def telemetrySnapshot(self):return self.telemetry.snapshot().to_dict()
    @Slot(str)
    def setProfile(self,value):
        self.profiles.set_profile(value)
        if self.ai_resources and hasattr(self.ai_resources,'set_profile'):self.ai_resources.set_profile(self.profiles.effective_profile())
        self.changed.emit()
    @Slot(str)
    def setPreviewQuality(self,value):self.profiles.set_preview_quality(value);self.changed.emit()
    @Slot(int)
    def setWorkerLimit(self,value):
        self.profiles.set_worker_limit(value)
        if self.worker_pool and hasattr(self.worker_pool,"set_active_limit"):
            self.worker_pool.set_active_limit(self.profiles.worker_limit)
        self.changed.emit()
    @Slot(int,int,result='QVariantMap')
    def previewPolicy(self,active_layers=1,source_height=1080):return self.profiles.preview_policy(active_layers=active_layers,source_height=source_height).to_dict()
    @Slot()
    def refreshTelemetry(self):self.telemetryChanged.emit()
