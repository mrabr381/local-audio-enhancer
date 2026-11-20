"""The pipeline: trim silence -> spectral denoise -> normalise -> limit.

Order matters: trimming first means the noise profile is estimated
from real quiet parts, not long silences; normalising last means
the gain is computed from the cleaned signal.
"""

from __future__ import annotations

import math
import os

import numpy as np

from .denoise import spectral_gate
from .io import AudioError, load_audio, write_mp3, write_wav
from .measure import measure, noise_floor_dbfs


def trim_silence(audio: np.ndarray, rate: int,
                 margin_db: float = 12.0, pad_ms: int = 80) -> np.ndarray:
    """Cut leading/trailing silence (frames below noise floor + margin)."""
    if audio.size == 0:
        return audio
    floor = noise_floor_dbfs(audio, rate)
    threshold = 10.0 ** ((floor + margin_db) / 20.0)
    win = max(1, rate // 100)  # 10 ms frames
    n = len(audio) // win
    if n == 0:
        return audio
    frames = audio[: n * win].reshape(n, win)
    rms = np.sqrt(np.mean(frames ** 2, axis=1))
    voiced = np.where(rms > threshold)[0]
    if voiced.size == 0:
        return audio  # nothing above threshold — leave untouched
    pad = max(1, int(pad_ms / 10))
    start = max(0, int(voiced[0]) - pad) * win
    end = min(len(audio), (int(voiced[-1]) + 1 + pad) * win)
    return audio[start:end]


def _soft_limit(audio: np.ndarray, ceiling_db: float = -1.0) -> np.ndarray:
    """Gentle tanh soft-clip so peaks never exceed the ceiling."""
    ceiling = 10.0 ** (ceiling_db / 20.0)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak <= ceiling:
        return audio
    # Scale so the peak lands on the ceiling, then soft-clip the top.
    scaled = audio * (ceiling / peak)
    return np.tanh(scaled * 1.5) / np.tanh(1.5) * ceiling


def normalise_loudness(audio: np.ndarray, rate: int,
                       target_lufs: float) -> tuple[np.ndarray, float]:
    """Apply gain so integrated loudness hits the target. Returns (audio, gain_db)."""
    before = measure(rate, audio)
    gain_db = target_lufs - before["integrated_lufs"]
    # Never apply absurd gains (e.g. near-silent input): cap at +30 dB.
    gain_db = max(-40.0, min(30.0, gain_db))
    out = audio * (10.0 ** (gain_db / 20.0))
    out = _soft_limit(out)
    return out.astype(np.float32), round(gain_db, 2)


def enhance_file(input_path: str, output_dir: str,
                 target_lufs: float = -16.0,
                 denoise: bool = True,
                 trim: bool = True,
                 output_format: str = "wav") -> dict:
    """Run the full pipeline. Returns a dict with paths + measurements."""
    rate, audio = load_audio(input_path)
    before = measure(rate, audio)
    steps: list[str] = []

    work = audio
    if trim:
        trimmed = trim_silence(work, rate)
        if len(trimmed) != len(work):
            steps.append(f"trimmed silence: {len(work) / rate:.2f}s -> "
                         f"{len(trimmed) / rate:.2f}s")
        work = trimmed
    if denoise:
        work = spectral_gate(work, rate)
        steps.append("spectral noise reduction applied")
    work, gain_db = normalise_loudness(work, rate, target_lufs)
    steps.append(f"loudness normalised to {target_lufs} LUFS (gain {gain_db:+.2f} dB)")

    after = measure(rate, work)
    os.makedirs(output_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(input_path))[0]
    if output_format == "mp3":
        out_path = os.path.join(output_dir, f"{base}_enhanced.mp3")
        write_mp3(out_path, rate, work)
    elif output_format == "wav":
        out_path = os.path.join(output_dir, f"{base}_enhanced.wav")
        write_wav(out_path, rate, work)
    else:
        raise AudioError(f"Unsupported output format: {output_format}")

    return {
        "input": input_path,
        "output": out_path,
        "sample_rate": rate,
        "target_lufs": target_lufs,
        "gain_db": gain_db,
        "steps": steps,
        "before": before,
        "after": after,
        "before_audio": audio,
        "after_audio": work,
    }
