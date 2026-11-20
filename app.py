"""Streamlit web app for Local Audio Enhancer.

Upload a voice recording -> trim silence, remove noise, normalise
loudness -> listen to before/after and download the cleaned file.
Runs entirely on the machine hosting the app. No upload to any
third party, no account, no API key.
"""

import os
import tempfile

import streamlit as st

from audio_enhance.enhance import enhance_file
from audio_enhance.io import AudioError
from audio_enhance.report import write_waveform_svg

st.set_page_config(page_title="Local Audio Enhancer", page_icon="🎙️")
st.title("🎙️ Local Audio Enhancer")
st.write(
    "Clean a noisy voice recording on your own machine: "
    "trim silence, remove background noise, normalise loudness. "
    "Nothing is uploaded anywhere."
)

uploaded = st.file_uploader(
    "Choose an audio file", type=["wav", "mp3", "m4a", "ogg", "flac"])
target = st.slider("Target loudness (LUFS)", -30.0, -8.0, -16.0, 0.5,
                   help="-16 LUFS is the podcast standard; "
                        "-14 LUFS suits music-adjacent content.")
denoise = st.checkbox("Remove background noise", value=True)
trim = st.checkbox("Trim leading/trailing silence", value=True)
out_format = st.radio("Output format", ["wav", "mp3"], horizontal=True)

if uploaded is not None:
    suffix = os.path.splitext(uploaded.name)[1]
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_in:
        tmp_in.write(uploaded.getvalue())
        in_path = tmp_in.name
    with tempfile.TemporaryDirectory() as tmp_out:
        try:
            with st.spinner("Enhancing…"):
                result = enhance_file(
                    in_path, tmp_out, target_lufs=target,
                    denoise=denoise, trim=trim, output_format=out_format)
            b, a = result["before"], result["after"]
            st.subheader("Before / after")
            col1, col2, col3 = st.columns(3)
            col1.metric("Loudness", f"{a['integrated_lufs']} LUFS",
                        f"{a['integrated_lufs'] - b['integrated_lufs']:+.2f}")
            col2.metric("Noise floor", f"{a['noise_floor_dbfs']} dBFS",
                        f"{a['noise_floor_dbfs'] - b['noise_floor_dbfs']:+.2f} dB")
            col3.metric("Duration", f"{a['duration_s']} s",
                        f"{a['duration_s'] - b['duration_s']:+.2f} s")
            st.write("**Steps:** " + "; ".join(result["steps"]))

            svg_path = os.path.join(tmp_out, "waveform.svg")
            write_waveform_svg(svg_path, result["sample_rate"],
                               result["before_audio"], result["after_audio"])
            # st.image does not render SVG reliably; embed it as HTML.
            with open(svg_path, encoding="utf-8") as fh:
                st.markdown(fh.read(), unsafe_allow_html=True)
            st.caption("Waveform: before (top) / after (bottom)")

            st.audio(uploaded.getvalue(), format=f"audio/{suffix.lstrip('.')}")
            with open(result["output"], "rb") as fh:
                cleaned = fh.read()
            st.audio(cleaned, format=f"audio/{out_format}")
            st.download_button(
                "⬇️ Download cleaned audio",
                cleaned,
                file_name=os.path.basename(result["output"]),
                mime=f"audio/{out_format}")
        except AudioError as exc:
            st.error(f"Could not process this file: {exc}")
        finally:
            if os.path.exists(in_path):
                os.remove(in_path)
else:
    st.info("No file yet — or try the sample: regenerate it with "
            "`python scripts/make_sample.py`, then run the CLI "
            "`python -m audio_enhance --input sample_data/noisy.wav "
            "--out sample_output/`.")
