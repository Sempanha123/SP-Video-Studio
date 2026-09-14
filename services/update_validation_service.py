from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess

from domain.update_manifest import UpdateManifest


class UpdateValidationError(RuntimeError):
    pass


class UpdateValidationService:
    def __init__(self, staging_root: Path, *, expected_signer_subject: str = "") -> None:
        self.root = Path(staging_root).resolve(strict=False)
        self.expected_signer_subject = str(expected_signer_subject or "").strip()

    def validate(self, path: Path, manifest: UpdateManifest) -> dict[str, object]:
        candidate = Path(path).resolve(strict=True)
        if candidate.parent != self.root or candidate.suffix.lower() != ".exe":
            raise UpdateValidationError("Installer is outside the managed update staging directory")
        size = candidate.stat().st_size
        if size != manifest.installer_size:
            raise UpdateValidationError("Installer size does not match the update manifest")
        digest = self.sha256(candidate)
        if digest.lower() != manifest.installer_sha256.lower():
            raise UpdateValidationError("Installer checksum does not match the update manifest")
        signature = self.verify_authenticode(candidate)
        return {"sha256": digest, "size": size, **signature}

    @staticmethod
    def sha256(path: Path) -> str:
        hasher = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def verify_authenticode(self, path: Path) -> dict[str, object]:
        if not self.expected_signer_subject:
            return {"signatureConfigured": False, "signatureValid": None, "signer": ""}
        if os.name != "nt":
            raise UpdateValidationError("Authenticode verification requires Windows")
        script = (
            "$s=Get-AuthenticodeSignature -LiteralPath $args[0];"
            "$o=[ordered]@{Status=[string]$s.Status;Subject=if($s.SignerCertificate){[string]$s.SignerCertificate.Subject}else{''}};"
            "$o|ConvertTo-Json -Compress"
        )
        try:
            completed = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script, str(path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
                shell=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise UpdateValidationError("Could not verify installer digital signature") from exc
        if completed.returncode != 0:
            raise UpdateValidationError("Could not verify installer digital signature")
        try:
            payload = json.loads(completed.stdout.strip())
        except json.JSONDecodeError as exc:
            raise UpdateValidationError("Digital signature verifier returned invalid data") from exc
        status = str(payload.get("Status") or "")
        signer = str(payload.get("Subject") or "")
        if status.lower() != "valid" or self.expected_signer_subject.casefold() not in signer.casefold():
            raise UpdateValidationError("Installer digital signature is not from the expected publisher")
        return {"signatureConfigured": True, "signatureValid": True, "signer": signer}
