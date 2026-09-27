"""Offline smoke checks for frozen release binaries using synthetic media."""

import hashlib
import json
import subprocess
import tempfile
import threading
from pathlib import Path

from converter import convert_media, ffmpeg_executable, probe_media, process_options, suggested_output


def check_conversion() -> dict:
    """Exercise the bundled FFmpeg and Python modules, without private inputs."""
    with tempfile.TemporaryDirectory(prefix="videotomp4-smoke-") as directory:
        source = Path(directory) / "sample.avi"
        subprocess.run([
            ffmpeg_executable(), "-v", "error", "-y", "-f", "lavfi", "-i",
            "testsrc=size=640x360:rate=24", "-t", "3", "-c:v", "mpeg4", "-q:v", "2", str(source),
        ], check=True, capture_output=True, **process_options())
        original = hashlib.sha256(source.read_bytes()).digest()
        info = probe_media(source)
        output = convert_media(info, suggested_output(source), threading.Event(), lambda *args: None)
        result = probe_media(output)
        subprocess.run([ffmpeg_executable(), "-v", "error", "-i", str(output), "-f", "null", "-"], check=True, capture_output=True, **process_options())
        assert (result.width, result.height) == (640, 360)
        assert result.video_codec == "h264" and result.pixel_format == "yuv420p"
        assert info.size <= output.stat().st_size <= info.size * 130 // 100
        assert hashlib.sha256(source.read_bytes()).digest() == original
        return {"conversion": "passed", "size_range": "passed", "source_preserved": "passed"}


def write_report(path: Path, result: dict) -> None:
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
