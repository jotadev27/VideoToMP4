"""Create an Ubuntu .deb and Fedora .rpm from the same tested Linux bundle."""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app_info import VERSION  # noqa: E402


def stage_payload(root: Path, bundle: Path):
    # Packaging stages contain generated files only; reset them for repeatable rebuilds.
    if root.exists():
        shutil.rmtree(root)
    shutil.copytree(bundle, root / "opt" / "videotomp4", dirs_exist_ok=True)
    applications = root / "usr/share/applications"
    applications.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "installer/linux/videotomp4.desktop", applications)
    icons = root / "usr/share/icons/hicolor/scalable/apps"
    icons.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "assets/logo.svg", icons / "videotomp4.svg")
    binaries = root / "usr/bin"
    binaries.mkdir(parents=True, exist_ok=True)
    (binaries / "videotomp4").symlink_to("../../opt/videotomp4/VideoToMP4")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=("deb", "rpm"), required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    work, output = args.work.resolve(), args.output.resolve()
    work.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    if args.format == "deb":
        root = work / "deb-root"
        stage_payload(root, args.bundle)
        control = root / "DEBIAN"
        control.mkdir(exist_ok=True)
        size = sum(p.stat().st_size for p in root.rglob("*") if p.is_file() and not p.is_symlink()) // 1024
        (control / "control").write_text(
            f"Package: videotomp4\nVersion: {VERSION}\nArchitecture: amd64\n"
            "Maintainer: jotadev27 <jotadev27@users.noreply.github.com>\n"
            f"Installed-Size: {size}\nSection: video\nPriority: optional\n"
            "Depends: libc6 (>= 2.35), libgl1, libegl1, libopengl0, libglib2.0-0, "
            "libfontconfig1, libdbus-1-3, libxkbcommon0, libxkbcommon-x11-0, "
            "libxcb-cursor0, libxcb-icccm4, libxcb-keysyms1, libxcb-render-util0, libxcb-xinerama0, libxcb-xkb1\n"
            "Homepage: https://github.com/jotadev27/VideoToMP4\n"
            "Description: Convert local videos to MP4 with a minimal desktop interface\n"
            " Preserves originals, controls output size, and runs without uploads.\n",
            encoding="utf-8",
        )
        subprocess.run(["dpkg-deb", "--root-owner-group", "--build", str(root), str(output / f"VideoToMP4-v{VERSION}-linux-ubuntu-amd64.deb")], check=True)
    else:
        payload = work / "payload"
        stage_payload(payload, args.bundle)
        for directory in ("BUILD", "BUILDROOT", "RPMS", "SOURCES", "SPECS", "SRPMS"):
            (work / directory).mkdir(exist_ok=True)
        spec = work / "SPECS/videotomp4.spec"
        spec.write_text(
            f"Name: videotomp4\nVersion: {VERSION}\nRelease: 1\n"
            "Summary: Convert local videos to MP4\nLicense: MIT AND GPL-3.0-only AND LGPL-3.0-only\n"
            "URL: https://github.com/jotadev27/VideoToMP4\nBuildArch: x86_64\nAutoReqProv: no\n"
            "Requires: glibc >= 2.35, libglvnd-glx, libglvnd-egl, libglvnd-opengl, glib2, fontconfig, dbus-libs, "
            "libxkbcommon, libxkbcommon-x11, xcb-util-cursor, xcb-util-wm, xcb-util-keysyms, xcb-util-renderutil, libxcb\n"
            "%global debug_package %{nil}\n%global __strip /bin/true\n"
            "%global __os_install_post %{nil}\n"
            "%description\nA minimal local desktop video converter with bounded output sizes.\n"
            f"%install\nmkdir -p %{{buildroot}}\ncp -a {payload}/. %{{buildroot}}/\n"
            "%files\n/opt/videotomp4\n/usr/bin/videotomp4\n/usr/share/applications/videotomp4.desktop\n"
            "/usr/share/icons/hicolor/scalable/apps/videotomp4.svg\n",
            encoding="utf-8",
        )
        temporary = work / "tmp"
        temporary.mkdir(exist_ok=True)
        subprocess.run(["rpmbuild", "--define", f"_topdir {work}", "--define", f"_tmppath {temporary}", "--define", "_buildhost release-builder", "-bb", str(spec)], check=True)
        built = next((work / "RPMS/x86_64").glob("*.rpm"))
        shutil.copy2(built, output / f"VideoToMP4-v{VERSION}-linux-fedora-x86_64.rpm")


if __name__ == "__main__":
    main()
