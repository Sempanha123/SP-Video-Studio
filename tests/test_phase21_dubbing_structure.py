from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_phase21_qml_surface_exists():
    names={"TranslateDubStudio.qml","DubSetup.qml","DubTranscriptPanel.qml","DubTranslationPanel.qml","DubVoicePanel.qml","DubSegmentList.qml","DubSegmentRow.qml","DubTimingInspector.qml","DubAudioMixPanel.qml","DubPreview.qml","DubReadiness.qml"}
    assert names <= {p.name for p in (ROOT/"ui"/"qml"/"dubbing").glob("*.qml")}

def test_no_forbidden_phase21_features_are_added():
    files=list((ROOT/"domain").glob("dub*.py"))+list((ROOT/"services").glob("dubbing*.py"))
    content="\n".join(p.read_text(encoding="utf-8").lower() for p in files)
    assert "celebrity" not in content
    assert "diarizationmodel" not in content.replace("_","")
    assert "lip_sync" not in content

def test_renderer_has_generic_audio_override():
    plan=(ROOT/"rendering"/"render_plan.py").read_text(encoding="utf-8")
    renderer=(ROOT/"rendering"/"renderer.py").read_text(encoding="utf-8")
    assert "primary_audio_override" in plan
    assert "resolved_primary_audio_override" in renderer

def test_phase21_runtime_and_translation_entry_are_wired():
    runtime=(ROOT/"app"/"phase21_runtime.py").read_text(encoding="utf-8")
    page=(ROOT/"ui"/"qml"/"editor"/"TranslationPage.qml").read_text(encoding="utf-8")
    pyproject=(ROOT/"pyproject.toml").read_text(encoding="utf-8")
    assert "qmlRegisterSingletonType" in runtime
    assert "SPVideoStudio.Phase21" in page and "TranslateDubStudio" in page
    assert 'sp-video-studio = "app.phase21_runtime:run"' in pyproject
