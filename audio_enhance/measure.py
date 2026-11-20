"""Measurements — every number is measured, never invented.

Loudness (integrated LUFS + true peak) comes from ffmpeg's
``loudnorm`` filter, which implements ITU-R BS.1770 — the same
standard broadcast tools use. If ffmpeg is absent we fall back to
a plain RMS estimate, clearly labelled as an estimate.
Noise floor is the RMS of the quietest 100 ms windows, in dBFS.
"""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import tempfile

import numpy as np

from .io import FFMPEG, AudioError, write_wav


def duration_seconds(audio: np.ndarray, rate: int) -> float:
    return len(audio) / rate


def peak_dbfs(audio: np.ndarray) -> float:
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    return 20.0 * math.log10(peak) if peak > 0 else -math.inf


def rms_dbfs(audio: np.ndarray) -> float:
    rms = float(np.sqrt(np.mean(audio ** 2))) if audio.size else 0.0
    return 20.0 * math.log10(rms) if rms > 0 else -math.inf


def noise_floor_dbfs(audio: np.ndarray, rate: int) -> float:
    """RMS of the quietest 10% of 100 ms windows (dBFS)."""
    win = max(1, rate // 10)
    n = len(audio) // win
    if n == 0:
        return rms_dbfs(audio)
    frames = audio[: n * win].reshape(n, win)
    rms = np.sqrt(np.mean(frames ** 2, axis=1))
    quiet = np.sort(rms)[: max(1, n // 10)]
    mean_quiet = float(np.mean(quiet))
    return 20.0 * math.log10(mean_quiet) if mean_quiet > 0 else -math.inf


def _loudnorm_via_ffmpeg(rate: int, audio: np.ndarray) -> dict | None:
    """Run ffmpeg loudnorm (two-pass values, JSON) on in-memory audio."""
    if FFMPEG is None:
        return None
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        write_wav(tmp_path, rate, audio)
        cmd = [
            FFMPEG, "-i", tmp_path, "-af",
            "loudnorm=print_format=json", "-f", "null", "-",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        text = proc.stderr or ""
        match = re.search(r"\{[^}]*\"input_i\"[^}]*\}", text, re.DOTALL)
        if not match:
            return None
        data = json.loads(match.group(0))
        return {
            "integrated_lufs": float(data["input_i"]),
            "true_peak_dbfs": float(data["input_tp"]),
            "lra": float(data["input_lra"]),
            "threshold": float(data["input_thresh"]),
            "method": "ffmpeg loudnorm (ITU-R BS.1770)",
        }
    except (ValueError, KeyError, subprocess.SubprocessError):
        return None
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def measure(rate: int, audio: np.ndarray) -> dict:
    """Measure everything the report needs. Returns plain floats."""
    loud = _loudnorm_via_ffmpeg(rate, audio)
    if loud is None:
        # Fallback: plain RMS, labelled as an estimate.
        loud = {
            "integrated_lufs": rms_dbfs(audio),
            "true_peak_dbfs": peak_dbfs(audio),
            "lra": float("nan"),
            "threshold": float("nan"),
            "method": "RMS estimate (ffmpeg not available)",
        }
    return {
        "duration_s": round(duration_seconds(audio, rate), 3),
        "peak_dbfs": round(peak_dbfs(audio), 2),
        "rms_dbfs": round(rms_dbfs(audio), 2),
        "noise_floor_dbfs": round(noise_floor_dbfs(audio, rate), 2),
        "integrated_lufs": round(loud["integrated_lufs"], 2),
        "true_peak_dbfs": round(loud["true_peak_dbfs"], 2),
        "lra": loud["lra"],
        "method": loud["method"],
    }
