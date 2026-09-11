from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT/path).read_text(encoding='utf-8')


def test_workspace_exposes_scene_storyboard():
    workspace=text('ui/qml/pages/ProjectWorkspacePage.qml')
    assert 'text: "Scenes"' in workspace
    assert 'workspaceMode === "scenes"' in workspace
    assert 'SceneEditor {' in workspace
    assert 'sceneController.setCurrentProject' in workspace


def test_scene_editor_contains_phase13_core_actions():
    editor=text('ui/qml/editor/SceneEditor.qml')+text('ui/qml/editor/SceneList.qml')+text('ui/qml/editor/SceneInspector.qml')+text('ui/qml/editor/SceneOverlayEditor.qml')+text('ui/qml/editor/SceneTransitionPicker.qml')
    for phrase in ['Add Scene','From Script','From Transcript','Choose Media','Narration','Subtitles','Text & Overlays','Transition','Delete Scene']:
        assert phrase in editor
    assert 'AI Director' not in editor
    assert 'Render Video' not in editor
    assert 'Timeline' not in editor


def test_scene_preview_reuses_controller_and_normalized_overlay_layout():
    preview=text('ui/qml/editor/ScenePreview.qml')
    assert 'controller.playScene(true)' in preview
    assert '(modelData.x || 0) * parent.width' in preview
    assert '(modelData.y || 0) * parent.height' in preview
    assert 'MediaPlayer {' not in preview


def test_scene_controller_is_registered_in_bootstrap():
    bootstrap=text('app/bootstrap.py')
    assert 'SceneController' in bootstrap
    assert 'setContextProperty("sceneController", scene_controller)' in bootstrap
    assert 'scene_controller.playbackRequested.connect' in bootstrap
