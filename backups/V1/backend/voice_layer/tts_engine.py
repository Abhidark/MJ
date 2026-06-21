import edge_tts
import uuid
from pathlib import Path
from voice_layer.voice_config import load_voice_settings, get_voice_style
from voice_layer.language_detector import detect_language

# Audio output directory
AUDIO_DIR = Path(__file__).parent.parent / "audio_cache"
AUDIO_DIR.mkdir(exist_ok=True)


def select_voice(text: str) -> str:
    """Pick the best voice based on detected language and settings."""
    settings = load_voice_settings()
    lang = detect_language(text)

    if lang in ("hindi", "hinglish"):
        return settings.get("hindi_voice", "hi-IN-SwaraNeural")
    else:
        return settings.get("english_voice", "en-IN-NeerjaNeural")


async def generate_speech(text: str, emotion: str = "neutral") -> str:
    """Generate speech audio from text. Returns filename."""

    voice = select_voice(text)
    style = get_voice_style(emotion)

    filename = f"mj_{uuid.uuid4().hex[:8]}.mp3"
    filepath = AUDIO_DIR / filename

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=style["rate"],
        pitch=style["pitch"],
        volume=style["volume"],
    )

    await communicate.save(str(filepath))
    return filename


async def test_voice(text: str, voice: str, rate: str, pitch: str, volume: str) -> str:
    """Generate test speech with specific settings. Returns filename."""

    filename = f"mj_test_{uuid.uuid4().hex[:8]}.mp3"
    filepath = AUDIO_DIR / filename

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        pitch=pitch,
        volume=volume,
    )

    await communicate.save(str(filepath))
    return filename


def cleanup_old_audio(keep_latest: int = 20):
    """Remove old audio files, keep only latest N."""
    files = sorted(AUDIO_DIR.glob("mj_*.mp3"), key=lambda f: f.stat().st_mtime)
    for f in files[:-keep_latest]:
        f.unlink(missing_ok=True)
