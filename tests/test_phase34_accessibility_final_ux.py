from __future__ import annotations

from pathlib import Path

from domain.accessibility_settings import AccessibilitySettings
from domain.settings import AppSettings
from services.accessibility_service import AccessibilityService
from services.focus_navigation_service import FocusNavigationService

ROOT = Path(__file__).resolve().parents[1]
QML = ROOT / "ui" / "qml"


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _hex_luminance(value: str) -> float:
    value = value.lstrip("#")
    rgb = [int(value[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
    linear = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in rgb]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(a: str, b: str) -> float:
    x, y = _hex_luminance(a), _hex_luminance(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


class _Current:
    reduce_motion = "system"
    interface_text_size = "default"
    stronger_focus_indicator = False


class _FakeSettings:
    def __init__(self):
        self.current = _Current()
        self.changes = {}

    def update(self, **changes):
        self.changes.update(changes)
        for key, value in changes.items():
            setattr(self.current, key, value)
        return self.current


def test_accessibility_settings_validate_and_scale():
    prefs = AccessibilitySettings(reduce_motion="on", interface_text_size="large", stronger_focus_indicator=True)
    prefs.validate()
    assert prefs.text_scale == 1.12


def test_accessibility_settings_round_trip_in_existing_settings_document(tmp_path):
    settings = AppSettings.defaults(tmp_path)
    settings = settings.with_changes(
        reduce_motion="on", interface_text_size="large", stronger_focus_indicator=True
    )
    restored = AppSettings.from_dict(settings.to_dict(), tmp_path)
    assert restored.reduce_motion == "on"
    assert restored.interface_text_size == "large"
    assert restored.stronger_focus_indicator is True


def test_old_settings_documents_keep_phase34_defaults(tmp_path):
    payload = AppSettings.defaults(tmp_path).to_dict()
    payload.pop("accessibility")
    restored = AppSettings.from_dict(payload, tmp_path)
    assert restored.reduce_motion == "system"
    assert restored.interface_text_size == "default"
    assert restored.stronger_focus_indicator is False


def test_accessibility_service_persists_preferences(monkeypatch):
    store = _FakeSettings()
    service = AccessibilityService(store)
    monkeypatch.setattr(service, "system_prefers_reduced_motion", lambda: True)
    assert service.current().reduce_motion_effective is True
    service.set_reduce_motion("off")
    service.set_interface_text_size("large")
    service.set_stronger_focus_indicator(True)
    state = service.current()
    assert state.reduce_motion_effective is False
    assert state.text_scale == 1.12
    assert state.stronger_focus_indicator is True


def test_focus_navigation_is_bounded_and_predictable():
    assert FocusNavigationService.next_index(0, 4, 1) == 1
    assert FocusNavigationService.next_index(3, 4, 1) == 3
    assert FocusNavigationService.next_index(0, 4, -1) == 0
    assert FocusNavigationService.nearest_index([100, 500, 900], 640) == 1


def test_shared_controls_have_accessibility_metadata_and_delayed_tooltips():
    for file in ["AppButton.qml", "IconButton.qml", "AppTextField.qml", "AppComboBox.qml", "AppSwitch.qml"]:
        source = _text(f"ui/qml/components/{file}")
        assert "Accessible.name" in source
        assert "Accessible.role" in source
    assert "Theme.tooltipDelay" in _text("ui/qml/components/IconButton.qml")
    assert "visualFocus" in _text("ui/qml/components/AppButton.qml")


def test_dialog_restores_focus_and_accepts_initial_focus():
    source = _text("ui/qml/components/AppDialog.qml")
    assert "previousFocusItem" in source
    assert "initialFocusItem" in source
    assert "onAboutToShow" in source
    assert "onClosed" in source
    assert "forceActiveFocus" in source


def test_focus_ring_is_separate_from_selection():
    card = _text("ui/qml/components/AppCard.qml")
    ring = _text("ui/qml/accessibility/FocusRing.qml")
    assert "selected ? Theme.colors.surfaceSelected" in card
    assert "FocusRing" in card
    assert "Theme.focusWidth" in ring


def test_reduce_motion_drives_shared_animation_tokens():
    theme = _text("ui/qml/theme/Theme.qml")
    animation = _text("ui/qml/theme/AnimationTokens.qml")
    assert "reducedMotion" in theme
    assert "AnimationTokens { reducedMotion: root.reducedMotion }" in theme
    assert "reducedMotion ? 0" in animation


def test_interface_text_size_scales_typography_without_extreme_scale():
    theme = _text("ui/qml/theme/Theme.qml")
    typography = _text("ui/qml/theme/Typography.qml")
    assert 'interfaceTextSize === "large" ? 1.12 : 1.0' in theme
    assert "function px(base)" in typography
    assert "multilingualLineHeight: 1.58" in typography


def test_light_and_dark_contrast_tokens_meet_phase34_targets():
    # Values are the semantic tokens intentionally selected in Phase 34.
    pairs = [
        ("#25232B", "#FFFFFF", 4.5),
        ("#615D6A", "#FFFFFF", 4.5),
        ("#6F6A78", "#FFFFFF", 4.5),
        ("#F1F0F5", "#1E2026", 4.5),
        ("#BBB8C4", "#1E2026", 4.5),
        ("#A39EAC", "#1E2026", 4.5),
        ("#36785F", "#ECF6F1", 4.5),
        ("#8B6328", "#FBF4E8", 4.5),
        ("#9F4752", "#F9ECEE", 4.5),
        ("#476B8C", "#EDF3F8", 4.5),
    ]
    for fg, bg, minimum in pairs:
        assert _contrast(fg, bg) >= minimum


def test_status_badges_do_not_depend_on_color_only():
    source = _text("ui/qml/components/StatusBadge.qml")
    for symbol in ["⚠", "↻", "✓", "!"]:
        assert symbol in source
    assert "Accessible.name" in source


def test_main_applies_persisted_accessibility_before_showing_window():
    source = _text("ui/qml/Main.qml")
    assert "visible: false" in source
    assert "applyAccessibilitySettings" in source
    assert "window.visible=true" in source


def test_bootstrap_preserves_fractional_high_dpi_scale_factors():
    source = _text("app/bootstrap.py")
    assert "HighDpiScaleFactorRoundingPolicy.PassThrough" in source


def test_1366_class_layout_keeps_compact_navigation_and_workspace_minimums():
    main = _text("ui/qml/Main.qml")
    timeline = _text("ui/qml/timeline/TimelineEditor.qml")
    assert "width: 1360" in main
    assert "minimumWidth: 1080" in main
    assert "width < 1220" in main
    assert "SplitView.minimumWidth:420" in timeline or "SplitView.minimumWidth: 420" in timeline
    assert "SplitView.minimumWidth:380" in timeline or "SplitView.minimumWidth: 380" in timeline


def test_timeline_is_one_keyboard_region_and_exposes_playhead_text():
    editor = _text("ui/qml/timeline/TimelineEditor.qml")
    clip = _text("ui/qml/timeline/TimelineClip.qml")
    controller = _text("ui/controllers/timeline_controller.py")
    assert "activeFocusOnTab" in editor
    assert "selectRelativeClip" in editor
    assert "playheadAccessibleText" in controller
    assert "Accessible.name" in clip
    assert "activeFocusOnTab: false" in clip


def test_speech_table_has_row_navigation_edit_escape_and_multilingual_line_height():
    editor = _text("ui/qml/speech/SpeechEditor.qml")
    row = _text("ui/qml/speech/SpeechRow.qml")
    assert "Keys.onUpPressed" in editor
    assert "Keys.onDownPressed" in editor
    assert "Keys.onReturnPressed" in editor
    assert "Keys.onEscapePressed" in editor
    assert "Accessible.name" in row
    assert "Start time" in row and "End time" in row
    assert "multilingualLineHeight" in row


def test_subtitle_editor_has_accessible_rows_and_keyboard_selection():
    editor = _text("ui/qml/editor/SubtitleStudio.qml")
    row = _text("ui/qml/editor/SubtitleCueRow.qml")
    assert "selectRelativeCue" in editor
    assert "Accessible.role: Accessible.ListItem" in row
    assert 'Accessible.name: "Subtitle text"' in row
    assert "multilingualLineHeight" in row


def test_audio_faders_have_names_values_and_keyboard_commit_paths():
    files = ["MixerTrack.qml", "MixerStrip.qml", "MixerBus.qml", "MasterStrip.qml", "DuckingPanel.qml"]
    combined = "\n".join(_text(f"ui/qml/audio/{name}") for name in files)
    assert "Accessible.role: Accessible.Slider" in combined or "Accessible.role:Accessible.Slider" in combined
    assert "decibels" in combined
    assert "activeFocus" in combined
    assert "onValueChanged" in combined


def test_language_picker_uses_native_and_display_names_with_support_text():
    source = _text("ui/qml/components/LanguagePicker.qml")
    assert "nativeName" in source
    assert "displayName" in source
    for label in ["Supported", "Model Required", "Partially Supported", "Unsupported"]:
        assert label in source
    assert "flag" not in source.lower()


def test_multilingual_samples_are_preserved_in_accessibility_preview():
    source = _text("ui/qml/accessibility/AccessibilityPreview.qml")
    assert "អ្នករាយការណ៍" in source
    assert "ผู้สื่อข่าว" in source
    assert "Phóng viên" in source


def test_assets_templates_batch_and_speech_have_actionable_empty_states():
    checks = {
        "ui/qml/assets/AssetGrid.qml": "No reusable assets yet",
        "ui/qml/pages/TemplatesPage.qml": "No templates found",
        "ui/qml/batch/BatchQueue.qml": "No Batch Items yet",
        "ui/qml/speech/SpeechEditor.qml": "No speech blocks yet",
    }
    for file, phrase in checks.items():
        assert phrase in _text(file)


def test_project_creation_uses_inline_validation():
    source = _text("ui/qml/pages/CreatePage.qml")
    assert "Project name is required." in source
    assert "projectNameError" in source
    assert "Accessible.AlertMessage" in source


def test_error_toast_filters_obvious_raw_technical_errors():
    source = _text("ui/qml/components/Toast.qml")
    assert "Traceback" in source
    assert "sqlite3." in source
    assert "filter_complex" in source
    assert "technicalMessage" in source


def test_phase33_command_module_import_is_consistent():
    wrong = []
    for path in QML.rglob("*.qml"):
        if "SPVideoStudio.Phase33" in path.read_text(encoding="utf-8"):
            wrong.append(str(path.relative_to(ROOT)))
    assert wrong == []


def test_phase34_runtime_layers_on_phase33_without_replacing_business_logic():
    source = _text("app/phase34_runtime.py")
    assert "phase33_runtime" in source
    assert "return run_phase33()" in source
    assert "phase35" not in source.lower()


def test_settings_page_exposes_real_accessibility_controls():
    source = _text("ui/qml/pages/SettingsPage.qml")
    assert '"Accessibility"' in source
    assert "Reduce Motion" in source
    assert "Interface Text Size" in source
    assert "Stronger Focus Indicator" in source
    assert "High Contrast" not in source


def test_phase34_does_not_introduce_continuous_decorative_animation():
    # Shared motion is finite Behavior animation; no looping Sequential/Parallel animation.
    sources = "\n".join(path.read_text(encoding="utf-8") for path in QML.rglob("*.qml"))
    assert "loops: Animation.Infinite" not in sources
    assert "loops: -1" not in sources


def test_main_entrypoint_and_script_use_phase34_runtime():
    assert "app.phase34_runtime" in _text("main.py")
    assert 'sp-video-studio = "app.phase34_runtime:run"' in _text("pyproject.toml")


def test_shared_app_dialog_suppresses_background_commands_and_restores_focus():
    source = _text("ui/qml/components/AppDialog.qml")
    assert "SPVideoStudio.Commands" in source
    assert "Commands.setModalOpen(true)" in source
    assert "Commands.setModalOpen(false)" in source
    assert "previousFocusItem" in source


def test_export_flow_has_keyboard_modal_progress_and_completion_semantics():
    page = _text("ui/qml/export/ExportPage.qml")
    progress = _text("ui/qml/export/ExportProgress.qml")
    complete = _text("ui/qml/export/ExportComplete.qml")
    preset = _text("ui/qml/export/ExportPresetCard.qml")
    settings = _text("ui/qml/export/ExportSettingsPanel.qml")
    assert "AppDialog" in page and "initialFocusItem: presetName" in page
    assert "Cancel Export" in progress and "Cancelling…" in progress
    assert "indeterminateStage" in progress
    assert "Export complete" in complete
    assert "interactive: true" in preset and "accessibleName" in preset
    for label in ["Export width", "Export height", "Export FPS", "Output folder", "Export filename"]:
        assert label in settings
