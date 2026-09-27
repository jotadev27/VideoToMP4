"""Local FFmpeg conversion with cancellation and atomic output publication."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


class ConversionError(Exception):
    """A failure that can be shown directly to the user."""


class Cancelled(Exception):
    pass


@dataclass(frozen=True)
class MediaInfo:
    path: Path
    duration: float | None
    width: int
    height: int
    video_index: int
    video_codec: str
    video_profile: str
    pixel_format: str
    audio_index: int | None
    audio_copy: bool
    hdr: bool
    size: int

    @property
    def video_copy(self) -> bool:
        return (
            self.video_codec == "h264"
            and self.video_profile in {"Baseline", "Constrained Baseline", "Main", "High", "Constrained High"}
            and self.pixel_format == "yuv420p"
            and not self.hdr
            and self.width % 2 == 0
            and self.height % 2 == 0
        )


def ffmpeg_executable() -> str:
    override = os.environ.get("VIDEO_TO_MP4_FFMPEG")
    if override:
        if not Path(override).is_file():
            raise ConversionError("The configured FFmpeg executable could not be found.")
        return override
    # The bundled build has H.264, AAC, and HDR tone-mapping support.
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError, RuntimeError):
        executable = shutil.which("ffmpeg")
        if executable:
            return executable
        raise ConversionError("FFmpeg is missing. Install the project requirements and try again.")


def process_options() -> dict:
    options = {"encoding": "utf-8", "errors": "replace"}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NO_WINDOW
    return options


def stop_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def probe_media(path: Path, cancel: threading.Event | None = None) -> MediaInfo:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise ConversionError("This file could not be found. Please select it again.")
    if path.stat().st_size == 0:
        raise ConversionError("This file is empty. Please select a valid video.")
    cancel = cancel or threading.Event()
    command = [
        ffmpeg_executable(), "-hide_banner", "-nostdin",
        "-protocol_whitelist", "file,pipe,crypto,data", "-i", str(path),
    ]
    # FFmpeg reports stream information without decoding or changing the file.
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **process_options()) as process:
        deadline = time.monotonic() + 60
        while True:
            if cancel.is_set():
                stop_process(process)
                raise Cancelled()
            try:
                _, diagnostic = process.communicate(timeout=0.15)
                break
            except subprocess.TimeoutExpired:
                if time.monotonic() > deadline:
                    stop_process(process)
                    raise ConversionError("Reading this video took too long. It may be damaged or unavailable.")

    videos = re.findall(r"^\s*Stream #0:(\d+)[^\n]*?: Video: ([^\n]+)", diagnostic, re.MULTILINE)
    videos = [(index, line) for index, line in videos if "attached pic" not in line]
    if not videos:
        raise ConversionError("No readable video was found. The file may be damaged, protected, or unsupported.")
    index, video = videos[0]
    dimensions = re.search(r"(?:^|[, ])(\d{1,6})x(\d{1,6})(?:[, \[]|$)", video)
    if not dimensions:
        raise ConversionError("The video dimensions could not be read. Please try another file.")
    duration_match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", diagnostic)
    duration = None
    if duration_match:
        hours, minutes, seconds = map(float, duration_match.groups())
        duration = hours * 3600 + minutes * 60 + seconds
    audio = re.search(r"^\s*Stream #0:(\d+)[^\n]*?: Audio: ([^\n]+)", diagnostic, re.MULTILINE)
    pixel = re.search(r"\b(yuv\w+|yuva\w+|rgb\w+|bgr\w+|gbr\w+|gray\w*|nv12|nv21)\b", video)
    return MediaInfo(
        path=path,
        duration=duration if duration and duration > 0 else None,
        width=int(dimensions[1]),
        height=int(dimensions[2]),
        video_index=int(index),
        video_codec=video.split()[0].rstrip(","),
        video_profile=(re.search(r"^\S+ \(([^)]+)\)", video)[1] if re.search(r"^\S+ \(([^)]+)\)", video) else "unknown"),
        pixel_format=pixel[0] if pixel else "unknown",
        audio_index=int(audio[1]) if audio else None,
        audio_copy=bool(audio and audio[2].startswith("aac ") and re.search(r"\b(mono|stereo)\b", audio[2])),
        hdr="smpte2084" in video or "arib-std-b67" in video,
        size=path.stat().st_size,
    )


def suggested_output(source: Path) -> Path:
    base = source.with_suffix(".mp4")
    if base == source or base.exists():
        base = source.with_name(source.stem + "_converted.mp4")
    number = 2
    candidate = base
    while candidate.exists():
        candidate = base.with_name(f"{base.stem}_{number}.mp4")
        number += 1
    return candidate


def conversion_command(info: MediaInfo, destination: Path) -> list[str]:
    command = [
        ffmpeg_executable(), "-hide_banner", "-nostdin", "-y", "-loglevel", "warning",
        "-protocol_whitelist", "file,pipe,crypto,data", "-i", str(info.path),
        "-map", f"0:{info.video_index}",
    ]
    if info.audio_index is not None:
        command += ["-map", f"0:{info.audio_index}"]
    if info.video_copy:
        command += ["-c:v", "copy"]
    else:
        filters = []
        if info.hdr:
            filters += [
                "zscale=t=linear:npl=100", "format=gbrpf32le", "zscale=p=bt709",
                "tonemap=tonemap=mobius:desat=0", "zscale=t=bt709:m=bt709:r=limited",
            ]
        # H.264 4:2:0 needs even dimensions. Pad at most one pixel; never shrink.
        filters.append("pad=ceil(iw/2)*2:ceil(ih/2)*2")
        command += [
            "-vf", ",".join(filters), "-c:v", "libx264", "-preset", "slow",
            "-crf", "16", "-pix_fmt", "yuv420p", "-profile:v", "high",
            "-fps_mode", "passthrough",
        ]
        if info.hdr:
            command += ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]
    if info.audio_index is not None:
        if info.audio_copy:
            command += ["-c:a", "copy"]
        else:
            command += ["-c:a", "aac", "-b:a", "256k", "-ac", "2", "-ar", "48000"]
    command += [
        "-map_metadata", "0", "-map_chapters", "0", "-sn", "-dn",
        "-tag:v", "avc1", "-movflags", "+faststart", "-progress", "pipe:1",
        "-nostats", "-f", "mp4", str(destination),
    ]
    return command


def friendly_error(diagnostic: str) -> str:
    lower = diagnostic.lower()
    if "no space left" in lower:
        return "There is not enough free space. Choose another location or free up disk space."
    if "permission denied" in lower or "read-only file system" in lower:
        return "This location is not writable. Please choose another output location."
    if "unknown encoder" in lower or "no such filter" in lower:
        return "This FFmpeg build is missing a required feature. Install the project requirements."
    if "invalid data" in lower or "error while decoding" in lower:
        return "The video could not be decoded. It may be damaged or use an unsupported codec."
    return "Conversion failed. The video may be damaged or unsupported. Try another file or output location."


def convert_media(
    info: MediaInfo,
    output: Path,
    cancel: threading.Event,
    progress: Callable[[float | None, str], None],
) -> Path:
    output = output.expanduser().absolute()
    if output.suffix.lower() != ".mp4":
        raise ConversionError("The output filename must end in .mp4.")
    if output.resolve() == info.path.resolve():
        raise ConversionError("Choose a different output filename to keep your original video safe.")
    if output.exists() or output.is_symlink():
        raise ConversionError("That output file already exists. Choose a new filename.")
    if not output.parent.is_dir():
        raise ConversionError("The output folder no longer exists. Please choose another location.")
    if cancel.is_set():
        raise Cancelled()
    try:
        descriptor, temporary_name = tempfile.mkstemp(prefix=".video-to-mp4-", suffix=".mp4", dir=output.parent)
        os.close(descriptor)
    except OSError as error:
        raise ConversionError("This location is not writable. Please choose another output location.") from error
    temporary = Path(temporary_name)
    process = None
    try:
        # Write diagnostics to a temporary file so neither pipe can block FFmpeg.
        with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as log:
            process = subprocess.Popen(
                conversion_command(info, temporary), stdout=subprocess.PIPE, stderr=log,
                bufsize=1, **process_options(),
            )
            finished = threading.Event()

            def watch_cancel() -> None:
                while not finished.wait(0.1):
                    if cancel.is_set():
                        stop_process(process)
                        return

            watcher = threading.Thread(target=watch_cancel, daemon=True)
            watcher.start()
            try:
                progress(0 if info.duration else None, "Converting…")
                for line in process.stdout:
                    key, _, value = line.strip().partition("=")
                    if key == "out_time_us":
                        try:
                            seconds = max(0, int(value) / 1_000_000)
                        except ValueError:
                            continue
                        percent = min(99, seconds / info.duration * 100) if info.duration else None
                        progress(percent, "Converting…")
                    elif key == "progress" and value == "end":
                        progress(99 if info.duration else None, "Finishing…")
                return_code = process.wait()
            finally:
                finished.set()
                watcher.join(timeout=4)
                process.stdout.close()
            if cancel.is_set():
                raise Cancelled()
            if return_code != 0 or temporary.stat().st_size == 0:
                log.seek(0)
                raise ConversionError(friendly_error(log.read()))
        progress(99, "Checking the result…")
        result = probe_media(temporary, cancel)
        if result.video_codec != "h264" or result.pixel_format != "yuv420p":
            raise ConversionError("The output could not be verified. Your original video is safe.")
        if cancel.is_set():
            raise Cancelled()
        # A hard link publishes the completed file atomically without ever replacing an existing file.
        try:
            os.link(temporary, output)
        except FileExistsError as error:
            raise ConversionError("That output file now exists. Choose a new filename.") from error
        except OSError:
            # Some FAT/exFAT/network volumes do not support hard links.
            # Exclusive creation still protects existing files; roll back partial copies.
            created = False
            try:
                with output.open("xb") as target:
                    created = True
                    with temporary.open("rb") as source:
                        while chunk := source.read(4 * 1024 * 1024):
                            if cancel.is_set():
                                raise Cancelled()
                            target.write(chunk)
                    target.flush()
                    os.fsync(target.fileno())
            except BaseException:
                if created:
                    output.unlink(missing_ok=True)
                raise
        progress(100, "Complete")
        return output
    finally:
        if process is not None:
            stop_process(process)
        temporary.unlink(missing_ok=True)
