from pathlib import Path


def test_subtitle_studio_workspace_is_wired():
    workspace=Path('ui/qml/pages/ProjectWorkspacePage.qml').read_text(encoding='utf-8')
    studio=Path('ui/qml/editor/SubtitleStudio.qml').read_text(encoding='utf-8')
    overlay=Path('ui/qml/editor/SubtitlePreviewOverlay.qml').read_text(encoding='utf-8')
    toolbar=Path('ui/qml/editor/SubtitleToolbar.qml').read_text(encoding='utf-8')
    bootstrap=Path('app/bootstrap.py').read_text(encoding='utf-8')
    assert 'text: "Subtitles"' in workspace
    assert 'SubtitleStudio' in workspace and 'SubtitlePreviewOverlay' in workspace
    assert 'subtitleController' in bootstrap and 'SubtitleController' in bootstrap
    assert 'Create Subtitle Track' in studio
    assert 'From Transcript' in studio and 'From Translation' in studio and 'Bilingual' in studio
    assert 'Render Preview' in toolbar
    assert 'activeWord' in overlay and 'word_highlight' in overlay
    assert 'PreviewPlayer' in workspace


def test_subtitle_studio_does_not_expose_future_phase_features():
    text='\n'.join(Path(p).read_text(encoding='utf-8') for p in [
        'ui/qml/editor/SubtitleStudio.qml','ui/qml/editor/SubtitleToolbar.qml','ui/qml/editor/SubtitleStylePanel.qml'
    ])
    for forbidden in ('Generate Scene','Timeline Editor','Render Final Video','Dub Audio','News Workflow'):
        assert forbidden not in text
