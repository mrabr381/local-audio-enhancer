# Audio enhancement report

Input: `noisy.wav`  
Output: `noisy_enhanced.wav`  
Sample rate: 16000 Hz  
Loudness method: ffmpeg loudnorm (ITU-R BS.1770)

## What was done

- spectral noise reduction applied
- loudness normalised to -16.0 LUFS (gain +2.64 dB)

## Before / after (all values measured, not estimated)

| Measurement | Before | After |
|---|---|---|
| Duration | 4.88 s | 4.88 s |
| Integrated loudness | -15.45 LUFS | -15.99 LUFS |
| True peak | -1.36 dBFS | -1.95 dBFS |
| RMS level | -15.44 dBFS | -15.32 dBFS |
| Peak | -1.41 dBFS | -2.03 dBFS |
| Noise floor | -20.22 dBFS | -30.54 dBFS |

Noise-floor improvement: -10.32 dB  
Loudness change: -0.54 LUFS

## Files in this folder

- `*_enhanced.wav` — the cleaned audio
- `waveform.svg` — before/after waveform
- `waveform.csv` — the same waveform data as text
