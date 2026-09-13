from __future__ import annotations

import csv
import json
import shutil
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from tests.qa_support.fake_engines import FakeDirectorProvider, FakeSTTEngine, FakeTTSEngine, FakeTranslationEngine
from tests.qa_support.media_fixtures import MediaFixtureSet, generate_media_fixtures, run_ffmpeg, validate_mp4


@dataclass(slots=True)
class QAProject:
    project_id: str
    workflow: str
    language: str
    name: str
    root: Path
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def manifest(self) -> Path:
        return self.root / "project.json"


class ReleaseWorkflowHarness:
    """Deterministic release-QA harness with real tiny FFmpeg outputs.

    The harness intentionally lives under tests. It never discovers AppPaths and
    never reads LocalAppData. The complete repository's service-specific tests
    still cover product internals; this harness provides repeatable cross-workflow
    E2E sequencing without requiring large AI models.
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.projects_root = self.root / "Projects"
        self.assets_root = self.root / "Asset Library"
        self.outputs_root = self.root / "Outputs"
        self.fixtures_root = self.root / "fixtures"
        for path in (self.projects_root, self.assets_root, self.outputs_root, self.fixtures_root):
            path.mkdir(parents=True, exist_ok=True)
        self.fixtures: MediaFixtureSet = generate_media_fixtures(self.fixtures_root)
        self.tts = FakeTTSEngine()
        self.stt = FakeSTTEngine()
        self.translation = FakeTranslationEngine()
        self.director = FakeDirectorProvider()
        self._counter = 0
        self.db_path = self.root / "qa-state.db"
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS qa_events("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,project_id TEXT NOT NULL,kind TEXT NOT NULL,payload_json TEXT NOT NULL)"
            )
            connection.commit()

    def create_project(self, workflow: str, language: str = "en", name: str | None = None) -> QAProject:
        self._counter += 1
        project_id = f"qa-{workflow}-{language}-{self._counter:02d}"
        title = name or f"QA {workflow.title()} {language}"
        path = self.projects_root / project_id
        path.mkdir(parents=True, exist_ok=False)
        for child in ("media", "audio", "subtitles", "renders", "sources", "generated"):
            (path / child).mkdir()
        project = QAProject(project_id, workflow, language, title, path, {"schemaVersion": 2})
        self._save_manifest(project)
        self.record(project, "project_created", {"workflow": workflow, "language": language})
        return project

    def _save_manifest(self, project: QAProject) -> None:
        payload = {
            "id": project.project_id,
            "name": project.name,
            "workflow": project.workflow,
            "language": project.language,
            "schemaVersion": 2,
            "metadata": project.metadata,
        }
        project.manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def record(self, project: QAProject, kind: str, payload: dict[str, Any]) -> None:
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                "INSERT INTO qa_events(project_id,kind,payload_json) VALUES(?,?,?)",
                (project.project_id, kind, json.dumps(payload, ensure_ascii=False, sort_keys=True)),
            )
            connection.commit()

    def events(self, project: QAProject) -> list[tuple[str, dict[str, Any]]]:
        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(
                "SELECT kind,payload_json FROM qa_events WHERE project_id=? ORDER BY id", (project.project_id,)
            ).fetchall()
        return [(str(kind), json.loads(payload)) for kind, payload in rows]

    def copy_fixture(self, project: QAProject, source: Path, name: str | None = None) -> Path:
        target = project.root / "media" / (name or source.name)
        shutil.copy2(source, target)
        self.record(project, "media_import", {"name": target.name})
        return target

    def speech(self, project: QAProject, text: str, *, speaker: str, language: str | None = None) -> Path:
        output = project.root / "audio" / f"{speaker}.wav"
        request = SimpleNamespace(text=text, language=language or project.language, output_path=output)
        result = self.tts.generate(request)
        self.record(project, "speech_block", {"speaker": speaker, "text": text, "language": language or project.language})
        self.record(project, "tts_generated", {"speaker": speaker, "file": Path(result.output_path).name})
        return output

    def subtitle(self, project: QAProject, text: str, name: str = "captions.srt") -> Path:
        output = project.root / "subtitles" / name
        output.write_text(f"1\n00:00:00,000 --> 00:00:01,200\n{text}\n\n", encoding="utf-8")
        self.record(project, "subtitle", {"text": text, "file": name})
        return output

    def _render(
        self,
        project: QAProject,
        *,
        video_inputs: list[Path],
        voice: Path,
        music: Path | None = None,
        video_filter: str | None = None,
        filter_complex_video: str | None = None,
        output_name: str = "output.mp4",
    ) -> Path:
        output = project.root / "renders" / output_name
        if output.exists():
            raise FileExistsError(f"Release QA refuses output collision: {output.name}")
        args: list[str] = []
        for path in video_inputs:
            args += ["-i", str(path)]
        audio_start = len(video_inputs)
        args += ["-i", str(voice)]
        if music is not None:
            args += ["-i", str(music)]
        filters: list[str] = []
        if filter_complex_video:
            filters.append(filter_complex_video)
            video_map = "[v]"
        else:
            video_map = "0:v:0"
        if music is not None:
            filters.append(
                f"[{audio_start}:a]volume=1.0[voice];"
                f"[{audio_start + 1}:a]volume=0.12[music];"
                "[voice][music]amix=inputs=2:duration=longest:normalize=0[a]"
            )
            audio_map = "[a]"
        else:
            audio_map = f"{audio_start}:a:0"
        if filters:
            args += ["-filter_complex", ";".join(filters)]
        if video_filter and not filter_complex_video:
            args += ["-vf", video_filter]
        args += [
            "-map", video_map, "-map", audio_map, "-t", "1.2", "-shortest",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", "-y", str(output),
        ]
        run_ffmpeg(args, timeout=30)
        validate_mp4(output)
        self.record(project, "render", {"file": output.name})
        return output

    def normal_video(self, *, language: str = "en") -> tuple[QAProject, Path]:
        project = self.create_project("video", language, f"Normal {language}")
        video = self.copy_fixture(project, self.fixtures.video)
        image = self.copy_fixture(project, self.fixtures.image)
        music = self.copy_fixture(project, self.fixtures.music)
        self.record(project, "timeline_clip", {"source": video.name, "track": "video-1"})
        self.record(project, "timeline_clip", {"source": image.name, "track": "overlay-1"})
        overlay = "Hello · សួស្តី · สวัสดี · Xin chào"
        self.record(project, "overlay_text", {"text": overlay})
        voice = self.speech(project, "Release QA normal video", speaker="narrator", language=language)
        self.subtitle(project, overlay)
        self.record(project, "audio_mix", {"music": music.name, "ducking": True})
        output = self._render(project, video_inputs=[video], voice=voice, music=music)
        return project, output

    def reporter_news(self, *, portrait: bool = False) -> tuple[QAProject, Path]:
        project = self.create_project("news", "en", "Reporter News")
        presenter = self.copy_fixture(project, self.fixtures.green_screen, "presenter.mp4")
        broll = self.copy_fixture(project, self.fixtures.video, "broll.mp4")
        music = self.copy_fixture(project, self.fixtures.music)
        provenance = {
            "source": "fixture://local-news-source",
            "claim": "A deterministic QA event occurred.",
            "approved": True,
        }
        (project.root / "sources" / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
        self.record(project, "news_source", provenance)
        self.record(project, "reporter_speaker", {"speaker": "Reporter", "role": "reporter"})
        self.record(project, "lower_third", {"title": "QA Reporter", "subtitle": "Verified Fixture"})
        self.record(project, "green_screen_layer", {"source": presenter.name, "chromaKey": True})
        self.record(project, "broll", {"source": broll.name})
        voice = self.speech(project, "Reporter voice for approved grounded claim.", speaker="reporter")
        self.subtitle(project, "Reporter caption · ព័ត៌មាន · ข่าว · Tin tức")
        self.record(project, "audio_mix", {"music": music.name, "ducking": True})
        scale = "scale=90:160" if portrait else "scale=160:90"
        composite = (
            "[0:v]chromakey=0x00cc44:0.25:0.10,scale=64:64[fg];"
            "[1:v]scale=160:90[bg];[bg][fg]overlay=8:18:shortest=1,"
            f"{scale}[v]"
        )
        output = self._render(
            project, video_inputs=[presenter, broll], voice=voice, music=music,
            filter_complex_video=composite, output_name="reporter-news.mp4",
        )
        assert json.loads((project.root / "sources" / "provenance.json").read_text(encoding="utf-8"))["approved"] is True
        return project, output

    def interview_news(self) -> tuple[QAProject, Path]:
        project = self.create_project("news", "en", "Interview News")
        left = self.copy_fixture(project, self.fixtures.video, "reporter.mp4")
        right = self.copy_fixture(project, self.fixtures.green_screen, "guest.mp4")
        music = self.copy_fixture(project, self.fixtures.music)
        self.record(project, "speaker", {"name": "Reporter", "voice": "voice-a"})
        self.record(project, "speaker", {"name": "Guest", "voice": "voice-b"})
        self.record(project, "layout", {"kind": "split-screen", "pip": True})
        voice = self.speech(project, "Reporter asks. Guest answers.", speaker="interview")
        self.subtitle(project, "Reporter: Question\nGuest: Answer")
        self.record(project, "audio_mix", {"music": music.name, "voices": ["voice-a", "voice-b"]})
        composite = "[0:v]scale=80:90[left];[1:v]scale=80:90[right];[left][right]hstack=inputs=2[v]"
        output = self._render(
            project, video_inputs=[left, right], voice=voice, music=music,
            filter_complex_video=composite, output_name="interview.mp4",
        )
        return project, output

    def story(self) -> tuple[QAProject, Path]:
        project = self.create_project("story", "en", "Story QA")
        video = self.copy_fixture(project, self.fixtures.video)
        music = self.copy_fixture(project, self.fixtures.music)
        plan = self.director.generate_structured("story_plan", {"idea": "A tiny deterministic adventure"})
        self.record(project, "story_plan", plan)
        self.record(project, "story_beats", {"beats": ["setup", "turn", "ending"]})
        self.record(project, "script", {"narrator": "Narrator line", "character": "Character line"})
        self.record(project, "scene", {"count": 3})
        voice = self.speech(project, "Narrator and character tell a small story.", speaker="narrator")
        self.subtitle(project, "A deterministic story subtitle")
        self.record(project, "audio_mix", {"music": music.name, "ambience": "fixture"})
        output = self._render(project, video_inputs=[video], voice=voice, music=music, output_name="story.mp4")
        return project, output

    def translate_and_dub(self, *, source_language: str = "en", target_language: str = "km") -> tuple[QAProject, Path]:
        project = self.create_project("translate", target_language, "Dub QA")
        source = self.copy_fixture(project, self.fixtures.video, "source.mp4")
        music = self.copy_fixture(project, self.fixtures.music)
        stt_request = SimpleNamespace(source_path=self.fixtures.voice_wav, language=source_language, metadata={})
        transcription = self.stt.transcribe(stt_request)
        source_text = list(transcription.segments)[0].text
        self.record(project, "transcript", {"language": source_language, "text": source_text})
        request = SimpleNamespace(source_language=source_language, target_language=target_language, text=source_text)
        translated = self.translation.translate(request).text
        self.record(project, "translation", {"reviewed": True, "language": target_language, "text": translated})
        self.record(project, "speech_block", {"targetVoice": "dub-target", "timing": [0, 1200]})
        voice = self.speech(project, translated, speaker="dub-target", language=target_language)
        self.subtitle(project, translated, "target.srt")
        self.record(project, "audio_mix", {"source": "ducked", "dub": "foreground", "music": music.name})
        output = self._render(project, video_inputs=[source], voice=voice, music=music, output_name="dub.mp4")
        return project, output

    def shorts(self) -> tuple[QAProject, Path]:
        project = self.create_project("shorts", "en", "Shorts QA")
        source = self.copy_fixture(project, self.fixtures.long_video)
        broll = self.copy_fixture(project, self.fixtures.video, "short-broll.mp4")
        music = self.copy_fixture(project, self.fixtures.music)
        self.record(project, "manual_range", {"inMs": 500, "outMs": 2500})
        self.record(project, "short", {"aspect": "9:16", "hook": "QA hook"})
        self.record(project, "broll", {"source": broll.name})
        voice = self.speech(project, "Short hook and caption", speaker="short")
        self.subtitle(project, "Short caption")
        output = self._render(
            project, video_inputs=[source], voice=voice, music=music,
            video_filter="scale=90:160", output_name="short-9x16.mp4",
        )
        return project, output

    def template(self) -> tuple[QAProject, dict[str, Any]]:
        template = {
            "name": "Reporter News",
            "placeholders": {"presenter": "asset:presenter", "broll": "asset:broll"},
            "workflow": "news",
        }
        template_path = self.root / "reporter-template.json"
        template_path.write_text(json.dumps(template, indent=2), encoding="utf-8")
        presenter_asset = self.assets_root / "presenter.mp4"
        broll_asset = self.assets_root / "broll.mp4"
        shutil.copy2(self.fixtures.green_screen, presenter_asset)
        shutil.copy2(self.fixtures.video, broll_asset)
        project = self.create_project("news", "en", "Template Reporter")
        resolved = {
            "presenter": str(presenter_asset),
            "broll": str(broll_asset),
            "templateSnapshot": json.loads(template_path.read_text(encoding="utf-8")),
        }
        project.metadata["template"] = resolved
        self._save_manifest(project)
        template["name"] = "MUTATED AFTER APPLY"
        template_path.write_text(json.dumps(template), encoding="utf-8")
        reloaded = json.loads(project.manifest.read_text(encoding="utf-8"))["metadata"]["template"]
        self.record(project, "template_applied", {"independent": reloaded["templateSnapshot"]["name"] == "Reporter News"})
        return project, reloaded

    def asset_library(self) -> dict[str, Any]:
        asset = self.assets_root / "reusable-broll.mp4"
        shutil.copy2(self.fixtures.video, asset)
        a = self.create_project("video", "en", "Asset A")
        b = self.create_project("video", "en", "Asset B")
        refs = {a.project_id: str(asset), b.project_id: str(asset)}
        detached = a.root / "media" / asset.name
        shutil.copy2(asset, detached)
        refs[a.project_id] = str(detached)
        relinked = self.assets_root / "reusable-broll-relinked.mp4"
        asset.rename(relinked)
        refs[b.project_id] = str(relinked)
        delete_guard = any(Path(value).resolve() == relinked.resolve() for value in refs.values())
        return {"asset": relinked, "refs": refs, "detached": detached, "deleteGuard": delete_guard}

    def batch(self) -> dict[str, Any]:
        csv_path = self.root / "batch.csv"
        rows = [
            {"title": "Batch One", "language": "en", "platform": "youtube"},
            {"title": "Batch Khmer", "language": "km", "platform": "shorts"},
            {"title": "Batch Thai", "language": "th", "platform": "reels"},
        ]
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["title", "language", "platform"])
            writer.writeheader(); writer.writerows(rows)
        states: list[dict[str, Any]] = []
        outputs: list[Path] = []
        paused = False
        for index, row in enumerate(rows):
            project = self.create_project("batch", row["language"], row["title"])
            video = self.copy_fixture(project, self.fixtures.video)
            voice = self.speech(project, f"Batch row {index}", speaker=f"batch-{index}", language=row["language"])
            if index == 1:
                paused = True
                states.append({"row": index, "status": "paused"})
                states.append({"row": index, "status": "resumed"})
            if index == 2:
                states.append({"row": index, "status": "failed", "reason": "injected retry marker"})
                states.append({"row": index, "status": "retried"})
            output = self._render(project, video_inputs=[video], voice=voice, output_name=f"batch-{index}.mp4")
            outputs.append(output)
            states.append({"row": index, "status": "completed", "platform": row["platform"]})
        return {"csv": csv_path, "outputs": outputs, "states": states, "paused": paused}

    def recovery(self) -> tuple[QAProject, Path]:
        project = self.create_project("video", "en", "Recovery QA")
        video = self.copy_fixture(project, self.fixtures.video)
        voice = self.speech(project, "Before crash", speaker="recovery")
        snapshot = self.root / "recovery-snapshot"
        shutil.copytree(project.root, snapshot)
        self.record(project, "unclean_shutdown", {"simulated": True})
        project.manifest.write_text("{corrupted by simulated unclean close", encoding="utf-8")
        shutil.copy2(snapshot / "project.json", project.manifest)
        self.record(project, "recovered", {"snapshot": snapshot.name})
        output = self._render(project, video_inputs=[video], voice=voice, output_name="recovered.mp4")
        return project, output

    def close(self) -> None:
        self.tts.unload(); self.stt.unload(); self.translation.unload()
