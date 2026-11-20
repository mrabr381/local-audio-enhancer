"""Audio loading / writing.

WAV is read with scipy (no extra dependency). Anything else
(MP3, M4A, OGG, FLAC, ...) is decoded to 16-bit PCM WAV through
ffmpeg, which is a documented requirement. Output is WAV by
default; MP3 export also goes through ffmpeg.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

import numpy as np
from scipy.io import wavfile

FFMPEG = shutil.which("ffmpeg")

SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".aac", ".wma"}


class AudioError(Exception):
    """Raised for any unreadable / unsupported input."""


def _decode_with_ffmpeg(path: str) -> tuple[int, np.ndarray]:
    """Decode any ffmpeg-supported file to mono float32 in [-1, 1]."""
    if FFMPEG is None:
        raise AudioError(
            "ffmpeg is required to read this file type. "
            "Install ffmpeg (https://ffmpeg.org/download.html) and retry, "
            "or use a WAV file."
        )
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        cmd = [
            FFMPEG, "-y", "-v", "error", "-i", path,
            "-ac", "1", "-ar", "48000", "-sample_fmt", "s16", tmp_path,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if proc.returncode != 0 or not os.path.exists(tmp_path):
            raise AudioError(
                f"ffmpeg could not decode '{os.path.basename(path)}': "
                f"{(proc.stderr or 'unknown error').strip()}"
            )
        return _read_wav(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _read_wav(path: str) -> tuple[int, np.ndarray]:
    try:
        rate, data = wavfile.read(path)
    except Exception as exc:  # corrupt / truncated WAV
        raise AudioError(f"Could not read WAV file '{os.path.basename(path)}': {exc}")
    if data.size == 0:
        raise AudioError(f"Audio file '{os.path.basename(path)}' is empty (0 samples).")
    if data.ndim == 2:  # stereo -> mono by averaging channels
        data = data.mean(axis=1)
    if data.dtype == np.int16:
        audio = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        audio = data.astype(np.float32) / 2147483648.0
    elif data.dtype == np.uint8:
        audio = (data.astype(np.float32) - 128.0) / 128.0
    elif data.dtype in (np.float32, np.float64):
        audio = data.astype(np.float32)
    else:
        raise AudioError(f"Unsupported WAV sample format: {data.dtype}")
    return int(rate), np.ascontiguousarray(audio, dtype=np.float32)


def load_audio(path: str) -> tuple[int, np.ndarray]:
    """Load an audio file as (sample_rate, mono float32 in [-1, 1])."""
    if not os.path.isfile(path):
        raise AudioError(f"File not found: {path}")
    ext = os.path.splitext(path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise AudioError(
            f"Unsupported file type '{ext}'. Supported: "
            + ", ".join(sorted(SUPPORTED_EXTENSIONS))
        )
    if ext == ".wav":
        return _read_wav(path)
    return _decode_with_ffmpeg(path)


def write_wav(path: str, rate: int, audio: np.ndarray) -> None:
    """Write mono float32 audio as 16-bit PCM WAV."""
    clipped = np.clip(audio, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype(np.int16)
    wavfile.write(path, rate, pcm)


def write_mp3(path: str, rate: int, audio: np.ndarray) -> None:
    """Write MP3 via ffmpeg (192 kbps). Requires ffmpeg."""
    if FFMPEG is None:
        raise AudioError("ffmpeg is required to export MP3. Install ffmpeg and retry.")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        write_wav(tmp_path, rate, audio)
        cmd = [
            FFMPEG, "-y", "-v", "error", "-i", tmp_path,
            "-codec:a", "libmp3lame", "-b:a", "192k", path,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            raise AudioError(f"ffmpeg MP3 export failed: {(proc.stderr or '').strip()}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
