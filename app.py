import asyncio
import re

import edge_tts
import streamlit as st


# ---------- Page & global styling ----------

st.set_page_config(page_title="Text to Speech Studio", page_icon="🎙️")

st.markdown(
    """
    <style>
    body {
        background: radial-gradient(circle at top left, #eef2ff 0, #ffffff 45%, #f7f7fb 100%);
    }
    .main .block-container {
        padding-top: 2.5rem;
        padding-bottom: 2.5rem;
        max-width: 960px;
    }
    .tts-header {
        text-align: center;
        margin-bottom: 2.0rem;
    }
    .tts-title {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: 0.04em;
        margin-bottom: 0.35rem;
    }
    .tts-subtitle {
        font-size: 0.95rem;
        color: #6c757d;
    }
    .tts-card {
        padding: 1.6rem 1.9rem;
        border-radius: 1.25rem;
        border: 1px solid #e5e7eb;
        background: #ffffffcc;
        backdrop-filter: blur(12px);
        box-shadow: 0 22px 55px rgba(15, 23, 42, 0.10);
    }
    .tts-section-title {
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.13em;
        font-weight: 600;
        color: #9ca3af;
        margin-bottom: 0.6rem;
    }
    .tts-voice-help {
        font-size: 0.8rem;
        color: #9ca3af;
        margin-top: 0.25rem;
    }
    /* Script area */
    .stTextArea textarea {
        border-radius: 0.9rem !important;
    }
    /* Make selectboxes rounded, but don't mess with layout width */
    .stSelectbox > div[data-baseweb="select"] {
        border-radius: 999px !important;
    }
    /* Sliders & button */
    .stSlider > div[data-baseweb="slider"] {
        padding-top: 0.4rem;
    }
    .stButton>button {
        border-radius: 999px;
        padding: 0.55rem 1.6rem;
        background: linear-gradient(135deg, #4f46e5, #7c3aed);
        color: white;
        border: none;
        font-weight: 600;
        letter-spacing: 0.03em;
        box-shadow: 0 12px 30px rgba(79, 70, 229, 0.35);
    }
    .stButton>button:hover {
        filter: brightness(1.05);
        box-shadow: 0 14px 36px rgba(79, 70, 229, 0.45);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------- Helpers for voices ----------

LANGUAGE_NAMES = {
    "af": "Afrikaans",
    "ar": "Arabic",
    "bn": "Bengali",
    "de": "German",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "hi": "Hindi",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "nl": "Dutch",
    "pl": "Polish",
    "pt": "Portuguese",
    "ru": "Russian",
    "tr": "Turkish",
    "ur": "Urdu",
    "zh": "Chinese",
}

COUNTRY_NAMES = {
    "AU": "Australia",
    "BR": "Brazil",
    "CA": "Canada",
    "DE": "Germany",
    "ES": "Spain",
    "FR": "France",
    "GB": "United Kingdom",
    "IN": "India",
    "JP": "Japan",
    "KR": "Korea",
    "MX": "Mexico",
    "PK": "Pakistan",
    "PT": "Portugal",
    "TR": "Türkiye",
    "US": "United States",
}


def language_label_from_locale(locale: str) -> str:
    """Convert e.g. 'en-US' -> 'English (United States)'."""
    if not locale:
        return "Unknown"

    parts = locale.split("-")
    lang_code = parts[0]
    country_code = parts[1] if len(parts) > 1 else ""

    lang_name = LANGUAGE_NAMES.get(lang_code, lang_code)
    if country_code:
        country_name = COUNTRY_NAMES.get(country_code, country_code)
        return f"{lang_name} ({country_name})"
    return lang_name


def clean_voice_name(short_name: str) -> str:
    """'en-US-AndrewMultilingualNeural' -> 'Andrew'."""
    if not short_name:
        return "Voice"

    name_token = short_name.split("-")[-1]
    name_token = re.sub(r"Neural$", "", name_token)
    name_token = re.sub(r"Multilingual$", "", name_token)
    return name_token or short_name


def style_from_short_name(short_name: str) -> str:
    return "Multilingual" if "Multilingual" in short_name else "Natural"


@st.cache_data(show_spinner=False)
def load_voices():
    """Fetch and cache the full voice list."""
    voices = asyncio.run(edge_tts.list_voices())
    voices = sorted(voices, key=lambda v: v.get("ShortName", ""))
    return voices


async def tts_to_bytes_async(text: str, voice: str, rate: int = 0, pitch: int = 0) -> bytes:
    if not text.strip():
        return b""

    rate_str = f"{rate:+d}%"
    pitch_str = f"{pitch:+d}Hz"

    communicate = edge_tts.Communicate(text, voice, rate=rate_str, pitch=pitch_str)

    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]

    return audio_data


def tts_to_bytes(text: str, voice: str, rate: int, pitch: int) -> bytes:
    return asyncio.run(tts_to_bytes_async(text, voice, rate, pitch))


# ---------- Session state for persistent audio ----------

if "tts_audio" not in st.session_state:
    st.session_state["tts_audio"] = None
if "tts_filename" not in st.session_state:
    st.session_state["tts_filename"] = "output.mp3"


# ---------- Layout ----------

st.markdown(
    """
    <div class="tts-header">
        <div class="tts-title">Text to Speech Studio</div>
        <div class="tts-subtitle">
            Paste your script, choose a voice, and export a clean, natural read.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

voices_data = load_voices()
if not voices_data:
    st.error("No voices are available at the moment. Please try again later.")
    st.stop()

with st.container():
    st.markdown('<div class="tts-card">', unsafe_allow_html=True)

    left_col, right_col = st.columns([1.2, 0.8])

    # --- Left: script ---
    with left_col:
        st.markdown('<div class="tts-section-title">SCRIPT</div>', unsafe_allow_html=True)
        script = st.text_area(
            label="Script",
            value="Hello, this is a sample script. Replace this text with your own content.",
            height=260,
            placeholder="Paste your script here...",
            label_visibility="collapsed",  # hide Streamlit's built-in label -> no weird bar
        )

    # --- Right: voice & controls ---
    with right_col:
        st.markdown(
            '<div class="tts-section-title">VOICE SETTINGS</div>',
            unsafe_allow_html=True,
        )

        # Language filter
        label_to_locale = {}
        for v in voices_data:
            loc = v.get("Locale")
            if not loc:
                continue
            label = language_label_from_locale(loc)
            label_to_locale[label] = loc

        language_labels = sorted(label_to_locale.keys())
        default_lang_index = (
            language_labels.index("English (United States)") + 1
            if "English (United States)" in language_labels
            else 0
        )

        language_choice = st.selectbox(
            "Language",
            ["All languages"] + language_labels,
            index=default_lang_index,
        )

        genders = sorted({v.get("Gender", "") for v in voices_data if v.get("Gender")})
        gender_choice = st.selectbox("Gender", ["Any"] + genders, index=0)

        filtered = voices_data
        if language_choice != "All languages":
            selected_locale = label_to_locale[language_choice]
            filtered = [v for v in filtered if v.get("Locale") == selected_locale]

        if gender_choice != "Any":
            filtered = [v for v in filtered if v.get("Gender") == gender_choice]

        if not filtered:
            st.warning("No voices match the current filters.")
            st.markdown("</div>", unsafe_allow_html=True)
            st.stop()

        voice_labels = []
        shortname_by_label = {}
        for v in filtered:
            short = v.get("ShortName", "")
            locale = v.get("Locale", "")
            gender = v.get("Gender", "")

            base_name = clean_voice_name(short)
            style = style_from_short_name(short)
            lang_label = language_label_from_locale(locale)

            label = f"{base_name} ({style}) - {lang_label}"
            if gender:
                label += f" · {gender}"

            voice_labels.append(label)
            shortname_by_label[label] = short

        default_index = 0
        for i, label in enumerate(voice_labels):
            if "Andrew" in label:
                default_index = i
                break

        selected_voice_label = st.selectbox(
            "Voice", voice_labels, index=default_index, key="voice_select"
        )
        selected_short_name = shortname_by_label[selected_voice_label]

        st.markdown(
            '<div class="tts-voice-help">Fine-tune speed and pitch for subtle variations.</div>',
            unsafe_allow_html=True,
        )

        rate_col, pitch_col = st.columns(2)
        with rate_col:
            rate = st.slider("Speed", -40, 40, 0, step=5)
        with pitch_col:
            pitch = st.slider("Pitch", -20, 20, 0, step=2)

    st.markdown("</div>", unsafe_allow_html=True)  # close card


# ---------- Generate & persistent output ----------

generate = st.button("Generate audio", type="primary")

if generate:
    if not script.strip():
        st.error("Please enter some text first.")
    else:
        with st.spinner("Creating your audio..."):
            audio_bytes = tts_to_bytes(script, selected_short_name, rate, pitch)

        if not audio_bytes:
            st.error("Something went wrong while generating audio. Please try again.")
        else:
            st.session_state["tts_audio"] = audio_bytes
            st.session_state["tts_filename"] = (
                f"{clean_voice_name(selected_short_name)}.mp3"
            )

if st.session_state["tts_audio"]:
    st.audio(st.session_state["tts_audio"], format="audio/mp3")
    st.download_button(
        "Download MP3",
        data=st.session_state["tts_audio"],
        file_name=st.session_state["tts_filename"],
        mime="audio/mpeg",
        key="download_button_persistent",
    )
