from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def read(path:str)->str: return (ROOT/path).read_text(encoding='utf-8')


def test_phase17_timeline_qml_components_exist():
    names=['TimelineEditor.qml','TimelineHeader.qml','TimelineRuler.qml','TimelinePlayhead.qml','TimelineTrack.qml','TimelineClip.qml','TimelineClipHandle.qml','TimelineToolbar.qml','TimelineZoomControl.qml','TimelineContextMenu.qml','TimelineSelectionOverlay.qml']
    for name in names: assert (ROOT/'ui/qml/timeline'/name).exists(),name


def test_workspace_storyboard_and_timeline_share_project_module():
    text=read('ui/qml/pages/ProjectWorkspacePage.qml')
    assert 'TimelineEditor' in text and 'timelineController' in text
    assert 'setWorkspaceMode("timeline")' in text
    assert 'SceneEditor' in text  # Storyboard remains available.


def test_timeline_reuses_preview_and_exposes_core_editing():
    text=read('ui/qml/timeline/TimelineEditor.qml')+read('ui/qml/timeline/TimelineToolbar.qml')
    assert 'PreviewPlayer' in text
    for token in ['Split','Duplicate','Delete','Undo','Redo','Marker','Snap','Fit','Frame −','Frame +','Transition Out']:
        assert token in text
    for shortcut in ['Ctrl+B','Ctrl+Z','Ctrl+Y','Ctrl+D']:
        assert shortcut in text


def test_timeline_has_no_new_media_player_or_renderer_commands():
    text='\n'.join(p.read_text(encoding='utf-8') for p in (ROOT/'ui/qml/timeline').glob('*.qml'))
    assert 'MediaPlayer {' not in text
    assert 'ffmpeg' not in text.lower()
    assert 'subprocess' not in text.lower()


def test_track_ui_has_lock_mute_visibility_and_semantic_clips():
    text=read('ui/qml/timeline/TimelineEditor.qml')+read('ui/qml/timeline/TimelineTrack.qml')+read('ui/qml/timeline/TimelineClip.qml')
    assert 'setTrackLocked' in text
    assert 'setTrackMuted' in text or 'muted' in text
    assert 'setTrackVisible' in text or 'visible' in text
    assert 'sourceType' in text and 'durationMs' in text


def test_qml_delimiters_are_balanced():
    for path in (ROOT/'ui/qml/timeline').glob('*.qml'):
        text=path.read_text(encoding='utf-8')
        assert text.count('{')==text.count('}'),path.name
        assert text.count('(')==text.count(')'),path.name
