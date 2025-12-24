# app.py
import asyncio

import edge_tts
import streamlit as st


# ---------- Edge-TTS helpers ----------

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
    # edge-tts async streaming API:
    # async for chunk in communicate.stream(): ... (audio chunks)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]

    return audio_data


def synthesize(text: str, voice: str, rate: int, pitch: int) -> bytes:
    """Sync wrapper for Streamlit (because Streamlit callbacks sync hote hain)."""
    return asyncio.run(tts_to_bytes(text, voice, rate, pitch))


@st.cache_data(show_spinner=True)
def load_voices():
    """
    Saari available Edge TTS voices fetch karo.
    edge_tts.list_voices() async hota hai, isliye yahan asyncio.run use kiya.
    Result Streamlit cache karega taa ke har reload pe call na ho.
    """
    voices = asyncio.run(edge_tts.list_voices())
    # Thoda sort kar dete hain ShortName se
    voices = sorted(voices, key=lambda v: v.get("ShortName", ""))
    return voices


# ---------- Streamlit UI ----------

st.set_page_config(page_title="Edge-TTS Full Voices Demo", page_icon="🔊")

st.title("🔊 Edge-TTS Full Voices (Streamlit App)")

st.write(
    "Yeh app Microsoft Edge TTS ki saari available voices list karke "
    "un se speech generate karta hai.\n\n"
    "⚠️ Yeh demo / low-volume / learning use ke liye best hai. "
    "Heavy production / commercial use se pehle Microsoft ke terms zaroor padh lo."
)

# Load all voices once (cached)
voices_data = load_voices()

if not voices_data:
    st.error("Koi voice list nahi mili, baad mein dubara try karo.")
    st.stop()

# --- Locale (language) filter ---

locales = sorted({v.get("Locale", "") for v in voices_data if v.get("Locale")})
locale_options = ["All"] + locales

selected_locale = st.selectbox("Language / Locale filter:", locale_options, index=0)

if selected_locale == "All":
    filtered_voices = voices_data
else:
    filtered_voices = [v for v in voices_data if v.get("Locale") == selected_locale]

if not filtered_voices:
    st.warning("Is locale ke liye koi voices nahi milin.")
    st.stop()

# Map label -> ShortName for dropdown
voice_map = {
    f"{v.get('ShortName', '')} - {v.get('Locale', '?')} ({v.get('Gender', '?')})": v.get(
        "ShortName", ""
    )
    for v in filtered_voices
}

voice_labels = list(voice_map.keys())

# Default: try to select Andrew if present, warna first voice
default_index = 0
for i, label in enumerate(voice_labels):
    short = voice_map[label]
    if short in ("en-US-AndrewNeural", "en-US-AndrewMultilingualNeural"):
        default_index = i
        break

selected_label = st.selectbox(
    "Voice choose karo:",
    voice_labels,
    index=default_index,
)
voice_id = voice_map[selected_label]

# --- Text + controls ---

text = st.text_area(
    "Text likho (yahan paste bhi kar sakte ho):",
    "Hello, this is Edge TTS speaking from a Streamlit app!",
    height=200,
    # NOTE: max_chars yahan jaan-boojh kar nahi lagaya,
    # taa ke paste properly kaam kare.
)

col1, col2 = st.columns(2)
with col1:
    rate = st.slider("Rate (speed %)", -50, 50, 0, step=5)
with col2:
    pitch = st.slider("Pitch (Hz)", -20, 20, 0, step=2)

if st.button("🎙️ Generate Speech"):
    if not text.strip():
        st.error("Text khaali hai, kuch likho pehle.")
    else:
        with st.spinner("Voice generate ho rahi hai..."):
            audio_bytes = synthesize(text, voice_id, rate, pitch)

        if not audio_bytes:
            st.error("Kuch issue aaya, dobara try karo.")
        else:
            st.success("Done! Neeche audio player aur download button hai 👇")
            st.audio(audio_bytes, format="audio/mp3")
            st.download_button(
                "⬇️ Download MP3",
                data=audio_bytes,
                file_name=f"{voice_id}.mp3",
                mime="audio/mpeg",
            )

# Optional info panel
with st.expander("ℹ️ Extra info"):
    st.write(f"Total voices loaded: **{len(voices_data)}**")
    st.write(
        "Yeh list `edge_tts.list_voices()` se aati hai, jo Microsoft Edge ke "
        "online TTS endpoint se voices fetch karta hai."
    )
