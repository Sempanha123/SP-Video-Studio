from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.constants import APP_VERSION
from app.update_config import UPDATE_CHANNEL, UPDATE_MANIFEST_SCHEMA_VERSION
from domain.schema_version import PROJECT_SCHEMA_VERSION
from domain.update_manifest import SemanticVersion


def https_url(value: str, name: str) -> str:
    parsed = urlparse(str(value or "").strip())
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError(f"{name} must be a public HTTPS URL")
    return parsed.geturl()


def sha256(path: Path) -> str:
    hasher=hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b''):hasher.update(chunk)
    return hasher.hexdigest()


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description='Generate a deterministic MMO Video Studio Stable update manifest.')
    parser.add_argument('--installer',required=True)
    parser.add_argument('--installer-url',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--minimum-supported-version',default=APP_VERSION)
    parser.add_argument('--release-notes',default='')
    parser.add_argument('--release-notes-url',default='')
    parser.add_argument('--signer-subject',default='')
    args=parser.parse_args(argv)
    installer=Path(args.installer).resolve(strict=True)
    if not installer.is_file() or installer.suffix.lower()!='.exe':raise SystemExit('Installer must be an existing .exe file')
    SemanticVersion.parse(APP_VERSION);SemanticVersion.parse(args.minimum_supported_version)
    payload={
        'schema_version':UPDATE_MANIFEST_SCHEMA_VERSION,
        'channel':UPDATE_CHANNEL,
        'version':APP_VERSION,
        'minimum_supported_version':args.minimum_supported_version,
        'published_at':datetime.now(timezone.utc).isoformat(),
        'release_notes':str(args.release_notes),
        'release_notes_url':https_url(args.release_notes_url,'release-notes-url') if args.release_notes_url else '',
        'installer_url':https_url(args.installer_url,'installer-url'),
        'installer_sha256':sha256(installer),
        'installer_size':installer.stat().st_size,
        'signature':{'type':'authenticode','signer':str(args.signer_subject).strip()} if args.signer_subject else {},
        'minimum_project_schema':PROJECT_SCHEMA_VERSION,
    }
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding='utf-8')
    print(output)
    return 0

if __name__=='__main__':raise SystemExit(main())
