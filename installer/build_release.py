"""Build all v1.0 packages locally; never push or upload release files."""

import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "installer/.build"
ARTIFACTS = ROOT / "installer/artifacts"


def run(arguments):
    subprocess.run([str(argument) for argument in arguments], cwd=ROOT, check=True)


def main():
    for tool in ("podman", "rpmbuild"):
        if not shutil.which(tool):
            raise SystemExit(f"Required build tool not found: {tool}")
    BUILD.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    podman = ["podman", "--root", BUILD / "containers", "--runroot", BUILD / "runroot"]
    run([sys.executable, "installer/make_artwork.py"])
    with tempfile.TemporaryDirectory(prefix="videotomp4-public-source-") as directory:
        source = Path(directory) / "source"
        run([sys.executable, "installer/prepare_source.py", source])
        for target in ("linux", "windows"):
            run(podman + ["build", "-t", f"localhost/videotomp4-{target}:v1.0", "-f", f"installer/{target}/Dockerfile", "."])
            output = BUILD / target
            output.mkdir(exist_ok=True)
            mounts = ["-v", f"{source}:/source:ro,z", "-v", f"{output}:/output:rw,z"]
            if target == "linux":
                run(podman + ["run", "--rm", "--network=none", *mounts,
                    "-v", f"{ARTIFACTS}:/artifacts:rw,z", "localhost/videotomp4-linux:v1.0", "sh", "-c",
                    "python3 -m unittest discover -s tests -v && "
                    "python3 installer/build_bundle.py --output /output/dist && "
                    "/output/dist/VideoToMP4/VideoToMP4 --self-test /output/smoke.json && "
                    "python3 installer/package_linux.py --format deb --bundle /output/dist/VideoToMP4 "
                    "--work /output/package --output /artifacts"])
            else:
                run(podman + ["run", "--rm", "--network=none", *mounts,
                    "localhost/videotomp4-windows:v1.0", "sh", "-c",
                    "wine python Z:/source/installer/build_bundle.py --output Z:/output/dist && "
                    "QT_QPA_PLATFORM=offscreen wine Z:/output/dist/VideoToMP4/VideoToMP4.exe "
                    "--self-test Z:/output/smoke.json"])
        # Compile the setup wizard with Linux NSIS using the real Windows bundle.
        run(podman + ["run", "--rm", "--network=none", "-v", f"{source}:/source:ro,z",
            "-v", f"{BUILD / 'windows/dist'}:/windows:ro,z", "-v", f"{ARTIFACTS}:/artifacts:rw,z",
            "localhost/videotomp4-linux:v1.0", "makensis", "-V2",
            "-DBUNDLE=/windows/VideoToMP4", "-DOUTPUT=/artifacts/VideoToMP4-v1.0-windows-setup.exe",
            "/source/installer/windows/setup.nsi"])
        run([sys.executable, "installer/package_linux.py", "--format", "rpm", "--bundle",
             BUILD / "linux/dist/VideoToMP4", "--work", BUILD / "rpm", "--output", ARTIFACTS])
        bundle = BUILD / "windows/dist/VideoToMP4"
        with zipfile.ZipFile(ARTIFACTS / "VideoToMP4-v1.0-windows-portable.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path in sorted(bundle.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(bundle.parent))
        run([sys.executable, "installer/write_hashes.py", ARTIFACTS, "--manifest", "installer/SHA256SUMS.txt"])
    print("Release files are ready in installer/artifacts. Nothing was pushed or uploaded.")


if __name__ == "__main__":
    main()
