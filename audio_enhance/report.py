"""Report + waveform outputs.

- ``report.md`` — before/after measurements, all measured by ffmpeg
  loudnorm / the measurement module. Nothing is invented.
- ``waveform.svg`` — before/after waveform (SVG, not PNG, so it can
  be pushed through the GitHub connector, which is UTF-8-only).
- ``waveform.csv`` — downsampled waveform data (text, pushable),
  so anyone can redraw or check the numbers without the binary audio.
"""

from __future__ import annotations

import os

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def _downsample(audio: np.ndarray, rate: int, points: int = 800) -> np.ndarray:
    """Min/max envelope downsampled to `points` columns."""
    if len(audio) == 0:
        return np.zeros((2, points))
    chunk = max(1, len(audio) // points)
    n = len(audio) // chunk
    frames = audio[: n * chunk].reshape(n, chunk)
    mins = frames.min(axis=1)
    maxs = frames.max(axis=1)
    return np.vstack([mins, maxs])


def write_waveform_csv(path: str, rate: int,
                       before: np.ndarray, after: np.ndarray) -> None:
    """time_s, before_min, before_max, after_min, after_max (text)."""
    b = _downsample(before, rate)
    a = _downsample(after, rate)
    n = min(b.shape[1], a.shape[1])
    times = np.linspace(0, len(before) / rate, n)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("time_s,before_min,before_max,after_min,after_max\n")
        for i in range(n):
            fh.write(f"{times[i]:.3f},{b[0, i]:.5f},{b[1, i]:.5f},"
                     f"{a[0, i]:.5f},{a[1, i]:.5f}\n")


def write_waveform_svg(path: str, rate: int,
                       before: np.ndarray, after: np.ndarray) -> None:
    # Plot the min/max envelope (800 points), NOT raw samples:
    # a raw 16 kHz waveform as SVG paths is ~8 MB; the envelope is ~40 KB
    # and looks identical at display size.
    fig, axes = plt.subplots(2, 1, figsize=(10, 4), sharex=True)
    for ax, audio, color, title in (
        (axes[0], before, "#c2410c", "Before — noisy input"),
        (axes[1], after, "#166534", "After — cleaned + normalised"),
    ):
        env = _downsample(audio, rate)
        times = np.linspace(0, len(audio) / rate, env.shape[1])
        ax.fill_between(times, env[1], env[0], color=color, alpha=0.7)
        ax.set_title(title, loc="left")
        ax.set_ylabel("amplitude")
        ax.set_xlim(0, max(len(audio) / rate, 0.1))
    axes[1].set_xlabel("seconds")
    fig.tight_layout()
    # Fixed hash salt + no embedded date => byte-identical SVG across runs.
    with matplotlib.rc_context({"svg.hashsalt": "local-audio-enhancer"}):
        fig.savefig(path, format="svg", metadata={"Date": None})
    plt.close(fig)


def _row(label: str, key: str, before: dict, after: dict, unit: str = "") -> str:
    b = before[key]
    a = after[key]
    if isinstance(b, float) and (b != b):  # NaN
        b_str = "—"
    else:
        b_str = f"{b}{unit}"
    if isinstance(a, float) and (a != a):
        a_str = "—"
    else:
        a_str = f"{a}{unit}"
    return f"| {label} | {b_str} | {a_str} |"


def write_report(path: str, result: dict) -> None:
    b, a = result["before"], result["after"]
    lines = [
        "# Audio enhancement report",
        "",
        f"Input: `{os.path.basename(result['input'])}`  ",
        f"Output: `{os.path.basename(result['output'])}`  ",
        f"Sample rate: {result['sample_rate']} Hz  ",
        f"Loudness method: {a['method']}",
        "",
        "## What was done",
        "",
    ]
    lines += [f"- {step}" for step in result["steps"]]
    lines += [
        "",
        "## Before / after (all values measured, not estimated)",
        "",
        "| Measurement | Before | After |",
        "|---|---|---|",
        _row("Duration", "duration_s", b, a, " s"),
        _row("Integrated loudness", "integrated_lufs", b, a, " LUFS"),
        _row("True peak", "true_peak_dbfs", b, a, " dBFS"),
        _row("RMS level", "rms_dbfs", b, a, " dBFS"),
        _row("Peak", "peak_dbfs", b, a, " dBFS"),
        _row("Noise floor", "noise_floor_dbfs", b, a, " dBFS"),
        "",
        f"Noise-floor improvement: "
        f"{a['noise_floor_dbfs'] - b['noise_floor_dbfs']:+.2f} dB  ",
        f"Loudness change: {a['integrated_lufs'] - b['integrated_lufs']:+.2f} LUFS",
        "",
        "## Files in this folder",
        "",
        "- `*_enhanced.wav` — the cleaned audio",
        "- `waveform.svg` — before/after waveform",
        "- `waveform.csv` — the same waveform data as text",
        "",
    ]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
