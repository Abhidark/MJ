"""
STT Engine — Server-side Speech-to-Text using Whisper (via faster-whisper or openai-whisper).
Falls back to Google Speech Recognition if Whisper is unavailable.
"""

import os
import uuid
import tempfile
import logging
from pathlib import Path

logger = logging.getLogger("mj.stt")

# Audio upload directory
UPLOAD_DIR = Path(__file__).parent.parent / "audio" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Try to import whisper backends
_whisper_backend = None

try:
    from faster_whisper import WhisperModel
    _whisper_backend = "faster-whisper"
    _model = None

    def _get_model():
        global _model
        if _model is None:
            model_size = os.environ.get("WHISPER_MODEL", "base")
            device = os.environ.get("WHISPER_DEVICE", "cpu")
            compute_type = "int8" if device == "cpu" else "float16"
            logger.info(f"Loading faster-whisper model: {model_size} on {device}")
            _model = WhisperModel(model_size, device=device, compute_type=compute_type)
        return _model

    def transcribe_audio(audio_path: str, language: str = None) -> dict:
        """Transcribe audio file using faster-whisper."""
        model = _get_model()
        segments, info = model.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        text_parts = []
        word_timestamps = []
        for segment in segments:
            text_parts.append(segment.text.strip())
            if segment.words:
                for w in segment.words:
                    word_timestamps.append({
                        "word": w.word,
                        "start": round(w.start, 2),
                        "end": round(w.end, 2)
                    })

        full_text = " ".join(text_parts)
        return {
            "text": full_text,
            "language": info.language,
            "language_probability": round(info.language_probability, 2),
            "duration": round(info.duration, 2),
            "words": word_timestamps[:100],  # Cap word timestamps
            "backend": "faster-whisper"
        }

except ImportError:
    pass

if _whisper_backend is None:
    try:
        import whisper
        _whisper_backend = "openai-whisper"
        _model = None

        def _get_model():
            global _model
            if _model is None:
                model_size = os.environ.get("WHISPER_MODEL", "base")
                logger.info(f"Loading openai-whisper model: {model_size}")
                _model = whisper.load_model(model_size)
            return _model

        def transcribe_audio(audio_path: str, language: str = None) -> dict:
            """Transcribe audio file using openai-whisper."""
            model = _get_model()
            opts = {"fp16": False}
            if language:
                opts["language"] = language
            result = model.transcribe(audio_path, **opts)
            return {
                "text": result["text"].strip(),
                "language": result.get("language", "unknown"),
                "language_probability": 0.0,
                "duration": 0.0,
                "words": [],
                "backend": "openai-whisper"
            }

    except ImportError:
        pass

if _whisper_backend is None:
    try:
        import speech_recognition as sr
        _whisper_backend = "speech-recognition"

        def transcribe_audio(audio_path: str, language: str = None) -> dict:
            """Fallback: use Google Speech Recognition."""
            recognizer = sr.Recognizer()
            with sr.AudioFile(audio_path) as source:
                audio = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio, language=language or "en-US")
                return {
                    "text": text,
                    "language": language or "en-US",
                    "language_probability": 0.0,
                    "duration": 0.0,
                    "words": [],
                    "backend": "google-speech"
                }
            except sr.UnknownValueError:
                return {"text": "", "language": "", "duration": 0, "words": [], "backend": "google-speech", "error": "Could not understand audio"}
            except sr.RequestError as e:
                return {"text": "", "language": "", "duration": 0, "words": [], "backend": "google-speech", "error": f"Google API error: {e}"}

    except ImportError:
        pass

# Final fallback
if _whisper_backend is None:
    _whisper_backend = "none"

    def transcribe_audio(audio_path: str, language: str = None) -> dict:
        return {
            "text": "",
            "language": "",
            "duration": 0,
            "words": [],
            "backend": "none",
            "error": "No STT backend available. Install faster-whisper, openai-whisper, or SpeechRecognition."
        }


async def save_and_transcribe(audio_bytes: bytes, filename: str = None, language: str = None) -> dict:
    """Save uploaded audio and transcribe it."""
    if not filename:
        filename = f"stt_{uuid.uuid4().hex[:8]}.wav"

    filepath = UPLOAD_DIR / filename
    filepath.write_bytes(audio_bytes)

    try:
        result = transcribe_audio(str(filepath), language=language)
        result["filename"] = filename
        return result
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return {
            "text": "",
            "error": str(e),
            "backend": _whisper_backend,
            "filename": filename
        }
    finally:
        # Clean up after 5 min (keep for debugging)
        pass


def get_stt_status() -> dict:
    """Return STT engine status."""
    return {
        "backend": _whisper_backend,
        "available": _whisper_backend != "none",
        "model": os.environ.get("WHISPER_MODEL", "base"),
        "device": os.environ.get("WHISPER_DEVICE", "cpu")
    }
