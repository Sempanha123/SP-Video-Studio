from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def text(path): return (ROOT/path).read_text(encoding='utf-8')

def test_story_workspace_reuses_shared_modules():
    page=text('ui/qml/pages/ProjectWorkspacePage.qml')
    assert 'import "../story"' in page and 'StoryStudio {' in page and 'workspaceMode === "story"' in page
    assert 'text: "Script"' in page and 'text: "Scenes"' in page and 'text: "Timeline"' in page and 'text: "Export"' in page
    assert 'mode === "voices"' in page

def test_story_studio_flow_and_offline_copy():
    studio=text('ui/qml/story/StoryStudio.qml')
    assert all(x in studio for x in ['Story Studio','Idea','Outline','Script']) and '"characters"' in studio
    assert 'offline' in studio.lower() or 'deterministic' in studio.lower()
    setup=text('ui/qml/story/StorySetup.qml'); outline=text('ui/qml/story/StoryOutline.qml')
    assert 'toneBox' in setup and 'audienceBox' in setup and 'durationBox' in setup
    assert 'Fit' in outline and 'Approve' in outline

def test_story_qml_balanced_delimiters():
    for path in (ROOT/'ui/qml/story').glob('*.qml'):
        value=path.read_text(encoding='utf-8')
        assert value.count('{')==value.count('}'), path
        assert value.count('(')==value.count(')'), path
