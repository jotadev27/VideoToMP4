"""Integration tests use generated temporary media, never personal videos."""

import hashlib
import re
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from converter import (
    Cancelled, ConversionError, convert_media, enforce_size_range,
    ffmpeg_executable, probe_media, suggested_output,
)


class ConverterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix="video-to-mp4-tests-")
        cls.root = Path(cls.directory.name)
        cls.ffmpeg = ffmpeg_executable()

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def make_video(self, name, codec="mpeg4", audio=True, dimensions="320x240"):
        path = self.root / name
        args = [self.ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size={dimensions}:rate=24"]
        if audio:
            args += ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000"]
        args += ["-t", "3", "-c:v", codec]
        if codec == "libx264":
            args += ["-pix_fmt", "yuv420p"]
        if audio:
            args += ["-c:a", "aac" if codec == "libx264" else "pcm_s16le"]
        subprocess.run(args + [str(path)], check=True, capture_output=True)
        return path

    def convert(self, source):
        info = probe_media(source)
        digest = hashlib.sha256(source.read_bytes()).digest()
        output = suggested_output(source)
        progress = []
        convert_media(info, output, threading.Event(), lambda *values: progress.append(values))
        self.assertEqual(source.parent, output.parent)
        self.assertRegex(output.name, re.escape(source.stem) + r"_extracted\d{4}\.mp4$")
        self.assertGreaterEqual(output.stat().st_size, info.size)
        self.assertLessEqual(output.stat().st_size, info.size * 130 // 100)
        self.assertEqual(hashlib.sha256(source.read_bytes()).digest(), digest)
        result = probe_media(output)
        self.assertEqual(result.video_codec, "h264")
        self.assertEqual(result.pixel_format, "yuv420p")
        self.assertEqual(progress[-1][0], 100)
        subprocess.run([self.ffmpeg, "-v", "error", "-i", str(output), "-f", "null", "-"], check=True, capture_output=True)
        self.assertFalse(list(self.root.glob(".video-to-mp4-*")))
        return info, result, output

    def test_avi_bitrate_budget_and_original(self):
        info, result, _ = self.convert(self.make_video("sample with spaces.avi"))
        self.assertEqual((info.width, info.height), (result.width, result.height))
        self.assertIsNotNone(result.audio_index)

    def test_compatible_video_packets_are_identical(self):
        source = self.make_video("compatible.mkv", "libx264")
        info, _, output = self.convert(source)
        self.assertTrue(info.video_copy)
        def video_hash(path):
            return subprocess.run([self.ffmpeg, "-v", "error", "-i", str(path), "-map", "0:v:0", "-c", "copy", "-f", "hash", "-hash", "sha256", "-"], check=True, capture_output=True).stdout
        self.assertEqual(video_hash(source), video_hash(output))

    def test_silent_odd_dimensions(self):
        _, result, _ = self.convert(self.make_video("odd.mkv", "ffv1", False, "321x241"))
        self.assertEqual((result.width, result.height), (322, 242))
        self.assertIsNone(result.audio_index)

    def test_invalid_and_empty_input(self):
        invalid = self.root / "invalid.bin"
        invalid.write_text("This is not a video.")
        with self.assertRaises(ConversionError):
            probe_media(invalid)
        invalid.write_bytes(b"")
        with self.assertRaises(ConversionError):
            probe_media(invalid)

    def test_existing_output_and_source_are_protected(self):
        source = self.make_video("protected.mkv", "libx264", False)
        info = probe_media(source)
        with self.assertRaises(ConversionError):
            convert_media(info, source, threading.Event(), lambda *args: None)
        existing = self.root / "existing.mp4"
        existing.write_bytes(b"keep this")
        with self.assertRaises(ConversionError):
            convert_media(info, existing, threading.Event(), lambda *args: None)
        self.assertEqual(existing.read_bytes(), b"keep this")

    def test_cancellation_removes_partial_output(self):
        source = self.make_video("cancel.avi")
        event = threading.Event()
        output = suggested_output(source)
        with self.assertRaises(Cancelled):
            convert_media(probe_media(source), output, event, lambda *args: event.set())
        self.assertFalse(output.exists())
        self.assertFalse(list(self.root.glob(".video-to-mp4-*")))

    def test_random_name_retries_collision(self):
        source = self.root / "name.avi"
        (self.root / "name_extracted0007.mp4").touch()
        with patch("converter.secrets.randbelow", side_effect=[7, 12]):
            self.assertEqual(suggested_output(source).name, "name_extracted0012.mp4")

    def test_size_gate_rejects_oversized_file(self):
        oversized = self.root / "oversized.mp4"
        oversized.write_bytes(bytes(131))
        with self.assertRaises(ConversionError):
            enforce_size_range(oversized, 100, threading.Event())


if __name__ == "__main__":
    unittest.main()
