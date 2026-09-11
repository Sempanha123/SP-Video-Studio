from domain.playback import LARGE_SEEK_STEP_MS, SEEK_STEP_MS, PlaybackSelection, PlaybackState
from services.playback_service import PlaybackService


def selection(media_type: str = "video", duration: int = 20_000) -> PlaybackSelection:
    return PlaybackSelection(
        media_id="media-1",
        project_id="project-1",
        media_type=media_type,
        name="ព័ត៌មានថ្មី (1).mp4" if media_type == "video" else "sample",
        path=r"C:\Project\media\ព័ត៌មានថ្មី (1).mp4",
        duration_ms=duration,
        width=1920 if media_type != "audio" else None,
        height=1080 if media_type != "audio" else None,
        fps=29.97 if media_type == "video" else None,
        sample_rate=48_000 if media_type == "audio" else None,
        channels=2 if media_type == "audio" else None,
    )


def test_video_selection_enters_loading_state():
    service = PlaybackService()
    service.select(selection())
    assert service.state == PlaybackState.LOADING
    assert service.snapshot.duration_ms == 20_000


def test_image_selection_is_ready_without_fake_duration():
    service = PlaybackService()
    service.select(selection("image", 0))
    assert service.state == PlaybackState.READY
    assert service.selection is not None and not service.selection.playable
    assert service.request_play() == (False, False)


def test_play_pause_and_end_replay_semantics():
    service = PlaybackService()
    service.select(selection())
    service.mark_ready()
    assert service.request_play() == (True, False)
    service.mark_playing()
    assert service.state == PlaybackState.PLAYING
    assert service.request_pause()
    service.mark_paused()
    assert service.state == PlaybackState.PAUSED
    service.mark_ended()
    assert service.state == PlaybackState.ENDED
    assert service.snapshot.position_ms == 20_000
    assert service.request_play() == (True, True)
    assert service.snapshot.position_ms == 0


def test_error_state_prevents_repeated_play_request():
    service = PlaybackService()
    service.select(selection())
    service.mark_error("Unsupported preview codec")
    assert service.state == PlaybackState.ERROR
    assert service.request_play() == (False, False)
    assert "codec" in service.snapshot.error_message


def test_seek_is_clamped_and_relative_seek_works():
    service = PlaybackService()
    service.select(selection(duration=10_000))
    assert service.seek(-500) == 0
    assert service.seek(50_000) == 10_000
    service.seek(4_000)
    assert service.seek_relative(2_500) == 6_500
    assert service.seek_relative(-20_000) == 0


def test_keyboard_seek_uses_shared_constants():
    service = PlaybackService()
    service.select(selection(duration=60_000))
    service.seek(20_000)
    assert service.keyboard_seek(1) == 20_000 + SEEK_STEP_MS
    assert service.keyboard_seek(-1, large=True) == 20_000 + SEEK_STEP_MS - LARGE_SEEK_STEP_MS


def test_volume_clamps_to_ui_range():
    service = PlaybackService()
    assert service.set_volume(140) == 100
    assert service.set_volume(-10) == 0
    assert service.set_volume(47.6) == 48


def test_mute_unmute_restores_previous_volume():
    service = PlaybackService()
    service.set_volume(38)
    assert service.toggle_mute() is True
    assert service.snapshot.previous_volume == 38
    service.set_volume(0)
    assert service.toggle_mute() is False
    assert service.snapshot.volume == 38


def test_clear_resets_transient_playback_but_keeps_volume():
    service = PlaybackService()
    service.set_volume(62)
    service.select(selection())
    service.mark_playing()
    service.set_position(4_000)
    service.clear()
    assert service.selection is None
    assert service.state == PlaybackState.IDLE
    assert service.snapshot.position_ms == 0
    assert service.snapshot.duration_ms == 0
    assert service.snapshot.volume == 62


def test_switching_media_replaces_stale_state():
    service = PlaybackService()
    service.select(selection(duration=50_000))
    service.mark_playing()
    service.set_position(30_000)
    second = selection("audio", 8_000)
    second.media_id = "media-2"
    service.select(second)
    assert service.selection is second
    assert service.snapshot.position_ms == 0
    assert service.snapshot.duration_ms == 8_000
    assert service.state == PlaybackState.LOADING


def test_unknown_duration_disables_meaningful_seek():
    service = PlaybackService()
    service.select(selection(duration=0))
    assert service.seek(5_000) == 0


def test_time_units_remain_numeric_not_formatted_in_state():
    service = PlaybackService()
    service.select(selection(duration=3_723_000))
    assert isinstance(service.snapshot.duration_ms, int)
    assert service.snapshot.duration_ms == 3_723_000
