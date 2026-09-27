"""Reject common private files, media, and embedded credentials in Git inputs."""

import re
import subprocess
import sys
from pathlib import Path

BLOCKED_SUFFIXES = {
    ".mp4", ".mkv", ".mov", ".avi", ".webm", ".wmv", ".mpeg", ".mpg",
    ".mts", ".m2ts", ".ts", ".3gp", ".vob", ".hevc", ".h264",
    ".mxf", ".nut", ".y4m", ".rm", ".rmvb", ".f4v", ".dv", ".swf",
    ".exe", ".dll", ".msi", ".scr", ".com", ".deb", ".rpm", ".zip",
    ".pem", ".key", ".p12", ".pfx", ".kdbx",
}
BLOCKED_DIRECTORIES = {".venv", ".codex", ".agents", ".ssh", "private", "personal", "artifacts", ".build"}
SECRET_PATTERNS = [
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(rb"\bgithub_pat_[A-Za-z0-9_]{40,}\b"),
    re.compile(rb"\bAKIA[A-Z0-9]{16}\b"),
]


def main():
    paths = subprocess.check_output(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"]).split(b"\0")
    errors = []
    for encoded in paths:
        if not encoded:
            continue
        relative = Path(encoded.decode("utf-8"))
        if relative.suffix.lower() in BLOCKED_SUFFIXES or set(relative.parts) & BLOCKED_DIRECTORIES or relative.name.startswith(".env"):
            errors.append(f"Excluded file type: {relative}")
            continue
        path = Path.cwd() / relative
        if path.is_symlink():
            errors.append(f"Symlink requires manual review: {relative}")
        elif path.is_file():
            if path.stat().st_size > 5 * 1024 * 1024:
                errors.append(f"Unexpected large file: {relative}")
                continue
            content = path.read_bytes()
            if any(pattern.search(content) for pattern in SECRET_PATTERNS):
                errors.append(f"Possible embedded credential: {relative}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Public tree check passed: no excluded files or recognized embedded credentials.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
