"""
Loki Module -- Entertainment
Fun & games: jokes, fun facts, riddles, and trivia.
"""

import re
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from modules.base_module import BaseModule


class LokiModule(BaseModule):
    name = "loki"
    display_name = "Loki"
    icon = "\U0001f3ae"  # game controller
    description = "Entertainment -- jokes, fun facts, riddles, and trivia"
    version = "1.0"
    category = "lifestyle"
    enabled = True

    KEYWORDS = [
        r"\bjoke\b", r"\bfun\s+fact\b", r"\briddle\b", r"\bgame\b",
        r"\btrivia\b", r"\bmazak\b", r"\bchutkula\b", r"\bentertain\b",
        r"\bfunny\b", r"\bhasao\b", r"\bhasa\s+do\b", r"\bbored\b",
        r"\bkuch\s+maza\b", r"\bfun\b", r"\blaugh\b", r"\bhumor\b",
        r"\bpuzzle\b", r"\bbrain\s*teaser\b", r"\bmasti\b",
    ]

    JOKES_ENGLISH = [
        ("Why do programmers prefer dark mode?", "Because light attracts bugs!"),
        ("Why was the JavaScript developer sad?", "Because he didn't Node how to Express himself."),
        ("What's a computer's favorite snack?", "Microchips!"),
        ("Why do Java developers wear glasses?", "Because they don't C#."),
        ("What did the router say to the doctor?", "It hurts when IP."),
        ("Why did the developer go broke?", "Because he used up all his cache."),
        ("How many programmers does it take to change a light bulb?", "None. That's a hardware problem."),
        ("Why do programmers hate nature?", "It has too many bugs and no documentation."),
    ]

    JOKES_HINDI = [
        ("Teacher: Tum school late kyu aaye?", "Student: Sir, board pe likha tha 'School ke aage dheere chalo'... toh dheere dheere aaya!"),
        ("Pappu se teacher ne pucha: 'Bhains ka doodh kyu peete hai?'", "Pappu: Kyunki bhains chai nahi banati!"),
        ("Ek aadmi ne dusre se pucha: 'Bhai coding seekhni hai'", "Dusra: 'Pehle patience install karo, baaki sab baad mein'"),
        ("Doctor: Aap roz subah 5 baje uthte ho?", "Patient: Ji nahi. Doctor: Toh kal se utha karo. Patient: Kyu? Doctor: Toh usse pehle marna padega na!"),
        ("Wife: Mere birthday pe kya gift doge?", "Husband: Ankhe band karo... dekho andhera... yahi hai tumhare future ka gift!"),
        ("Santa: Yaar main kal se gym join kar raha hoon", "Banta: Kal se? Kal toh aaj bhi kal tha!"),
        ("Interviewer: Aapki sabse badi kamzori kya hai?", "Candidate: Honesty. Interviewer: Mujhe nahi lagta yeh kamzori hai. Candidate: Tumhare lagta kya hai mujhe farak padta hai!"),
        ("Ek programmer ki biwi ne kaha: 'Market se 1 packet doodh lao, agar ande mile toh 6 le aana'", "Programmer 6 packet doodh le aaya. Biwi: 6 kyu? Programmer: Ande mil gaye the!"),
    ]

    FUN_FACTS = [
        "Honey never spoils. Archaeologists found 3000-year-old honey in Egyptian tombs that was still edible!",
        "A group of flamingos is called a 'flamboyance'.",
        "The first computer bug was an actual bug -- a moth stuck in a Harvard Mark II computer in 1947.",
        "Octopuses have three hearts and blue blood.",
        "The inventor of the Pringles can is buried in one.",
        "A day on Venus is longer than a year on Venus.",
        "There are more possible chess games than atoms in the observable universe.",
        "Bananas are berries, but strawberries aren't.",
        "The first text message ever sent was 'Merry Christmas' in 1992.",
        "NASA's internet speed is 91 Gbps -- about 13,000 times faster than average!",
        "The heart of a blue whale is so big that a small child could swim through its arteries.",
        "Cleopatra lived closer in time to the Moon landing than to the construction of the Great Pyramid.",
    ]

    RIDDLES = [
        ("I have keys but no locks. I have space but no room. You can enter but can't go inside. What am I?", "A keyboard!"),
        ("What has a head and a tail but no body?", "A coin!"),
        ("I speak without a mouth and hear without ears. I have no body, but I come alive with wind. What am I?", "An echo!"),
        ("The more you take, the more you leave behind. What am I?", "Footsteps!"),
        ("I have cities, but no houses. I have mountains, but no trees. I have water, but no fish. What am I?", "A map!"),
        ("What can travel around the world while staying in a corner?", "A postage stamp!"),
        ("I am not alive, but I grow; I don't have lungs, but I need air. What am I?", "Fire!"),
        ("What has 13 hearts but no other organs?", "A deck of cards!"),
    ]

    TRIVIA = [
        ("What is the smallest country in the world?", "Vatican City"),
        ("How many bones does an adult human have?", "206"),
        ("What programming language was created by Guido van Rossum?", "Python"),
        ("What planet is known as the Red Planet?", "Mars"),
        ("In what year was the first iPhone released?", "2007"),
    ]

    def __init__(self):
        self.humor_style = "clean"
        self._used_jokes = set()
        self._used_facts = set()

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        text_lower = text.lower()
        for pattern in self.KEYWORDS:
            if re.search(pattern, text_lower):
                return 0.85
        if intent in ("joke", "entertainment", "fun", "riddle", "trivia"):
            return 0.9
        return 0.0

    def _detect_type(self, text: str) -> str:
        text_lower = text.lower()
        if re.search(r"\briddle\b|\bpuzzle\b|\bbrain\s*teaser\b|\bpaheliyan?\b", text_lower):
            return "riddle"
        if re.search(r"\bfact\b|\bfun\s+fact\b|\bdid\s+you\s+know\b|\bpata\s+hai\b", text_lower):
            return "fact"
        if re.search(r"\btrivia\b|\bquiz\b|\bquestion\b", text_lower):
            return "trivia"
        return "joke"

    def _pick_random(self, items: list, used_set: set) -> int:
        """Pick a random index, avoiding recently used ones."""
        available = [i for i in range(len(items)) if i not in used_set]
        if not available:
            used_set.clear()
            available = list(range(len(items)))
        idx = random.choice(available)
        used_set.add(idx)
        return idx

    def execute(self, text: str, context: dict) -> dict:
        content_type = self._detect_type(text)

        if content_type == "joke":
            return self._tell_joke(text)
        elif content_type == "fact":
            return self._tell_fact()
        elif content_type == "riddle":
            return self._tell_riddle()
        elif content_type == "trivia":
            return self._ask_trivia()

        return self._tell_joke(text)

    def _tell_joke(self, text: str) -> dict:
        text_lower = text.lower()
        # Pick Hindi or English based on style or language hints
        use_hindi = (
            self.humor_style == "hinglish"
            or re.search(r"\bhindi\b|\bhinglish\b|\bmazak\b|\bchutkula\b|\bhasao\b", text_lower)
        )

        if use_hindi:
            jokes = self.JOKES_HINDI
        else:
            jokes = self.JOKES_ENGLISH

        idx = self._pick_random(jokes, self._used_jokes)
        setup, punchline = jokes[idx]

        return {
            "response": f"\U0001f602 **Joke Time!**\n\n{setup}\n\n*{punchline}*",
            "data": {"type": "joke", "language": "hindi" if use_hindi else "english"},
            "action": "joke",
        }

    def _tell_fact(self) -> dict:
        idx = self._pick_random(self.FUN_FACTS, self._used_facts)
        fact = self.FUN_FACTS[idx]

        return {
            "response": f"\U0001f4a1 **Fun Fact #{idx + 1}:**\n\n{fact}",
            "data": {"type": "fact", "index": idx},
            "action": "fun_fact",
        }

    def _tell_riddle(self) -> dict:
        riddle, answer = random.choice(self.RIDDLES)
        return {
            "response": (
                f"\U0001f9e9 **Riddle:**\n\n{riddle}\n\n"
                f"||**Answer:** {answer}||"
            ),
            "data": {"type": "riddle", "question": riddle, "answer": answer},
            "action": "riddle",
        }

    def _ask_trivia(self) -> dict:
        question, answer = random.choice(self.TRIVIA)
        return {
            "response": (
                f"\U0001f9e0 **Trivia Question:**\n\n{question}\n\n"
                f"*Think about it... then ask me for the answer!*\n\n"
                f"||**Answer:** {answer}||"
            ),
            "data": {"type": "trivia", "question": question, "answer": answer},
            "action": "trivia",
        }

    def get_system_prompt_addition(self) -> str:
        return (
            "You have access to jokes, fun facts, riddles, and trivia. "
            "When the user is bored or asks for entertainment, use the Loki module."
        )

    def get_context_for_llm(self, text: str, context: dict) -> str:
        return f"[Loki] Entertainment module. Humor style: {self.humor_style}"

    def get_settings(self) -> dict:
        return {
            "enabled": self.enabled,
            "humor_style": self.humor_style,
        }

    def update_settings(self, settings: dict):
        if "enabled" in settings:
            self.enabled = settings["enabled"]
        if "humor_style" in settings:
            if settings["humor_style"] in ("clean", "nerdy", "hinglish"):
                self.humor_style = settings["humor_style"]

    def get_settings_schema(self) -> list:
        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled},
            {
                "key": "humor_style", "label": "Humor Style",
                "type": "select", "value": self.humor_style,
                "options": [
                    {"label": "Clean", "value": "clean"},
                    {"label": "Nerdy / Tech", "value": "nerdy"},
                    {"label": "Hinglish", "value": "hinglish"},
                ],
            },
        ]
