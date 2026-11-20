"""Local Audio Enhancer — free, local voice/audio cleanup.

Pipeline: load (WAV/MP3/M4A via ffmpeg) -> trim silence ->
spectral noise reduction -> loudness normalisation (LUFS) ->
soft limiter -> export WAV/MP3 + Markdown report + waveform SVG.

100% local. No upload, no account, no API key.
"""

__version__ = "1.0.0"
__all__ = ["enhance_file"]

from .enhance import enhance_file
