"""
Conversation Modes for MJ Human Layer.
Defines response styles per intent, with dynamic mode transitions and formatting rules.
"""

MODE_STYLE = {
    "casual": {
        "tone": "friendly, natural, light",
        "max_length": "medium",
        "format": "conversational prose, no headers or bullet points unless asked",
        "temperature": 0.8,
        "system_hint": "Keep it brief and natural. Use Hinglish. Be warm.",
    },
    "command": {
        "tone": "short, confident, action-oriented",
        "max_length": "short",
        "format": "one-liner confirmation or brief status",
        "temperature": 0.3,
        "system_hint": "Execute and confirm. Don't explain unless asked. Be snappy like JARVIS.",
    },
    "coding": {
        "tone": "clear, practical, step-by-step",
        "max_length": "detailed",
        "format": "code blocks with explanations, use markdown",
        "temperature": 0.4,
        "system_hint": "Show code first, explain after. Use proper formatting. Be precise.",
    },
    "planning": {
        "tone": "organized, helpful, strategic",
        "max_length": "detailed",
        "format": "numbered steps, bullet points, clear structure",
        "temperature": 0.5,
        "system_hint": "Break it down into phases/steps. Be actionable, not vague.",
    },
    "emotional_support": {
        "tone": "warm, calm, supportive",
        "max_length": "medium",
        "format": "empathetic prose, no lists, be human",
        "temperature": 0.7,
        "system_hint": "Listen first. Validate feelings. Don't jump to solutions unless asked.",
    },
    "learning": {
        "tone": "simple, teacher-like, friendly",
        "max_length": "detailed",
        "format": "explanation with examples, analogies welcome",
        "temperature": 0.5,
        "system_hint": "Explain like teaching a friend. Use analogies. Build from basics.",
    },
    "creative": {
        "tone": "imaginative, free-flowing, expressive",
        "max_length": "flexible",
        "format": "depends on creative type (poem, story, etc.)",
        "temperature": 0.9,
        "system_hint": "Be creative and original. Match the requested format. Show flair.",
    },
    "data_query": {
        "tone": "informative, factual, concise",
        "max_length": "short",
        "format": "structured data with labels",
        "temperature": 0.3,
        "system_hint": "Present data clearly. Use proper formatting. Cite source.",
    },
    "file_ops": {
        "tone": "efficient, confirmatory",
        "max_length": "short",
        "format": "action confirmation with path/details",
        "temperature": 0.2,
        "system_hint": "Confirm what was done. Show relevant details. Be precise.",
    },
}

# Mode transition rules — when to suggest switching
MODE_TRANSITIONS = {
    ("casual", "coding"): "Looks like we're getting into code territory!",
    ("casual", "planning"): "Let me help you plan this out properly.",
    ("coding", "emotional_support"): "Take a breather — debugging can be frustrating.",
    ("coding", "casual"): "Nice work! What's next?",
    ("emotional_support", "casual"): "Feeling better? I'm here whenever.",
}


def get_mode(intent: str) -> dict:
    """Get mode style for an intent, with fallback to casual."""
    return MODE_STYLE.get(intent, MODE_STYLE["casual"])


def get_transition_message(old_intent: str, new_intent: str) -> str | None:
    """Get optional transition message when mode changes."""
    return MODE_TRANSITIONS.get((old_intent, new_intent))


def get_temperature(intent: str) -> float:
    """Get recommended temperature for an intent."""
    return MODE_STYLE.get(intent, MODE_STYLE["casual"]).get("temperature", 0.7)
