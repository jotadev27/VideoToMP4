# Security

Only local files are processed. The application opens no listening ports,
uploads no videos, and does not provide remote control. FFmpeg runs with a
local-protocol allowlist, argument lists instead of a shell, and no stdin.
Original videos and existing output files are never replaced.

Download release files from this repository's Releases page and compare their
SHA-256 hashes with `SHA256SUMS.txt`. Hashes detect changes relative to the
published manifest; they are not a malware scan or a digital signature.

`.gitignore` excludes media, credentials, private folders, build caches, and
release binaries. It cannot block malware or prevent access to your computer.
Review staged files before publishing. Never commit credentials, even temporarily.

Report vulnerabilities privately through GitHub's security reporting feature
when it is enabled. Do not publish private files or sensitive details in issues.
