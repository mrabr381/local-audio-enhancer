"""CLI: python -m audio_enhance --input noisy.wav --out report/"""

from __future__ import annotations

import argparse
import os
import sys

from .enhance import enhance_file
from .io import AudioError
from .report import write_report, write_waveform_csv, write_waveform_svg


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="audio-enhance",
        description="Clean a noisy voice recording locally: "
                    "trim silence, remove noise, normalise loudness.",
    )
    p.add_argument("--input", required=True, help="Input audio (WAV/MP3/M4A/...)")
    p.add_argument("--out", required=True, help="Output folder for cleaned audio + report")
    p.add_argument("--target-lufs", type=float, default=-16.0,
                   help="Target integrated loudness in LUFS (default: -16, podcast standard)")
    p.add_argument("--no-denoise", action="store_true", help="Skip noise reduction")
    p.add_argument("--no-trim", action="store_true", help="Skip silence trimming")
    p.add_argument("--format", choices=["wav", "mp3"], default="wav",
                   help="Output audio format (default: wav)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not (-40.0 <= args.target_lufs <= 0.0):
        print(f"Error: --target-lufs must be between -40 and 0 (got {args.target_lufs}).",
              file=sys.stderr)
        return 2
    try:
        result = enhance_file(
            args.input, args.out,
            target_lufs=args.target_lufs,
            denoise=not args.no_denoise,
            trim=not args.no_trim,
            output_format=args.format,
        )
    except AudioError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    b, a = result["before"], result["after"]
    write_report(os.path.join(args.out, "report.md"), result)
    write_waveform_svg(
        os.path.join(args.out, "waveform.svg"),
        result["sample_rate"], result["before_audio"], result["after_audio"])
    write_waveform_csv(
        os.path.join(args.out, "waveform.csv"),
        result["sample_rate"], result["before_audio"], result["after_audio"])

    print(f"Input : {os.path.basename(args.input)} "
          f"({b['duration_s']}s, {b['integrated_lufs']} LUFS, "
          f"noise floor {b['noise_floor_dbfs']} dBFS)")
    print(f"Output: {os.path.basename(result['output'])} "
          f"({a['duration_s']}s, {a['integrated_lufs']} LUFS, "
          f"noise floor {a['noise_floor_dbfs']} dBFS)")
    print(f"Noise floor improved by "
          f"{a['noise_floor_dbfs'] - b['noise_floor_dbfs']:+.2f} dB; "
          f"gain applied {result['gain_db']:+.2f} dB")
    print(f"Report: {os.path.join(args.out, 'report.md')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
