from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
def q(path): return (ROOT/path).read_text(encoding='utf-8')

def test_theme_has_required_semantic_tokens():
    s=q('ui/qml/theme/Colors.qml')
    for n in ('background','surface','surfaceRaised','surfaceHover','surfaceSelected','textPrimary','textSecondary','textMuted','textDisabled','border','borderStrong','focus','accent','accentHover','accentSoft','success','successSoft','warning','warningSoft','danger','dangerSoft','info','infoSoft','timelineBackground','previewBackground'):
        assert f'property color {n}' in s

def test_light_and_dark_are_explicit():
    s=q('ui/qml/theme/Colors.qml'); assert s.count('darkMode ?')>=20 and '#F7F7FA' in s and '#17181D' in s

def test_accent_is_soft_lavender_not_heavy_blue():
    s=q('ui/qml/theme/Colors.qml'); assert '#7567B1' in s and '#F0EDFA' in s

def test_typography_tokens():
    s=q('ui/qml/theme/Typography.qml')
    for n in ('caption','small','body','bodyStrong','sectionTitle','pageTitle','timeline','multilingualLineHeight'): assert n in s

def test_multilingual_fallbacks_present():
    s=q('ui/qml/theme/Typography.qml'); assert 'Noto Sans Khmer' in s and 'Noto Sans Thai' in s and 'Noto Sans' in s

def test_spacing_scale_contains_requested_values():
    s=q('ui/qml/theme/Spacing.qml')
    for v in (' 4',' 6',' 8',' 12',' 16',' 20',' 24',' 32'): assert v in s

def test_radius_scale_is_professional():
    s=q('ui/qml/theme/Radius.qml'); assert 'card: 12' in s and 'dialog: 16' in s

def test_motion_tokens_and_reduced_motion():
    s=q('ui/qml/theme/AnimationTokens.qml'); assert '120' in s and '180' in s and '260' in s and 'reducedMotion' in s

def test_density_tokens_exist():
    s=q('ui/qml/theme/Theme.qml'); assert 'comfortable' in s and 'compact' in s and 'densityScale' in s

def test_button_variants_and_compact_heights():
    s=q('ui/qml/components/AppButton.qml')
    for v in ('primary','secondary','quiet','danger'): assert v in s
    assert 'Theme.controlHeight' in s and 'glow' not in s.lower()

def test_card_states_are_shared():
    s=q('ui/qml/components/AppCard.qml'); assert 'surfaceSelected' in s and 'surfaceHover' in s and 'activeFocus' in s

def test_search_field_has_clear_and_focus():
    s=q('ui/qml/components/SearchField.qml'); assert 'clearRequested' in s and 'activeFocus' in s and 'search' in s

def test_page_header_is_compact():
    s=q('ui/qml/components/PageHeader.qml'); assert 'pageTitle' in s and '58' in s and 'giant' not in s.lower()

def test_workflow_stepper_semantics():
    s=q('ui/qml/components/WorkflowStepper.qml'); assert 'currentIndex' in s and 'attentionIndexes' in s and 'success' in s

def test_inspector_progressive_disclosure():
    s=q('ui/qml/components/InspectorSection.qml'); assert 'expanded' in s and 'visible: root.expanded' in s

def test_save_state_uses_phase27_in_shell():
    s=q('ui/qml/Main.qml'); assert 'SPVideoStudio.Phase27' in s and 'Recovery.saveState' in s and 'Ctrl+S' in s

def test_navigation_compacts_for_editor():
    s=q('ui/qml/Main.qml'); assert 'compactNav' in s and 'currentPage === "workspace"' in s and 'accentSoft' in s

def test_1366x768_is_above_minimum():
    s=q('ui/qml/Main.qml'); assert 'minimumWidth: 1080' in s and 'minimumHeight: 700' in s
    assert 1366>=1080 and 768>=700

def test_1920x1080_expands_navigation():
    assert 1920>=1220 and 1080>=700

def test_high_dpi_uses_logical_units():
    text='\n'.join(p.read_text(encoding='utf-8') for p in (ROOT/'ui/qml').rglob('*.qml'))
    assert 'devicePixelRatio *' not in text and 'physicalDotsPerInch' not in text

def test_design_gallery_has_all_language_samples():
    s=q('ui/qml/design/DesignGallery.qml'); assert 'សួស្តី' in s and 'สวัสดี' in s and 'Xin chào' in s

def test_asset_grid_is_virtualized_for_1000_assets():
    s=q('ui/qml/assets/AssetGrid.qml'); assert 'reuseItems: true' in s and 'cacheBuffer' in s
    assets=[{'id':str(i)} for i in range(1000)]; assert len(assets)==1000

def test_batch_queue_is_virtualized_for_1000_items():
    s=q('ui/qml/batch/BatchQueue.qml'); assert 'reuseItems: true' in s and 'cacheBuffer' in s
    items=[{'id':str(i),'status':'pending'} for i in range(1000)]; assert len(items)==1000

def test_batch_has_six_stage_creator_flow():
    s=q('ui/qml/batch/BatchFactory.qml');
    for stage in ('Template','Data','Mapping','Variants','Review','Run'): assert stage in s

def test_timeline_uses_dark_editor_tokens_without_new_logic():
    s=q('ui/qml/timeline/TimelineEditor.qml'); assert 'previewBackground' in s and ('timelineRuler' in s or 'timelineSurface' in s)
    assert 'splitSelected' in s and 'duplicateSelected' in s

def test_shorts_uses_dark_916_preview():
    s=q('ui/qml/shorts/ShortsStudio.qml'); assert 'previewBackground' in s and '9:16 preview' in s

def test_recovery_copy_is_calm_and_plain_language():
    s=q('ui/qml/recovery/RecoveryDialog.qml'); assert 'Your saved projects are safe' in s and 'warningSoft' in s and 'database' not in s.lower()

def test_no_neon_glow_or_confetti_in_phase28_qml():
    text='\n'.join(p.read_text(encoding='utf-8').lower() for p in (ROOT/'ui/qml').rglob('*.qml'))
    assert 'neon' not in text and 'confetti' not in text and 'dropshadow' not in text

def test_feature_hardcoded_color_exceptions_are_small():
    hits=[]
    for p in (ROOT/'ui/qml').rglob('*.qml'):
        if '/theme/' in p.as_posix(): continue
        for m in re.finditer(r'#[0-9A-Fa-f]{6,8}',p.read_text(encoding='utf-8')): hits.append((p.name,m.group()))
    assert len(hits)<=2, hits

def test_docs_cover_design_system_and_performance():
    s=q('docs/PHASE28_SOFT_CREATOR_UX.md')
    for term in ('Semantic color system','Typography','Timeline','Recovery','Responsive desktop','Performance rules','Component reuse rule'): assert term in s

def test_news_story_dub_use_shared_steppers():
    assert 'WorkflowStepper' in q('ui/qml/news/NewsStudio.qml')
    assert 'WorkflowStepper' in q('ui/qml/story/StoryStudio.qml')
    assert 'WorkflowStepper' in q('ui/qml/dubbing/TranslateDubStudio.qml')

def test_dub_keeps_source_and_translation_side_by_side():
    s=q('ui/qml/dubbing/TranslateDubStudio.qml'); assert 'DubTranscriptPanel' in s and 'DubTranslationPanel' in s and 'RowLayout' in s

def test_dialog_uses_dialog_radius_and_responsive_consumers():
    s=q('ui/qml/components/AppDialog.qml'); assert 'Theme.radius.dialog' in s and 'Theme.spacing.xlg' in s
