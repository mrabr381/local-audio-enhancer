"""Generate the sample audio (fully synthetic — no real person's voice).

Creates two files in sample_data/:
- ``noisy.wav`` — synthetic "voice-like" syllables + room noise + hum.
  This is the demo input.
- ``clean_reference.wav`` — the same syllables WITHOUT noise, so the
  enhancer's output can be compared against a known-clean signal.

Both files are binary and CANNOT be pushed through the GitHub
connector (UTF-8-only), so this script is the source of truth:
anyone who clones the repo regenerates them with one command.
The text-only record of the sample (waveform data + measurements)
lives in sample_output/waveform.csv and sample_output/report.md.
"""

from __future__ import annotations

import os
import sys

import numpy as np
from scipy.io import wavfile

SR = 16000

# Vowel formants (F1, F2, F3) in Hz — the classic Peterson & Barney values.
VOWELS = {
    "a": (730, 1090, 2440),
    "e": (530, 1840, 2480),
    "i": (270, 2290, 3010),
    "o": (570, 840, 2410),
    "u": (300, 870, 2240),
}

# (vowel, duration_s, f0_hz) — three short "sentences" of syllables.
SCRIPT = [
    ("a", 0.22, 118), ("e", 0.18, 122), ("i", 0.20, 115),
    ("o", 0.24, 110), ("u", 0.18, 108),
    ("e", 0.20, 124), ("a", 0.22, 120), ("i", 0.18, 126),
    ("o", 0.22, 112), ("u", 0.20, 109), ("a", 0.24, 117),
    ("i", 0.20, 121),
]


def syllable(vowel: str, duration: float, f0: float, sr: int) -> np.ndarray:
    """One vowel-like syllable: harmonics shaped by formants."""
    n = int(duration * sr)
    t = np.arange(n) / sr
    formants = VOWELS[vowel]
    signal = np.zeros(n)
    for harmonic in range(1, 13):
        freq = f0 * harmonic
        if freq > 5000:
            break
        amp = 1.0 / harmonic  # natural roll-off
        for f_formant in formants:
            amp *= 1.0 + 2.0 * np.exp(-((freq - f_formant) / 220.0) ** 2)
        signal += amp * np.sin(2 * np.pi * freq * t)
    signal /= np.max(np.abs(signal))
    # Raised-cosine attack/decay envelope (syllable shape).
    attack = int(0.03 * sr)
    decay = int(0.05 * sr)
    env = np.ones(n)
    env[:attack] = 0.5 - 0.5 * np.cos(np.pi * np.arange(attack) / attack)
    env[-decay:] = 0.5 + 0.5 * np.cos(np.pi * np.arange(decay) / decay)
    return signal * env * 0.5


def make_clean(seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    parts: list[np.ndarray] = [np.zeros(int(0.5 * SR))]  # 0.5 s lead-in
    for i, (vowel, dur, f0) in enumerate(SCRIPT):
        parts.append(syllable(vowel, dur, f0 * rng.uniform(0.97, 1.03), SR))
        gap = 0.35 if i in (4, 8) else 0.12  # sentence pauses
        parts.append(np.zeros(int(gap * SR)))
    audio = np.concatenate(parts)
    audio /= np.max(np.abs(audio))
    return (audio * 0.6).astype(np.float32)


def add_noise(clean: np.ndarray, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = len(clean)
    t = np.arange(n) / SR
    white = rng.standard_normal(n)
    # Low rumble (fan-like): white noise, heavily smoothed.
    rumble = np.convolve(white, np.ones(400) / 400.0, mode="same")
    hum = 0.08 * np.sin(2 * np.pi * 50 * t)
    noise = 0.10 * white + 0.25 * rumble + hum
    noisy = clean + noise.astype(np.float32)
    peak = np.max(np.abs(noisy))
    return (noisy / peak * 0.85).astype(np.float32)


def main() -> int:
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(here, "sample_data")
    os.makedirs(out_dir, exist_ok=True)
    clean = make_clean()
    noisy = add_noise(clean)
    wavfile.write(os.path.join(out_dir, "clean_reference.wav"),
                  SR, (clean * 32767).astype(np.int16))
    wavfile.write(os.path.join(out_dir, "noisy.wav"),
                  SR, (noisy * 32767).astype(np.int16))
    print(f"wrote sample_data/clean_reference.wav ({len(clean) / SR:.2f}s)")
    print(f"wrote sample_data/noisy.wav ({len(noisy) / SR:.2f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
