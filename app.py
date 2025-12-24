import asyncio
import re

import edge_tts
import streamlit as st


# ---------- Styling ----------

st.set_page_config(page_title="Text to Speech Studio", page_icon="🎙️")

st.markdown(
    """
    <style>
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
        font-size: 2.1rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        margin-bottom: 0.35rem;
    }
    .tts-subtitle {
        font-size: 0.95rem;
        color: #6c757d;
    }
    .tts-card {
        padding: 1.5rem 1.75rem;
        border-radius: 1.2rem;
        border: 1px solid #e5e7eb;
        background: #ffffff;
        box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
    }
    .tts-section-title {
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.13em;
        font-weight: 600;
        color: #9ca3af;
        margin-bottom: 0.6rem;
    }
    .tts-label {
        font-size: 0.9rem;
        font-weight: 600;
        margin-bottom: 0.2rem;
    }
    .tts-voice-help {
        font-size: 0.8rem;
        color: #9ca3af;
        margin-top: 0.25rem;
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
    """
    Turn e.g. 'en-US' into 'English (United States)'.
    Fallback to the raw locale if we don't know the mapping.
    """
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
    """
    'en-US-AndrewMultilingualNeural' -> 'Andrew', also strips 'Neural', 'Multilingual'.
    """
    if not short_name:
        return "Voice"

    # last token after locale, e.g. AndrewMultilingualNeural
    name_token = short_name.split("-")[-1]
    # remove suffixes
    name_token = re.sub(r"Neural$", "", name_token)
    name_token = re.sub(r"Multilingual$", "", name_token)
    return name_token or short_name


def style_from_short_name(short_name: str) -> str:
    if "Multilingual" in short_name:
        return "Multilingual"
    return "Natural"


@st.cache_data(show_spinner=False)
def load_voices():
    """
    Fetch and cache the full voice list from the TTS backend.
    """
    voices = asyncio.run(edge_tts.list_voices())
    voices = sorted(voices, key=lambda v: v.get("ShortName", ""))
    return voices


async def tts_to_bytes_async(
    text: str, voice: str, rate: int = 0, pitch: int = 0
) -> bytes:
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


# ---------- Layout ----------

st.markdown(
    """
    <div class="tts-header">
        <div class="tts-title">Text to Speech Studio</div>
        <div class="tts-subtitle">
            Paste your script, pick a voice, and export a clean, natural-sounding read.
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

    left_col, right_col = st.columns([1.15, 0.85])

    # --- Left: script ---

    with left_col:
        st.markdown('<div class="tts-section-title">Script</div>', unsafe_allow_html=True)
        script = st.text_area(
            "",
            "Hello, this is a sample script. Replace this text with your own content.",
            height=250,
            placeholder="Paste your script here...",
        )

    # --- Right: voice & controls ---

    with right_col:
        st.markdown(
            '<div class="tts-section-title">Voice Settings</div>',
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
        language_choice = st.selectbox(
            "Language",
            ["All languages"] + language_labels,
            index=language_labels.index("English (United States)")
            + 1
            if "English (United States)" in language_labels
            else 0,
        )

        # Gender filter
        genders = sorted({v.get("Gender", "") for v in voices_data if v.get("Gender")})
        gender_choice = st.selectbox("Gender", ["Any"] + genders, index=0)

        # Filter voices according to selection
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

        # Build professional display labels
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

        # Try to default to Andrew if available
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
            '<div class="tts-voice-help">Tip: adjust speed and pitch for subtle variations.</div>',
            unsafe_allow_html=True,
        )

        # Rate / pitch sliders
        rate_col, pitch_col = st.columns(2)
        with rate_col:
            rate = st.slider("Speed", -40, 40, 0, step=5)
        with pitch_col:
            pitch = st.slider("Pitch", -20, 20, 0, step=2)

    st.markdown("</div>", unsafe_allow_html=True)  # close card

# ---------- Generate button & output ----------

center = st.container()
with center:
    generate = st.button("Generate Audio", type="primary")

    if generate:
        if not script.strip():
            st.error("Please enter some text first.")
        else:
            with st.spinner("Creating your audio..."):
                audio_bytes = tts_to_bytes(script, selected_short_name, rate, pitch)

            if not audio_bytes:
                st.error("Something went wrong while generating audio. Please try again.")
            else:
                st.audio(audio_bytes, format="audio/mp3")
                st.download_button(
                    "Download MP3",
                    data=audio_bytes,
                    file_name=f"{clean_voice_name(selected_short_name)}.mp3",
                    mime="audio/mpeg",
                )
