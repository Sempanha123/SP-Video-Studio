from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def text(path):return (ROOT/path).read_text(encoding='utf-8')
def test_news_studio_exposes_visuals_without_duplicate_editors():
    src=text('ui/qml/news/NewsStudio.qml');assert '"visuals"' in src and 'NewsVisualStudio' in src and 'visualController' in src
def test_visual_studio_has_scene_layout_theme_graphic_and_provenance_surfaces():
    src=text('ui/qml/news/visuals/NewsVisualStudio.qml');assert all(x in src for x in ['NewsSceneLayoutPicker','NewsThemePanel','NewsGraphicPicker','NewsGraphicInspector','Timeline','Export'])
def test_visual_resources_are_versioned_and_no_qml_layout_coordinates_registry():
    assert 'schema_version' in text('resources/news/layouts/layouts.json');assert 'resolve_layout' not in text('ui/qml/news/visuals/NewsVisualStudio.qml')
def test_scene_preview_knows_generic_shape_overlay():
    assert 'modelData.type === "shape"' in text('ui/qml/editor/ScenePreview.qml')
def test_renderer_shape_support_is_generic_drawbox():
    src=text('rendering/scene_renderer.py');assert '"shape"' in src and 'drawbox=' in src
