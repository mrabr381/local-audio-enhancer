# Local Audio Enhancer 🎙️

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![No account](https://img.shields.io/badge/account-none%20required-brightgreen.svg)](#quickstart)
[![No upload](https://img.shields.io/badge/upload-none%20%E2%80%94%20100%25%20local-brightgreen.svg)](#how-it-works)
[![ffmpeg](https://img.shields.io/badge/ffmpeg-required-orange.svg)](#requirements)

Clean a noisy voice recording on your own machine — remove background
noise, trim silence, normalise loudness to a broadcast target — with
no upload, no account, no subscription and no per-minute fees. Paid
enhancers charge per minute or per month; this one costs nothing and
your audio never leaves your computer.

> **Live demo:** a real sample report with measured numbers and the
> before/after waveform — [sample report page](sample_output/index.html)
> (works on GitHub Pages, no server needed) — or run the web app on
> Streamlit Community Cloud (one-click deploy, see
> [Live demo](#live-demo)).

## Table of contents

- [Before / after](#before--after)
- [How it works](#how-it-works)
- [Quickstart](#quickstart)
- [What it produces](#what-it-produces)
- [Live demo](#live-demo)
- [Comparison](#comparison)
- [Honest limitations](#honest-limitations)
- [Project structure](#project-structure)

## Before / after

Sample: synthetic voice-like syllables + white noise, rumble and 50 Hz
hum (fully synthetic — no real person's voice). Measured with ffmpeg
`loudnorm` (ITU-R BS.1770), verified 2026-11-20:

| Measurement | Before | After |
|---|---|---|
| Integrated loudness | −15.45 LUFS | **−15.99 LUFS** (target −16) |
| Noise floor | −20.22 dBFS | **−30.54 dBFS** (−10.32 dB) |
| True peak | −1.36 dBFS | −1.95 dBFS (no clipping) |
| Duration | 4.88 s | 4.88 s (nothing cut — see below) |
| RMS level | −15.44 dBFS | −15.32 dBFS |

<details>
<summary>Full sample report (real output)</summary>

```
Input : noisy.wav (4.88s, -15.45 LUFS, noise floor -20.22 dBFS)
Output: noisy_enhanced.wav (4.88s, -15.99 LUFS, noise floor -30.54 dBFS)
Noise floor improved by -10.32 dB; gain applied +2.64 dB
```

Word-preservation check (measured, not assumed): in voiced regions
the enhanced audio correlates **0.975** with the known-clean
reference, and gap (between-words) RMS fell from 0.099 to 0.033 —
noise went down, words stayed.

</details>

The sample's 0.5 s lead-in is loud noise, not silence, so the trimmer
correctly left it alone (duration unchanged). Trimming was verified
separately: a 6.88 s file padded with 1 s of digital silence at each
end came out at 4.42 s — exactly the content span plus the 80 ms
padding.

## How it works

1. **Load** — WAV via scipy; MP3/M4A/OGG/FLAC via ffmpeg decode.
2. **Trim silence** — frames below (noise floor + 12 dB) are cut from
   the start/end, keeping 80 ms of padding.
3. **Spectral noise reduction** — STFT, noise profile from the
   quietest frames, per-bin gating smoothed in time and frequency
   (max −18 dB), so word onsets are not chopped.
4. **Loudness normalisation** — gain computed from ffmpeg loudnorm's
   integrated LUFS, capped at ±30 dB, then a gentle tanh soft-limiter
   keeps the true peak under −1 dBFS.
5. **Report** — Markdown report + waveform SVG + waveform CSV, all
   measured values, nothing invented.

## Requirements

- Python 3.10+
- **ffmpeg** (required for loudness measurement and for MP3/M4A
  input/output): `sudo apt install ffmpeg` · `brew install ffmpeg` ·
  [ffmpeg.org/download.html](https://ffmpeg.org/download.html)
- pip packages in `requirements.txt` (numpy, scipy, matplotlib,
  streamlit)

## Quickstart

```bash
git clone https://github.com/mrabr381/local-audio-enhancer.git
cd local-audio-enhancer
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. Regenerate the sample (audio files are binary and are not in the repo)
python scripts/make_sample.py

# 2. Enhance it
python -m audio_enhance --input sample_data/noisy.wav --out sample_output/

# 3. Your own recording
python -m audio_enhance --input my-voice.mp3 --out report/ --target-lufs -16 --format mp3
```

Options: `--target-lufs` (default −16, podcast standard; −14 suits
music-adjacent content), `--no-denoise`, `--no-trim`,
`--format wav|mp3`.

## What it produces

- **`*_enhanced.wav` / `.mp3`** — the cleaned audio.
- **`report.md`** — before/after loudness, peak, RMS, noise floor.
- **`waveform.svg`** — before/after waveform (SVG, not PNG, so the
  demo page works on GitHub Pages).
- **`waveform.csv`** — the same waveform data as text, so anyone can
  redraw or check the numbers without the binary audio.

## Live demo

- ✅ **Already built:** [sample_output/index.html](sample_output/index.html)
  — static page showing the real sample report (numbers, waveform,
  download links), zero external requests.
  **ABR's step (2 min):** repo Settings → Pages → Source: Deploy from a
  branch → `main`, folder `/ (root)` → Save. Live at
  `https://mrabr381.github.io/local-audio-enhancer/sample_output/`.
- ✅ **Streamlit Cloud ready:** `app.py` at the repo root, clean
  `requirements.txt`, and `packages.txt` (installs ffmpeg on the
  Streamlit host — ffmpeg is not preinstalled there). **ABR's step
  (1 click):** share.streamlit.io → Create app → repo
  `mrabr381/local-audio-enhancer`, branch `main`, file `app.py` →
  Deploy. Upload a file, listen before/after, download the cleaned
  audio.

## Comparison

| | Local Audio Enhancer | Paid enhancers (Adobe Podcast Enhance, Auphonic, Krisp) |
|---|---|---|
| Price | **Free, forever** | Paid tools charge per minute / per month (no prices quoted — verify on their own pricing pages) |
| Upload | **None — 100% local** | Audio is uploaded to their servers |
| Time limit | None | Usually capped on free tiers |
| Loudness target | Any LUFS you set | Fixed presets |
| Source code | Open (MIT) | Closed |

## Honest limitations

- **No human listening test.** Quality was verified with numbers
  (noise floor −10.32 dB, voiced correlation 0.975, no clipping),
  not by ear. Listen to the output before using it for anything
  important.
- **Spectral gating, not AI.** Stationary noise (hiss, hum, fan)
  drops a lot; sudden noises (door slams, keyboard clacks) mostly
  stay. There is no de-esser and no de-reverb.
- **Synthetic sample.** The demo voice is formant-synthesised
  syllables, not real speech — it proves the pipeline, not how it
  sounds on your voice.
- **Loudness measurement needs ffmpeg.** Without it, the tool falls
  back to an RMS estimate, clearly labelled in the report.
- **Long files are slower.** The gate is vectorised, but a 60-minute
  recording still takes a few minutes on a normal laptop.
- **MP3 export needs ffmpeg.** WAV export works without it.

## Project structure

```
├── app.py                      # Streamlit web app (repo root, deploy-ready)
├── audio_enhance/
│   ├── __init__.py  __main__.py
│   ├── cli.py                  # argument parsing, exit codes 0/1/2
│   ├── io.py                   # WAV + ffmpeg load/write
│   ├── measure.py              # ffmpeg loudnorm, noise floor, peak, RMS
│   ├── denoise.py              # spectral gating (STFT)
│   ├── enhance.py              # trim -> denoise -> normalise -> limit
│   └── report.py               # report.md + waveform SVG + waveform CSV
├── scripts/
│   └── make_sample.py          # regenerates sample_data/*.wav (synthetic)
├── sample_data/                # regenerated locally — binary, not in the repo
│   └── noisy.wav / clean_reference.wav
└── sample_output/              # real sample report + waveform SVG/CSV + demo page
    ├── report.md  waveform.svg  waveform.csv  index.html
```

## Contributing

Issues and pull requests are welcome. Please keep the quality promise:
no invented numbers, every measurement reproducible with the commands
above, and every new feature covered by a test on the sample audio.
