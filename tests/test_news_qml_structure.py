from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_news_studio_files_and_source_first_language():
    base=ROOT/'ui'/'qml'/'news'
    names={'NewsStudio.qml','NewsSetup.qml','NewsSources.qml','NewsSourceCard.qml','NewsSourceInspector.qml','NewsClaims.qml','NewsClaimRow.qml','NewsBrief.qml','NewsScriptBuilder.qml','NewsReadiness.qml'}
    assert names <= {p.name for p in base.glob('*.qml')}
    text=(base/'NewsStudio.qml').read_text(encoding='utf-8')
    assert 'Sources → Facts → Brief → Script → Video' in text
    assert 'chat' not in text.lower()

def test_news_uses_existing_workspaces_not_duplicate_editors():
    page=(ROOT/'ui'/'qml'/'pages'/'ProjectWorkspacePage.qml').read_text(encoding='utf-8')
    assert 'NewsStudio {' in page and 'workspaceMode === "news"' in page
    news=(ROOT/'ui'/'qml'/'news'/'NewsScriptBuilder.qml').read_text(encoding='utf-8')
    assert 'Open Script Editor' in news and 'Create Scenes' in news and 'Translate' in news

def test_news_qml_delimiters_balanced():
    for p in (ROOT/'ui'/'qml'/'news').glob('*.qml'):
        text=p.read_text(encoding='utf-8')
        assert text.count('{')==text.count('}'),p.name
        assert text.count('(')==text.count(')'),p.name
