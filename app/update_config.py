from __future__ import annotations

"""Build-level updater trust configuration.

The official manifest URL and expected Authenticode signer must be supplied by the
release owner. Projects/templates never participate in updater trust decisions.
"""

UPDATE_CHANNEL = "stable"
UPDATE_MANIFEST_SCHEMA_VERSION = 1
# Deliberately blank until the release owner publishes an official HTTPS manifest.
UPDATE_MANIFEST_URL = ""
# Example once code signing is deployed: "CN=Example Publisher, O=Example Publisher"
EXPECTED_UPDATE_SIGNER_SUBJECT = ""
UPDATE_STALE_AFTER_DAYS = 14
UPDATE_HTTP_TIMEOUT_SECONDS = 12.0
UPDATE_MAX_MANIFEST_BYTES = 256 * 1024
