from __future__ import annotations

class AudioMixerError(RuntimeError):
    """Base error for the Phase 30 mixer."""

class AudioTrackInvalid(AudioMixerError): pass
class AudioClipMissing(AudioMixerError): pass
class AudioRoutingInvalid(AudioMixerError): pass
class AudioEffectUnavailable(AudioMixerError): pass
class AudioAnalysisFailed(AudioMixerError): pass
class AudioMixFailed(AudioMixerError): pass
class AudioClippingDetected(AudioMixerError): pass
