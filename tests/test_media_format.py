from ui.models.media_format import format_duration, format_file_size, format_fps, format_resolution


def test_media_display_formatters_are_compact():
    assert format_duration(45_000) == "00:45"
    assert format_duration(3_720_000) == "01:02:00"
    assert format_file_size(12 * 1024 * 1024) == "12.0 MB"
    assert format_resolution(1920, 1080) == "1920 × 1080"
    assert format_resolution(None, None) == ""
    assert format_fps(30.0) == "30 fps"
    assert format_fps(29.97002997) == "29.97 fps"
