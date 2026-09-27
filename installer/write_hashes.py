"""Write portable SHA-256 checksums without machine-specific paths."""

import argparse
import hashlib
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    lines = []
    for path in sorted(args.directory.iterdir()):
        if path.is_file() and path.suffix.lower() in {".deb", ".rpm", ".exe", ".zip"}:
            with path.open("rb") as source:
                checksum = hashlib.sha256()
                while chunk := source.read(1024 * 1024):
                    checksum.update(chunk)
                digest = checksum.hexdigest()
            lines.append(f"{digest}  {path.name}\n")
    manifest = "".join(lines)
    (args.directory / "SHA256SUMS.txt").write_text(manifest, encoding="utf-8")
    if args.manifest:
        args.manifest.write_text(manifest, encoding="utf-8")


if __name__ == "__main__":
    main()
