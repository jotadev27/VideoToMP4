# v1.0 release files

Generated files are in `artifacts/` (ignored by Git):

| File | Purpose |
| --- | --- |
| `VideoToMP4-v1.0-linux-ubuntu-amd64.deb` | Ubuntu 22.04+ installer |
| `VideoToMP4-v1.0-linux-fedora-x86_64.rpm` | Fedora 40+ installer |
| `VideoToMP4-v1.0-windows-setup.exe` | Windows 10/11 English setup wizard |
| `VideoToMP4-v1.0-windows-portable.zip` | Windows portable bundle |
| `SHA256SUMS.txt` | SHA-256 manifest |

The checked-in `SHA256SUMS.txt` mirrors the generated artifact manifest.
`release-v1.0.txt` is ready to paste into a GitHub release named **v1.0**.
The release tag is **v1.0**, not a three-component version.

## Rebuild

Linux builders need Python, Podman, and `rpmbuild`. Windows setup compilation
uses NSIS. The build script uses an Ubuntu 22.04 container for Linux and a Wine
container with Windows Python 3.12 for Windows. Dependencies are installed only
inside build containers. Source copying uses an explicit allowlist so personal
files, Git data, and videos are not build inputs.

All release packages are built locally. This project does not use GitHub Actions.

```bash
.venv/bin/python -m pip install -r installer/requirements-build.txt
.venv/bin/python installer/build_release.py
.venv/bin/python installer/write_hashes.py installer/artifacts --manifest installer/SHA256SUMS.txt
cd installer/artifacts
sha256sum -c SHA256SUMS.txt
```

The app can also be frozen natively on Windows with Python 3.12:

```powershell
py -m pip install PySide6==6.8.3 imageio-ffmpeg==0.6.0 pyinstaller==6.22.0
py installer/build_bundle.py --output installer/.build/windows/dist
```

Run NSIS with `BUNDLE` pointing to the generated `VideoToMP4` directory.
Native rebuilds must use the supplied icon, artwork, version file, license files,
and full `_internal` runtime directory. PyInstaller requires a target-platform
Python runtime; a Linux executable cannot be renamed to produce a Windows app.

## Publish manually

Push the reviewed commits and `v1.0` tag, create a GitHub release, paste
`release-v1.0.txt`, and attach the four packages plus `SHA256SUMS.txt`.
Keep large release binaries out of repository history. No release is uploaded
automatically by this project.

## Validation

The generated app was installed and smoke-tested in clean Ubuntu 22.04 and
Fedora 44 containers. Windows portable conversion, silent installation,
installed-app conversion, and uninstall preserving user files were tested under
Wine. UI screenshots were checked visually, including the bundled font.
Native Windows and actual smartphones remain separate playback checks.
