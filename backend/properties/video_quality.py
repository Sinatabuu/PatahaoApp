"""Deterministic validation and thumbnail extraction for property videos."""

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.core.exceptions import ValidationError


MAX_VIDEO_BYTES = 100 * 1024 * 1024
MIN_VIDEO_SECONDS = 5
MAX_VIDEO_SECONDS = 120
MIN_LONG_EDGE = 854
MIN_SHORT_EDGE = 480
MAX_LONG_EDGE = 1920
MAX_SHORT_EDGE = 1080


@dataclass(frozen=True)
class PropertyVideoAnalysis:
    file_size: int
    content_sha256: str
    width: int
    height: int
    duration: int
    video_codec: str
    audio_codec: str
    thumbnail_bytes: bytes


def _seek(uploaded_file, position=0):
    try:
        uploaded_file.seek(position)
    except (AttributeError, OSError):
        return


def _validate_upload_envelope(uploaded_file):
    name = str(getattr(uploaded_file, "name", ""))
    suffix = Path(name).suffix.lower()

    if suffix != ".mp4":
        raise ValidationError(
            "Upload an MP4 walkthrough video encoded with H.264."
        )

    file_size = int(getattr(uploaded_file, "size", 0) or 0)

    if file_size <= 0:
        raise ValidationError("The selected video is empty.")

    if file_size > MAX_VIDEO_BYTES:
        raise ValidationError(
            "Property videos must be 100 MB or smaller."
        )

    _seek(uploaded_file)
    header = uploaded_file.read(64)
    _seek(uploaded_file)

    if b"ftyp" not in header:
        raise ValidationError(
            "The selected file is not a valid MP4 video."
        )

    return file_size


def _copy_upload_to_temporary_file(uploaded_file):
    digest = sha256()
    temporary_file = NamedTemporaryFile(
        suffix=".mp4",
        delete=False,
    )
    temporary_path = Path(temporary_file.name)
    copied = False

    try:
        _seek(uploaded_file)

        chunks = getattr(uploaded_file, "chunks", None)
        source_chunks = (
            chunks()
            if callable(chunks)
            else iter(lambda: uploaded_file.read(1024 * 1024), b"")
        )

        for chunk in source_chunks:
            digest.update(chunk)
            temporary_file.write(chunk)

        temporary_file.flush()
        copied = True
    finally:
        temporary_file.close()
        _seek(uploaded_file)

        if not copied:
            temporary_path.unlink(missing_ok=True)

    return temporary_path, digest.hexdigest()


def _run(command, *, purpose):
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=settings.VIDEO_PROCESSING_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as exc:
        raise ValidationError(
            "Video processing is not configured on this server."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise ValidationError(
            f"Video {purpose} took too long. Try a smaller file."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise ValidationError(
            f"The video could not pass {purpose}."
        ) from exc


def _probe_video(path):
    result = _run(
        [
            settings.VIDEO_FFPROBE_BINARY,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        purpose="inspection",
    )

    try:
        payload = json.loads(result.stdout)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            "The video inspection result was invalid."
        ) from exc

    streams = payload.get("streams", [])

    if not isinstance(streams, list):
        raise ValidationError("The uploaded MP4 contains no video stream.")

    video_stream = next(
        (
            stream
            for stream in streams
            if stream.get("codec_type") == "video"
        ),
        None,
    )

    if video_stream is None:
        raise ValidationError("The uploaded MP4 contains no video stream.")

    audio_stream = next(
        (
            stream
            for stream in streams
            if stream.get("codec_type") == "audio"
        ),
        None,
    )

    try:
        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))
        raw_duration = (
            video_stream.get("duration")
            or payload.get("format", {}).get("duration")
        )
        duration_value = float(raw_duration)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            "The video duration or resolution could not be verified."
        ) from exc

    video_codec = str(video_stream.get("codec_name", "")).lower()
    audio_codec = (
        str(audio_stream.get("codec_name", "")).lower()
        if audio_stream is not None
        else ""
    )

    return {
        "width": width,
        "height": height,
        "duration_value": duration_value,
        "video_codec": video_codec,
        "audio_codec": audio_codec,
    }


def _validate_probe(probe):
    if probe["video_codec"] != "h264":
        raise ValidationError(
            "Property videos must use the H.264 video codec."
        )

    if probe["audio_codec"] and probe["audio_codec"] != "aac":
        raise ValidationError(
            "Property video audio must use AAC encoding."
        )

    duration_value = probe["duration_value"]

    if duration_value < MIN_VIDEO_SECONDS:
        raise ValidationError(
            "Property videos must be at least 5 seconds long."
        )

    if duration_value > MAX_VIDEO_SECONDS:
        raise ValidationError(
            "Property videos must be no longer than 2 minutes."
        )

    long_edge = max(probe["width"], probe["height"])
    short_edge = min(probe["width"], probe["height"])

    if long_edge < MIN_LONG_EDGE or short_edge < MIN_SHORT_EDGE:
        raise ValidationError(
            "Property videos must be at least 854 x 480 resolution."
        )

    if long_edge > MAX_LONG_EDGE or short_edge > MAX_SHORT_EDGE:
        raise ValidationError(
            "Property videos must be 1080p or lower for this MVP."
        )


def _generate_thumbnail(path, duration_value):
    thumbnail_file = NamedTemporaryFile(
        suffix=".jpg",
        delete=False,
    )
    thumbnail_path = Path(thumbnail_file.name)
    thumbnail_file.close()

    try:
        capture_second = min(
            2.0,
            max(0.0, duration_value / 3),
        )
        _run(
            [
                settings.VIDEO_FFMPEG_BINARY,
                "-y",
                "-ss",
                f"{capture_second:.2f}",
                "-i",
                str(path),
                "-frames:v",
                "1",
                "-vf",
                (
                    "scale=1280:-2:"
                    "force_original_aspect_ratio=decrease"
                ),
                "-q:v",
                "3",
                str(thumbnail_path),
            ],
            purpose="thumbnail generation",
        )

        thumbnail_bytes = thumbnail_path.read_bytes()

        if not thumbnail_bytes:
            raise ValidationError(
                "The video thumbnail could not be generated."
            )

        return thumbnail_bytes
    finally:
        thumbnail_path.unlink(missing_ok=True)


def analyze_property_video(uploaded_file):
    """Validate an MP4 and return authoritative media metadata."""

    file_size = _validate_upload_envelope(uploaded_file)
    temporary_path, content_hash = _copy_upload_to_temporary_file(
        uploaded_file
    )

    try:
        probe = _probe_video(temporary_path)
        _validate_probe(probe)
        thumbnail_bytes = _generate_thumbnail(
            temporary_path,
            probe["duration_value"],
        )
    finally:
        temporary_path.unlink(missing_ok=True)
        _seek(uploaded_file)

    return PropertyVideoAnalysis(
        file_size=file_size,
        content_sha256=content_hash,
        width=probe["width"],
        height=probe["height"],
        duration=max(1, round(probe["duration_value"])),
        video_codec=probe["video_codec"],
        audio_codec=probe["audio_codec"],
        thumbnail_bytes=thumbnail_bytes,
    )
