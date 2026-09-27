# Third-party components

The application source is MIT licensed by jotadev27. Bundled dependencies
retain their own licenses; the application license does not replace them.

| Component | License | Source |
| --- | --- | --- |
| Python | Python Software Foundation | https://www.python.org/downloads/source/ |
| PySide6 / Shiboken6 | LGPL-3.0 / GPL-3.0 | https://code.qt.io/cgit/pyside/pyside-setup.git/ |
| Qt 6.8.3 | LGPL-3.0 / GPL-3.0; see individual modules | https://download.qt.io/archive/qt/6.8/6.8.3/single/ |
| imageio-ffmpeg 0.6.0 | BSD-2-Clause (Python wrapper) | https://github.com/imageio/imageio-ffmpeg/tree/v0.6.0 |
| FFmpeg and linked codecs | GPL-3.0 for the bundled static builds | https://github.com/imageio/imageio-ffmpeg/blob/v0.6.0/tasks.py |
| PyInstaller | GPL-2.0 with bootloader exception | https://github.com/pyinstaller/pyinstaller |
| Noto Sans | SIL Open Font License 1.1 | https://github.com/notofonts/noto-fonts |

The Linux FFmpeg binary in imageio-ffmpeg 0.6.0 is the unmodified 7.0.2
static build from https://johnvansickle.com/ffmpeg/; upstream FFmpeg source:
https://ffmpeg.org/releases/ffmpeg-7.0.2.tar.xz.
The Windows binary is the unmodified 7.1 build shipped by the same wheel;
upstream FFmpeg source: https://ffmpeg.org/releases/ffmpeg-7.1.tar.xz.
The wheel download/build provenance is recorded in its `tasks.py` file;
vendor build information is available at https://johnvansickle.com/ffmpeg/
and https://www.gyan.dev/ffmpeg/builds/.
Use `ffmpeg -version` and `ffmpeg -buildconf` to identify the exact build.

Qt libraries are dynamically linked and remain replaceable in the `_internal`
directory. Distribution bundles include dependency license files. No dependency
code or binaries have been modified. Users may replace compatible Qt libraries
and reverse engineer them for debugging their modifications under the LGPL.
