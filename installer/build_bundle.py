"""Freeze the app on its target OS; keep build paths outside the source tree."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app_info import VERSION  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    work = output.parent / "pyinstaller-work"
    command = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
        "--windowed", "--noupx", "--name", "VideoToMP4",
        "--distpath", str(output), "--workpath", str(work), "--specpath", str(work),
        "--add-data", f"{ROOT / 'assets'}{os.pathsep}assets",
        "--collect-all", "imageio_ffmpeg",
    ]
    if os.name == "nt":
        command += ["--icon", str(ROOT / "assets" / "logo.ico"), "--version-file", str(ROOT / "installer" / "windows" / "version_info.txt")]
    subprocess.run(command + [str(ROOT / "main.py")], check=True, cwd=ROOT)
    bundle = output / "VideoToMP4"
    for filename in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(ROOT / filename, bundle / filename)
    (bundle / "VERSION.txt").write_text(VERSION + "\n", encoding="utf-8")
    # Ship the licenses of the exact installed dependency distributions.
    import importlib.metadata
    licenses = bundle / "licenses"
    licenses.mkdir(exist_ok=True)
    shutil.copytree(ROOT / "installer/licenses", licenses, dirs_exist_ok=True)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.is_file():
        shutil.copy2(python_license, licenses / "Python-LICENSE.txt")
    elif Path("/usr/share/doc/python3.10/copyright").is_file():
        shutil.copy2("/usr/share/doc/python3.10/copyright", licenses / "Python-COPYRIGHT.txt")
    for name in ("PySide6", "PySide6_Essentials", "PySide6_Addons", "shiboken6", "imageio-ffmpeg", "pyinstaller"):
        distribution = importlib.metadata.distribution(name)
        for file in distribution.files or []:
            if any(word in file.name.lower() for word in ("license", "copying", "copyright")):
                source = Path(distribution.locate_file(file))
                if source.is_file():
                    shutil.copy2(source, licenses / f"{name}-{file.name}")


if __name__ == "__main__":
    main()
