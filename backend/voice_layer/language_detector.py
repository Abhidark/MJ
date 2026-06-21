import re


def detect_language(text: str) -> str:
    """Detect if text is Hindi, English, or Hinglish."""

    # Check for Devanagari script
    devanagari = len(re.findall(r'[ऀ-ॿ]', text))

    # Check for Latin script
    latin = len(re.findall(r'[a-zA-Z]', text))

    if devanagari > 0 and latin == 0:
        return "hindi"

    if devanagari == 0 and latin > 0:
        # Check for Hinglish (Hindi words in Latin script)
        hinglish_words = [
            "hai", "hoon", "haan", "nahi", "kya", "karo", "karte",
            "mein", "aur", "toh", "yeh", "woh", "abhi", "chalo",
            "rahi", "raha", "tumhare", "mere", "tera", "mat",
            "samajh", "bolo", "dekho", "suno", "achha", "theek",
            "kaisa", "kaisi", "kaise", "bahut", "thoda", "zyada",
            "pehle", "baad", "saath", "liye", "wala", "wali",
            "gayi", "gaya", "hogi", "hoga", "kar", "de", "le",
            "bhai", "yaar", "dost", "kaam", "din", "raat"
        ]
        words = text.lower().split()
        hindi_count = sum(1 for w in words if w in hinglish_words)

        if hindi_count >= 2 or hindi_count / max(len(words), 1) > 0.2:
            return "hinglish"

        return "english"

    if devanagari > 0 and latin > 0:
        return "hinglish"

    return "english"
