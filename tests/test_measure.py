"""Tests for the audio measurement maths (audio_enhance.measure) and the
silence trimmer (audio_enhance.enhance.trim_silence).

Every expected value is derived by hand from the function definitions,
except test_sample_numbers_reproduce, which checks the verified sample
measurements recorded in the README (-15.45 LUFS, -20.22 dBFS noise
floor) against the real sample file when it is present locally.
"""

import math
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from audio_enhance.enhance import normalise_loudness, trim_silence
from audio_enhance.measure import (
    duration_seconds,
    measure,
    noise_floor_dbfs,
    peak_dbfs,
    rms_dbfs,
)

RATE = 16000
REPO = Path(__file__).resolve().parent.parent


def sine(amplitude, seconds=1.0, rate=RATE, freq=440.0):
    t = np.arange(int(seconds * rate)) / rate
    return (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.float64)


def test_rms_dbfs_known_values():
    assert rms_dbfs(np.zeros(1000)) == -math.inf
    assert rms_dbfs(np.ones(1000)) == pytest.approx(0.0, abs=1e-9)
    # Constant 0.5 -> 20*log10(0.5) = -6.02 dBFS.
    assert rms_dbfs(np.full(1000, 0.5)) == pytest.approx(-6.02, abs=0.01)
    # Sine of amplitude A has RMS A/sqrt(2): 0.5 -> -9.03 dBFS.
    assert rms_dbfs(sine(0.5)) == pytest.approx(-9.03, abs=0.02)


def test_peak_dbfs_known_values():
    assert peak_dbfs(np.zeros(1000)) == -math.inf
    assert peak_dbfs(np.array([0.25, -0.5, 0.1])) == pytest.approx(-6.02, abs=0.01)
    assert peak_dbfs(np.ones(100)) == pytest.approx(0.0, abs=1e-9)


def test_duration_seconds():
    assert duration_seconds(np.zeros(48000), 16000) == pytest.approx(3.0)
    assert duration_seconds(np.zeros(8000), 16000) == pytest.approx(0.5)


def test_noise_floor_uses_quietest_windows():
    # 5 s loud (amp 0.5 sine, RMS -9.03 dBFS) then 5 s quiet (amp 0.01
    # sine, RMS -43.01 dBFS). The noise floor must come from the quiet
    # half, not the average of the whole file.
    audio = np.concatenate([sine(0.5, seconds=5.0), sine(0.01, seconds=5.0)])
    assert noise_floor_dbfs(audio, RATE) == pytest.approx(-43.01, abs=0.5)


def test_trim_silence_cuts_padded_silence():
    # 1 s silence + 2 s tone + 1 s silence. Expect ~2 s of content plus
    # the 80 ms padding on each side (~2.16 s), and shorter than 4 s.
    audio = np.concatenate(
        [np.zeros(RATE), sine(0.5, seconds=2.0), np.zeros(RATE)]
    )
    trimmed = trim_silence(audio, RATE)
    assert 2.0 < len(trimmed) / RATE < 2.3
    assert len(trimmed) < len(audio)


def test_trim_silence_leaves_pure_silence_alone():
    audio = np.zeros(2 * RATE)
    assert len(trim_silence(audio, RATE)) == len(audio)


def test_measure_returns_all_keys():
    result = measure(RATE, sine(0.5))
    for key in (
        "duration_s",
        "peak_dbfs",
        "rms_dbfs",
        "noise_floor_dbfs",
        "integrated_lufs",
        "true_peak_dbfs",
        "method",
    ):
        assert key in result
    assert result["duration_s"] == pytest.approx(1.0)
    assert result["rms_dbfs"] == pytest.approx(-9.03, abs=0.05)


def test_normalise_gain_is_capped_at_30_db():
    # Near-silent input would need >100 dB of gain; the cap is +30 dB.
    audio = np.full(RATE, 1e-6)
    _, gain_db = normalise_loudness(audio, RATE, target_lufs=-16.0)
    assert gain_db == pytest.approx(30.0)


@pytest.mark.skipif(
    not (REPO / "sample_data" / "noisy.wav").exists(),
    reason="sample audio is binary and regenerated locally, not in the repo",
)
@pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="loudnorm measurement needs ffmpeg"
)
def test_sample_numbers_reproduce():
    """The README's verified sample numbers, recomputed from the file."""
    from audio_enhance.io import load_audio

    rate, audio = load_audio(str(REPO / "sample_data" / "noisy.wav"))
    result = measure(rate, audio)
    assert result["duration_s"] == pytest.approx(4.88, abs=0.01)
    assert result["noise_floor_dbfs"] == pytest.approx(-20.22, abs=0.1)
    assert result["rms_dbfs"] == pytest.approx(-15.44, abs=0.1)
    assert result["integrated_lufs"] == pytest.approx(-15.45, abs=0.1)
    assert result["true_peak_dbfs"] == pytest.approx(-1.36, abs=0.1)
