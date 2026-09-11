from __future__ import annotations

import importlib.util
import sqlite3
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def load_speech_block_module():
    # Isolate the canonical model so this Phase-only patch can be verified even
    # when the cumulative repository is not mounted in the test sandbox.
    lang = types.ModuleType("domain.language")
    lang.supported_language_codes = lambda: {"en", "km", "th", "vi"}
    project = types.ModuleType("domain.project")
    project.utc_now_iso = lambda: "2026-09-12T00:00:00+00:00"
    errors = types.ModuleType("domain.phase22_errors")
    class SpeechBlockInvalid(ValueError):
        pass
    errors.SpeechBlockInvalid = SpeechBlockInvalid
    sys.modules.setdefault("domain", types.ModuleType("domain"))
    sys.modules["domain.language"] = lang
    sys.modules["domain.project"] = project
    sys.modules["domain.phase22_errors"] = errors
    spec = importlib.util.spec_from_file_location("phase32_speech_block", ROOT / "domain/speech_block.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def migration_connection():
    c = sqlite3.connect(":memory:")
    c.executescript(
        """
        CREATE TABLE projects(id TEXT PRIMARY KEY);
        CREATE TABLE scripts(id TEXT PRIMARY KEY,project_id TEXT);
        CREATE TABLE script_sections(id TEXT PRIMARY KEY,script_id TEXT);
        CREATE TABLE speech_blocks(
          id TEXT PRIMARY KEY,script_section_id TEXT NOT NULL,block_order INTEGER NOT NULL,speaker_id TEXT,
          text TEXT NOT NULL DEFAULT '',language TEXT NOT NULL DEFAULT 'en',voice_override_id TEXT NOT NULL DEFAULT '',
          speech_source_type TEXT NOT NULL DEFAULT 'tts',pause_before_ms INTEGER NOT NULL DEFAULT 0,
          pause_after_ms INTEGER NOT NULL DEFAULT 180,scene_id TEXT,start_offset_ms INTEGER,audio_id TEXT NOT NULL DEFAULT '',
          metadata_json TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL,updated_at TEXT NOT NULL
        );
        CREATE TABLE generated_audio(id TEXT PRIMARY KEY,project_id TEXT,section_id TEXT,metadata_json TEXT,created_at TEXT);
        INSERT INTO projects VALUES('p');
        INSERT INTO scripts VALUES('s','p');
        INSERT INTO script_sections VALUES('sec','s');
        INSERT INTO speech_blocks VALUES('b','sec',0,NULL,'hello','en','', 'tts',0,180,NULL,1000,'take1','{}','a','a');
        """
    )
    return c


def load_migration():
    spec = importlib.util.spec_from_file_location("phase32_m27", ROOT / "storage/migrations/m027_manual_speech_editor.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_speech_block_hash_and_legacy_take_mirroring():
    m = load_speech_block_module()
    b = m.SpeechBlock("sec", 0, "សួស្តី", project_id="p", language="km", audio_id="take1", timeline_start_ms=0, timeline_end_ms=2000)
    assert b.active_generated_audio_id == "take1"
    assert b.text_hash == m.speech_text_hash("សួស្តី")
    assert b.allocated_duration_ms == 2000


def test_speech_block_multilingual_validation():
    m = load_speech_block_module()
    for language, value in [("en", "Hello"), ("km", "សួស្តី"), ("th", "สวัสดี"), ("vi", "Xin chào Việt Nam")]:
        m.SpeechBlock("sec", 0, value, language=language, timeline_start_ms=0, timeline_end_ms=1000).validate()


def test_speech_block_rejects_invalid_timing():
    m = load_speech_block_module()
    with pytest.raises(ValueError):
        m.SpeechBlock("sec", 0, "bad", timeline_start_ms=1000, timeline_end_ms=999).validate()


def test_migration_backfills_owner_take_and_start():
    c = migration_connection(); load_migration().migrate(c)
    row = c.execute("SELECT project_id,timeline_start_ms,active_generated_audio_id,audio_status FROM speech_blocks WHERE id='b'").fetchone()
    assert row == ("p", 1000, "take1", "ready")


def test_migration_is_idempotent():
    c = migration_connection(); m = load_migration(); m.migrate(c); m.migrate(c)
    assert c.execute("SELECT COUNT(*) FROM speech_blocks").fetchone()[0] == 1


@pytest.mark.parametrize(
    "needle",
    [
        "Select | Start | End | Speaker | Language | Text | Voice Profile | Duration Status | Audio Status | Actions",
        "reuseItems: true",
        "Ctrl+Enter",
        "Ctrl+F",
        'sequence: "Delete"',
        'sequence: "Space"',
        'text: "+ Add Speech"',
        'text: "Split"',
        'text: "Merge"',
        'placeholderText: "Find"',
        'text: "Set Speaker"',
        'text: "Set Voice"',
        'text: "Set Language"',
        'text: "Generate Selected"',
        'text: "Generate Outdated"',
        'text: "Generate All"',
        'text: "Select All"',
        'text: "Select Failed"',
        'text: "Select Ungenerated"',
        'text: "Cancel Remaining"',
    ],
)
def test_editor_contract(needle: str):
    qml = text("ui/qml/speech/SpeechEditor.qml")
    if needle.startswith("Select |"):
        assert all(part in qml for part in needle.split(" | "))
    else:
        assert needle in qml


@pytest.mark.parametrize(
    "path,needles",
    [
        ("services/speech_block_service.py", ["SpeechAudioStatus.OUTDATED", "speech_text_hash", "bulk_assign", "def split", "def merge", "def replace", "0.8<=rate<=1.25"]),
        ("services/multispeaker_tts_service.py", ["force:bool=False", "previous_id", "SpeechAudioStatus.CANCELLED", "generate_sequence", "outdated_only"]),
        ("services/manual_speech_editor_service.py", ["update_subtitle_from_speech", "confirm_edited", "transcript_to_speech", "translation_to_speech", "machineTranslated"]),
        ("services/timeline_mapping_service.py", ['"speech_block"', "timeline_start_ms", "timeline_end_ms", "waveformSource"]),
        ("storage/repositories/phase22_repository.py", ["active_generated_audio_id", "timeline_start_ms", "timeline_end_ms", 'clone.active_generated_audio_id=""']),
        ("ui/controllers/manual_speech_controller.py", ["ValueCommand", "mark_structural_saved", "voicePreviewRequested", "togglePreviewRequested", "_jobDone=Signal"]),
    ],
)
def test_service_contracts(path: str, needles: list[str]):
    source = text(path)
    for needle in needles:
        assert needle in source


@pytest.mark.parametrize(
    "path,needle",
    [
        ("ui/qml/news/NewsStudio.qml", "SpeechEditor"),
        ("ui/qml/story/StoryStudio.qml", "SpeechEditor"),
        ("ui/qml/dubbing/TranslateDubStudio.qml", "SpeechEditor"),
        ("ui/qml/shorts/ShortsStudio.qml", "SpeechEditor"),
        ("ui/qml/timeline/TimelineEditor.qml", "SpeechEditor"),
        ("ui/qml/timeline/TimelineTrack.qml", 'sourceType==="speech_block"'),
        ("app/manual_speech_runtime.py", 'SPVideoStudio.ManualSpeech'),
        ("main.py", "app.manual_speech_runtime"),
    ],
)
def test_cross_workflow_integration(path: str, needle: str):
    assert needle in text(path)


def test_no_parallel_tts_segment_model_or_phase32_runtime():
    names = [p.name for p in ROOT.rglob("*.py")]
    assert "phase32_runtime.py" not in names
    production = [p for p in ROOT.rglob("*.py") if "tests" not in p.parts]
    assert "TTSSegment" not in "\n".join(text(str(p.relative_to(ROOT))) for p in production)


def test_take_activation_persists_before_duration_refresh():
    source = text("services/speech_block_service.py")
    assert "self.repository.save_block(project_id,item);self.apply_generated_duration" in source


def test_source_audio_is_not_sent_to_tts():
    source = text("services/multispeaker_tts_service.py")
    assert "block.source_type_code!=SpeechSourceType.TTS.value" in source


def test_phase27_autosave_state_is_integrated():
    assert "AutosaveService" in text("app/manual_speech_runtime.py")
    assert "mark_structural_saved" in text("ui/controllers/manual_speech_controller.py")


def test_audio_mixer_compatibility_keeps_legacy_pointer():
    repo = text("storage/repositories/phase22_repository.py")
    assert "item.audio_id=item.active_generated_audio_id" in repo
    assert "active_generated_audio_id" in text("domain/speech_block.py")


def test_1000_row_ui_is_virtualized_not_repeater_rows():
    qml = text("ui/qml/speech/SpeechEditor.qml")
    assert "ListView" in qml and "reuseItems: true" in qml and "delegate: SpeechRow" in qml


def load_speech_service_module():
    speech = load_speech_block_module()
    sys.modules["domain.speech_block"] = speech
    repo_mod = types.ModuleType("storage.repositories.phase22_repository")
    class Phase22Repository: pass
    repo_mod.Phase22Repository = Phase22Repository
    sys.modules.setdefault("storage", types.ModuleType("storage"))
    sys.modules.setdefault("storage.repositories", types.ModuleType("storage.repositories"))
    sys.modules["storage.repositories.phase22_repository"] = repo_mod
    spec = importlib.util.spec_from_file_location("phase32_speech_service", ROOT / "services/speech_block_service.py")
    mod = importlib.util.module_from_spec(spec); sys.modules[spec.name] = mod
    assert spec and spec.loader; spec.loader.exec_module(mod)
    return speech, mod


class FakeLanguages:
    def get(self, code):
        if code not in {"en", "km", "th", "vi"}: raise KeyError(code)
        return code


class FakeRepository:
    def __init__(self): self.items=[]
    def blocks_for_section(self, section): return sorted([x for x in self.items if x.script_section_id==section], key=lambda x:x.order)
    def blocks_for_project(self, project): return sorted([x for x in self.items if x.project_id==project], key=lambda x:x.order)
    def save_block(self, project, item):
        item.project_id=project
        self.items=[x for x in self.items if x.id!=item.id]; self.items.append(item); return item
    def save_blocks(self, project, items):
        for x in items:self.save_block(project,x)
        return items
    def block(self, project, block_id): return next((x for x in self.items if x.project_id==project and x.id==block_id),None)
    def speaker(self, project, speaker_id): return object() if speaker_id else None
    def delete_block(self, project, block_id): self.items=[x for x in self.items if not(x.project_id==project and x.id==block_id)]
    def normalize_block_order(self, project, section):
        for i,x in enumerate(self.blocks_for_section(section)):x.order=i


class FakeSpeakers:
    def resolve_voice(self, project, block):
        return types.SimpleNamespace(voice_id=block.voice_override_id or "project-default"), "block" if block.voice_override_id else "project"


def make_service():
    speech, smod = load_speech_service_module(); repo=FakeRepository(); svc=smod.SpeechBlockService(repo,FakeSpeakers(),FakeLanguages())
    return speech,repo,svc


def test_functional_text_edit_marks_outdated_and_preserves_take():
    speech,repo,svc=make_service(); b=svc.add("p","sec","Hello",language="en",start_ms=0,end_ms=2000); b.active_generated_audio_id=b.audio_id="take-a"; b.audio_status=speech.SpeechAudioStatus.READY; repo.save_block("p",b)
    old_hash=b.text_hash; changed=svc.update("p",b.id,text="Hello again")
    assert changed.active_generated_audio_id=="take-a" and changed.audio_status_code=="outdated" and changed.text_hash!=old_hash


def test_functional_bulk_assignment_is_row_scoped():
    _,repo,svc=make_service(); a=svc.add("p","sec","A",language="en"); b=svc.add("p","sec","B",language="km")
    svc.bulk_assign("p",[a.id],voice_id="voice-A",language="th")
    assert repo.block("p",a.id).voice_override_id=="voice-A" and repo.block("p",a.id).language=="th"
    assert repo.block("p",b.id).voice_override_id=="" and repo.block("p",b.id).language=="km"


def test_functional_split_preserves_first_take_but_invalidates_it():
    speech,repo,svc=make_service(); b=svc.add("p","sec","one two",language="en",start_ms=0,end_ms=4000); b.active_generated_audio_id=b.audio_id="take-a";b.audio_status=speech.SpeechAudioStatus.READY;repo.save_block("p",b)
    first,second=svc.split("p",b.id,2000,"one","two")
    assert first.timeline_end_ms==2000 and first.active_generated_audio_id=="take-a" and first.audio_status_code=="outdated"
    assert second.timeline_start_ms==2000 and second.active_generated_audio_id=="" and second.audio_status_code=="not_generated"


def test_functional_merge_uses_language_appropriate_spacing():
    _,_,svc=make_service(); a=svc.add("p","sec","សួស្តី",language="km",start_ms=0,end_ms=1000); b=svc.add("p","sec","ពិភពលោក",language="km",start_ms=1000,end_ms=2000)
    merged=svc.merge("p",a.id,b.id)
    assert merged.text=="សួស្តីពិភពលោក" and merged.timeline_end_ms==2000


def test_functional_timing_rejects_negative_or_reversed_ranges():
    _,_,svc=make_service(); b=svc.add("p","sec","hello",language="en")
    with pytest.raises(ValueError):svc.set_timing("p",b.id,-1,100)
    with pytest.raises(ValueError):svc.set_timing("p",b.id,100,100)
