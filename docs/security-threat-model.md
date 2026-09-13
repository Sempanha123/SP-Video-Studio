# MMO Video Studio Security Threat Model — Phase 37

## Scope and trust model

Phase 37 treats project/template/media/network/model input as untrusted data. Local user intent is trusted only to select an action; a filename, URL, ZIP member, JSON field, model manifest, subtitle, script, or provider value is never treated as executable code. Security failures fail closed where an operation would write/delete/execute outside an app-owned boundary, while preserving existing project data.

The release remains a local desktop application. Current online surfaces are explicit News URL fetching and managed model downloads. Phase 37 does not add cloud AI providers, telemetry, remote support, an updater, project-package import, or automatic crawling.

## Protected assets

- User projects and project metadata/database state.
- Imported media, generated media, renders, exports and external file references.
- Scripts, transcripts, translations, subtitles and News article/source content.
- Reference voice recordings and voice-related metadata, treated as sensitive user media.
- API/provider credentials if future online providers add them.
- Managed AI model files/manifests.
- User/built-in templates and `.mmovtemplate` packages.
- Recovery snapshots/autosave/session markers.
- Diagnostics/logs/support bundles.

## Trust boundaries

1. **Filesystem boundary** — app-owned project/cache/model/template/asset/recovery roots versus arbitrary external paths.
2. **Archive/import boundary** — `.mmovtemplate`, CSV and JSON/JSONL input versus validated domain data.
3. **Process boundary** — FFmpeg/FFprobe/system tools receive argv arrays; project text must never become shell syntax.
4. **Network boundary** — public News targets and trusted model-download endpoints versus local/private/metadata/internal targets.
5. **Privacy boundary** — local project content/reference voices versus explicitly configured online processing.
6. **Support boundary** — allow-listed environment/diagnostic summaries versus project/private content.
7. **Database boundary** — bound SQL parameters/migrations versus user-supplied values.
8. **Future updater boundary** — downloaded release artifacts must eventually require trusted HTTPS, integrity/authenticity validation, staging and explicit installation policy. Phase 37 does not implement an updater.

## Attack surfaces and threats

| Attack surface | Main threats | Phase 37 policy/control |
| --- | --- | --- |
| Template ZIP import | traversal, ZIP bomb, duplicate members, symlink/special file, script/executable payload, checksum tampering | pre-extraction path/type/count/size/ratio checks, streamed limits, semantic-payload checksums, controlled staging + atomic finalization |
| Managed filesystem writes/deletes | traversal, arbitrary deletion, symlink/junction escape, UNC/drive injection, reserved device names | canonical managed-root helpers, lexical + resolved containment, reparse/symlink rejection for destructive operations, Windows-name checks |
| Media/output filenames | malicious separators, absolute path, ADS, reserved names | output names are names rather than paths; path-like inputs are rejected, Unicode remains data |
| FFmpeg/FFprobe/subprocess | command injection, unbounded stderr, unsafe filter interpolation | argv lists, `shell=False`, explicit executable path, cancellation/bounded diagnostics, ASS/file-based text, FFmpeg filter-path escaping |
| News URLs | SSRF, unsafe schemes, private/loopback/link-local/metadata IPs, redirect pivot, simple DNS rebinding | HTTP/S only, DNS global-IP validation on each hop, redirect revalidation, best-effort connected-peer IP validation, byte/redirect/concurrency/time limits |
| Model downloads | redirect downgrade, untrusted host, traversal, oversized/tampered files, partial-install corruption | trusted HTTPS Hugging Face/hf.co family, redirect validation, bounded catalog, safe relative paths, expected size, SHA-256 when supplied, staging + verifier + atomic finalization |
| API/provider secrets | logs/project-file leakage, clipboard exposure | no current cloud credential feature; Phase 36 redaction extended for auth/cookie/token forms; future secrets must not enter project files and require a dedicated secure-storage design |
| Reference voices | accidental support/template packaging or silent upload | classified sensitive; support bundle allow-list excludes them; template package rejects reference/sensitive voice assets; no automatic upload path |
| Local database | SQL injection, corrupt migration/data loss | repository queries use bound parameters; migrations are app-defined; diagnostics use read/check/rolled-back probes; failures preserve data |
| Support bundles/logs | secret/private-content leakage | fixed allow-list, redaction, privacy gate, bounded recent logs, local creation only |
| External links/provider endpoints | unsafe scheme/automatic opening | no automatic opening of imported URLs; News has strict public-target policy; future custom providers need separate explicit configuration + privacy notice |
| Future updater | package substitution/execution | not implemented; future design must validate HTTPS + integrity/signature before staged install and must never execute content from templates/projects |

