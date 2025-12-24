# app.py
import asyncio
from io import BytesIO

import edge_tts
import streamlit as st


# ---------- Edge-TTS helper (async -> bytes) ----------
async def tts_to_bytes(text: str, voice: str, rate: int = 0, pitch: int = 0) -> bytes:
    """
    text  : text to speak
    voice : e.g. 'en-US-AndrewNeural'
    rate  : -50 .. 50  (percent)
    pitch : -50 .. 50  (Hz-ish)
    """
    if not text.strip():
        return b""

    rate_str = f"{rate:+d}%"
    pitch_str = f"{pitch:+d}Hz"

    communicate = edge_tts.Communicate(
        text,
        voice,
        rate=rate_str,
        pitch=pitch_str,
    )
    # edge-tts basic usage: Communicate(...).stream() :contentReference[oaicite:1]{index=1}

    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]

    return audio_data


def synthesize(text: str, voice: str, rate: int, pitch: int) -> bytes:
    """Sync wrapper for Streamlit."""
    return asyncio.run(tts_to_bytes(text, voice, rate, pitch))


# ---------- Streamlit UI ----------
st.set_page_config(page_title="Edge-TTS Andrew Demo", page_icon="🔊")

st.title("🔊 Edge-TTS Andrew Voice (Streamlit App)")
st.write(
    "Yeh demo Microsoft Edge / Azure Andrew voice use karta hai. "
    "Learning / low-volume use ke liye theek hai, heavy commercial se pehle "
    "Microsoft ke terms zaroor padh lo."
)

text = st.text_area(
    "Text likho:",
    "Hello, this is Andrew speaking from an Edge-TTS Streamlit app!",
    height=150,
    max_chars=2000,  # thoda safe limit
)

voice_options = {
    "Andrew (en-US-AndrewNeural)": "en-US-AndrewNeural",
    "Andrew Multilingual (en-US-AndrewMultilingualNeural)": "en-US-AndrewMultilingualNeural",
}
voice_label = st.selectbox("Voice choose karo:", list(voice_options.keys()))
voice_id = voice_options[voice_label]

col1, col2 = st.columns(2)
with col1:
    rate = st.slider("Rate (speed %)", -50, 50, 0, step=5)
with col2:
    pitch = st.slider("Pitch (Hz)", -20, 20, 0, step=2)

if st.button("🎙️ Generate Speech"):
    if not text.strip():
        st.error("Text khaali hai, kuch likho pehle.")
    else:
        with st.spinner("Andrew bol raha hai..."):
            audio_bytes = synthesize(text, voice_id, rate, pitch)

        if not audio_bytes:
            st.error("Kuch issue aaya, dobara try karo.")
        else:
            st.success("Done! Neeche audio player aur download button hai 👇")
            st.audio(audio_bytes, format="audio/mp3")
            st.download_button(
                "⬇️ Download MP3",
                data=audio_bytes,
                file_name="edge_tts_andrew.mp3",
                mime="audio/mpeg",
            )
