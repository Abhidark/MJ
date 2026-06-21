# MJ Voice Configuration
# Using Microsoft Edge TTS Neural Voices (Free, No API Key)

from pathlib import Path
import json

SETTINGS_FILE = Path(__file__).parent.parent / "voice_settings.json"

# All available voices
AVAILABLE_VOICES = {
    "hi-IN-SwaraNeural": "Swara (Hindi Female - Warm, Natural)",
    "hi-IN-MadhurNeural": "Madhur (Hindi Male)",
    "en-IN-NeerjaNeural": "Neerja (Indian English Female - Soft)",
    "en-IN-PrabhatNeural": "Prabhat (Indian English Male)",
    "en-US-JennyNeural": "Jenny (US English Female - Clear)",
    "en-US-AriaNeural": "Aria (US English Female - Friendly)",
    "en-US-SaraNeural": "Sara (US English Female - Calm)",
    "en-GB-SoniaNeural": "Sonia (British English Female)",
    "en-US-GuyNeural": "Guy (US English Male)",
}

# Default settings
DEFAULT_SETTINGS = {
    "hindi_voice": "hi-IN-SwaraNeural",
    "english_voice": "en-IN-NeerjaNeural",
    "rate": "-5%",
    "pitch": "+0Hz",
    "volume": "+0%",
    "auto_speak": True,
    "emotion_voice": True,
}

# Emotion-based voice adjustments (applied ON TOP of base settings)
EMOTION_STYLES = {
    "neutral": {"rate_adj": 0, "pitch_adj": 0, "volume_adj": 0},
    "happy": {"rate_adj": 5, "pitch_adj": 3, "volume_adj": 5},
    "sad": {"rate_adj": -15, "pitch_adj": -3, "volume_adj": -10},
    "angry": {"rate_adj": 0, "pitch_adj": 2, "volume_adj": 10},
    "confused": {"rate_adj": -10, "pitch_adj": 1, "volume_adj": 0},
    "stressed": {"rate_adj": -20, "pitch_adj": -2, "volume_adj": -5},
    "excited": {"rate_adj": 10, "pitch_adj": 5, "volume_adj": 10},
}


def load_voice_settings() -> dict:
    if SETTINGS_FILE.exists():
        saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        # Merge with defaults for any missing keys
        merged = {**DEFAULT_SETTINGS, **saved}
        return merged
    return DEFAULT_SETTINGS.copy()


def save_voice_settings(settings: dict):
    SETTINGS_FILE.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def get_voice_style(emotion: str = "neutral") -> dict:
    """Get final rate/pitch/volume combining base settings + emotion adjustment."""
    settings = load_voice_settings()
    emotion_adj = EMOTION_STYLES.get(emotion, EMOTION_STYLES["neutral"])

    # Parse base rate (e.g., "-5%" -> -5)
    base_rate = int(settings["rate"].replace("%", "").replace("+", ""))
    base_pitch = int(settings["pitch"].replace("Hz", "").replace("+", ""))
    base_vol = int(settings["volume"].replace("%", "").replace("+", ""))

    if settings.get("emotion_voice", True):
        final_rate = base_rate + emotion_adj["rate_adj"]
        final_pitch = base_pitch + emotion_adj["pitch_adj"]
        final_vol = base_vol + emotion_adj["volume_adj"]
    else:
        final_rate = base_rate
        final_pitch = base_pitch
        final_vol = base_vol

    # Clamp values
    final_rate = max(-50, min(50, final_rate))
    final_pitch = max(-50, min(50, final_pitch))
    final_vol = max(-50, min(50, final_vol))

    return {
        "rate": f"{'+' if final_rate >= 0 else ''}{final_rate}%",
        "pitch": f"{'+' if final_pitch >= 0 else ''}{final_pitch}Hz",
        "volume": f"{'+' if final_vol >= 0 else ''}{final_vol}%",
    }
