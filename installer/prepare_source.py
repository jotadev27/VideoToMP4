"""Copy only reviewed public build inputs into a clean, anonymous build path."""

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    destination = args.destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("main.py", "converter.py", "workers.py", "app_info.py", "diagnostics.py", "typography.py", "LICENSE", "THIRD_PARTY_NOTICES.md", "requirements.txt"):
        shutil.copy2(ROOT / name, destination / name)
    for name in ("assets", "tests", "installer/linux", "installer/windows", "installer/licenses"):
        shutil.copytree(ROOT / name, destination / name, dirs_exist_ok=True)
    for name in ("build_bundle.py", "package_linux.py", "write_hashes.py"):
        shutil.copy2(ROOT / "installer" / name, destination / "installer" / name)


if __name__ == "__main__":
    main()