## Filesystem model

`ManagedRoot`, `canonicalize_path()`, `is_within_managed_root()`, `safe_copy_destination()` and `safe_delete()` define the shared Phase 37 managed-path contract. The helper rejects NULs, traversal, absolute/UNC/drive injection for relative destinations, alternate-data-stream style colons and Windows reserved device components. Destructive operations refuse the managed root itself and reject symlink/reparse/junction entries rather than following them.

Windows path comparisons use normalized case where running on Windows. UNC roots can still be valid *managed roots* when configured by the application, but untrusted relative child names cannot inject a new UNC/drive destination. Python/Win32 long-path behavior is preserved; the application does not truncate paths to legacy `MAX_PATH`, because truncation could alter containment.

Existing Phase 29 cache cleanup was reviewed and retained: it already classifies protected/user/external categories, checks lexical and resolved containment, refuses symlinks, avoids following links during walks and protects active/recovery/referenced generated data. Existing project deletion was also retained: it validates `project.json`/project ID, known project-root containment, stages by rename before the database delete and attempts restoration if the database step fails.

## Archive/import model

`.mmovtemplate` is treated as hostile until validated. Phase 37 checks member count, declared aggregate size, individual size, suspicious compression ratio, encryption, traversal/absolute/Windows paths, symlink/special-file metadata, duplicate members and executable/script/active-document extensions before extraction. Extraction streams each file with an independent byte cap into a controlled staging directory; it never uses `extractall()`.

Semantic payloads (`template.json`, assets and docs) require manifest checksum coverage and checksum verification before import. Older cosmetic preview images remain compatible without mandatory checksum coverage; previews are inert image data and are still subject to archive type/size/path checks. New exports include a preview checksum when present. Reference/sensitive voice assets are rejected from template packages.

Batch CSV/JSON/JSONL import already enforces extension dispatch, a 64 MiB file bound, 100,000-row bound, object structure and JSON nesting depth. Malformed Unicode/JSON fails as data; arbitrary Python object deserialization is not used.

## Process and FFmpeg model

The reviewed FFmpeg path builds argument arrays and uses `shell=False`. User-visible overlay/subtitle text is written to ASS and escaped, preserving English, Khmer, Thai, Vietnamese and general Unicode. Files embedded in a filter expression use FFmpeg-specific path escaping; shell quoting is deliberately not mixed into the filter helper.

Long renders are cancellable rather than given an arbitrary global wall-clock timeout. Short capability/discovery probes are time bounded, and stderr retained for user-facing errors is bounded. This is accepted because legitimate rendering duration is user-content dependent.

## Network model

News fetches allow only HTTP/S public targets. Localhost, `.local`, `.internal`, loopback/private/link-local/non-global IPv4/IPv6 and known metadata IPs are rejected. DNS is validated before every request/redirect. Phase 37 additionally compares the connected peer IP where urllib exposes it, reducing obvious DNS-rebinding risk. Redirect count, response bytes, request timeout and concurrent fetches are bounded. TLS certificate verification stays at the standard Python HTTPS default; no unverified context is installed.

Managed model downloads are a separate policy from News SSRF. Current model sources are trusted HTTPS endpoints in the Hugging Face/hf.co domain family; redirects are revalidated and HTTP downgrade/untrusted hosts are rejected. This does not authorize arbitrary custom provider URLs.

## Privacy model

Local editing/rendering and installed local model workflows remain local. Data can currently leave the device only through explicit online actions such as fetching a News URL or downloading model files; those actions do not upload project content. No cloud AI provider is configured in this release. Any future cloud LLM/translation/TTS/custom-online provider must show what project text/audio may be transmitted before first use and must use a provider-specific consent/configuration path.

Reference voices are sensitive media. They are excluded from support bundles, rejected from template package assets, and have no silent upload path. Diagnostics/support data stays local unless the user manually shares the generated file outside the application.

## Residual/accepted risks

- Python `urllib` exposes the connected socket through implementation details rather than a stable peer-IP API; peer validation is therefore best effort in addition to mandatory DNS/redirect validation.
- OS-backed credential storage is not implemented because the current release has no persisted cloud/provider credential feature. If provider secrets are added, they must not be placed in project/AppSettings files; a dedicated OS-backed or clearly documented local secret store is required first.
- Native/model libraries have their own parser/runtime attack surface. Templates cannot supply executable model code, and managed models are verified, but upstream library vulnerabilities remain a dependency-management risk.
- Windows junction behavior is defended through reparse-point checks where `st_file_attributes` is available; final release testing should repeat junction cases on real Windows/NTFS.
- The future updater remains unimplemented and therefore untested; its security boundary is documented here for the later release phase.
