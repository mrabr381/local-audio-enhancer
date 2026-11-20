"""Spectral noise reduction (spectral gating).

STFT -> estimate a noise magnitude profile from the quietest
frames -> attenuate bins that sit close to the noise floor ->
inverse STFT. Over-subtraction is capped and the gate is
smoothed in time and frequency so words are not chopped.
This is a classic spectral-gating approach (the same family as
RNNoise-style / Audacity noise reduction), implemented locally
with numpy/scipy — no model download, no network.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import get_window, istft, stft


def _noise_profile(magnitude: np.ndarray, frame_rms: np.ndarray,
                   quiet_fraction: float = 0.2) -> np.ndarray:
    """Median magnitude spectrum of the quietest frames."""
    n_frames = magnitude.shape[1]
    n_quiet = max(1, int(n_frames * quiet_fraction))
    quiet_idx = np.argsort(frame_rms)[:n_quiet]
    return np.median(magnitude[:, quiet_idx], axis=1, keepdims=True)


def spectral_gate(audio: np.ndarray, rate: int,
                  reduction_db: float = 18.0,
                  noise_factor: float = 1.5) -> np.ndarray:
    """Attenuate stationary noise. Returns same-length audio."""
    if audio.size == 0:
        return audio
    nperseg = 2048
    if len(audio) < nperseg:
        return audio  # too short to gate safely — leave untouched
    _, _, zxx = stft(audio, fs=rate, window="hann", nperseg=nperseg,
                     noverlap=nperseg // 2, nfft=nperseg)
    magnitude = np.abs(zxx)
    phase = np.exp(1j * np.angle(zxx))
    frame_rms = np.sqrt(np.mean(magnitude ** 2, axis=0))

    noise = _noise_profile(magnitude, frame_rms)
    floor = 10.0 ** (-reduction_db / 20.0)  # max attenuation, e.g. -18 dB

    # Gain per bin: 1 where signal >> noise, `floor` where signal ~= noise.
    excess = magnitude / np.maximum(noise_factor * noise, 1e-12)
    gain = np.clip(excess - 1.0, 0.0, 1.0)  # 0..1 ramp
    gain = floor + (1.0 - floor) * gain

    # Smooth the gate in time (3 frames) and frequency (3 bins) so
    # it does not flutter and chop word onsets.
    from scipy.ndimage import uniform_filter1d

    gain = uniform_filter1d(uniform_filter1d(gain, 3, axis=0, mode="nearest"),
                            3, axis=1, mode="nearest")

    cleaned = istft(magnitude * gain * phase, fs=rate, window="hann",
                    nperseg=nperseg, noverlap=nperseg // 2, nfft=nperseg)[1]
    # istft can return a slightly different length; trim/pad to match.
    if len(cleaned) > len(audio):
        cleaned = cleaned[: len(audio)]
    elif len(cleaned) < len(audio):
        cleaned = np.pad(cleaned, (0, len(audio) - len(cleaned)))
    return cleaned.astype(np.float32)
