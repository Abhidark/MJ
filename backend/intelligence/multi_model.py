"""
MJ Intelligence: Multi-Model Reasoning
- Chain multiple Ollama models for better answers
- Think → Verify → Summarize pipeline
- Model specialization (code vs creative vs reasoning)
- Confidence scoring and answer selection
"""

import httpx
import json
import re
from typing import Optional
from datetime import datetime


OLLAMA_URL = "http://localhost:11434"


async def get_available_models() -> list:
    """Get list of installed Ollama models."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{OLLAMA_URL}/api/tags")
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                return [m["name"] for m in models]
    except Exception:
        pass
    return []


async def single_query(model: str, prompt: str, system: str = "", timeout: int = 30) -> Optional[str]:
    """Send a single non-streaming query to Ollama."""
    try:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={"model": model, "messages": messages, "stream": False},
            )
            if resp.status_code == 200:
                return resp.json().get("message", {}).get("content", "")
    except Exception:
        pass
    return None


async def chain_of_thought(question: str, primary_model: str, context: str = "") -> dict:
    """
    Multi-step reasoning pipeline:
    1. THINK — primary model generates detailed reasoning
    2. VERIFY — check for errors/inconsistencies
    3. SYNTHESIZE — create final polished answer

    All steps use the same model but different system prompts.
    """
    models = await get_available_models()
    if not models:
        return {"answer": None, "method": "no_models"}

    # Use primary model for all steps (works with single model too)
    model = primary_model if primary_model in models else models[0]

    # Step 1: THINK — Deep reasoning
    think_system = """You are a deep reasoning engine. Think step by step.
Break down the question, consider multiple angles, and show your reasoning.
Be thorough but focused. If you're not sure, say so."""

    think_prompt = question
    if context:
        think_prompt = f"Context:\n{context}\n\nQuestion: {question}"

    thought = await single_query(model, think_prompt, think_system, timeout=45)

    if not thought:
        return {"answer": None, "method": "think_failed"}

    # Step 2: VERIFY — Check the reasoning
    verify_system = """You are a fact-checker and logic verifier.
Review the reasoning below and identify any:
- Logical errors or contradictions
- Unsupported claims
- Missing important considerations
- Confidence level (high/medium/low)
Be brief and direct."""

    verify_prompt = f"Original question: {question}\n\nReasoning to verify:\n{thought}"

    verification = await single_query(model, verify_prompt, verify_system, timeout=30)

    # Step 3: SYNTHESIZE — Final answer
    synth_system = """You are a concise answer synthesizer.
Given the original question, detailed reasoning, and verification feedback,
produce the best possible final answer. Be clear, accurate, and helpful.
If the verification found issues, address them."""

    synth_prompt = f"""Question: {question}

Detailed Reasoning:
{thought}

Verification Notes:
{verification or 'No verification available'}

Now give the best final answer:"""

    final_answer = await single_query(model, synth_prompt, synth_system, timeout=30)

    return {
        "answer": final_answer,
        "thought": thought,
        "verification": verification,
        "model_used": model,
        "method": "chain_of_thought",
        "steps_completed": 3
    }


async def multi_perspective(question: str, primary_model: str, context: str = "") -> dict:
    """
    Get multiple perspectives on a question and synthesize.
    Uses different system prompts to get diverse viewpoints.
    """
    models = await get_available_models()
    model = primary_model if primary_model in models else (models[0] if models else None)
    if not model:
        return {"answer": None, "method": "no_models"}

    perspectives = [
        ("Technical", "You are a precise technical expert. Focus on facts, data, and accuracy."),
        ("Creative", "You are a creative thinker. Consider unusual angles and analogies."),
        ("Practical", "You are a practical advisor. Focus on actionable, real-world advice."),
    ]

    prompt = question
    if context:
        prompt = f"Context: {context}\n\nQuestion: {question}"

    answers = []
    for name, system in perspectives:
        resp = await single_query(model, prompt, system, timeout=25)
        if resp:
            answers.append({"perspective": name, "answer": resp})

    if not answers:
        return {"answer": None, "method": "all_perspectives_failed"}

    # Synthesize
    synth_prompt = f"Question: {question}\n\n"
    for a in answers:
        synth_prompt += f"[{a['perspective']} view]: {a['answer'][:500]}\n\n"
    synth_prompt += "Synthesize these perspectives into one comprehensive, balanced answer:"

    final = await single_query(
        model, synth_prompt,
        "Combine multiple expert perspectives into one clear, comprehensive answer.",
        timeout=30
    )

    return {
        "answer": final,
        "perspectives": answers,
        "model_used": model,
        "method": "multi_perspective",
        "num_perspectives": len(answers)
    }


def needs_deep_reasoning(text: str) -> Optional[str]:
    """
    Detect if a question needs multi-model reasoning.
    Returns reasoning type: 'chain', 'perspective', or None.
    """
    lower = text.lower().strip()

    # Chain of thought triggers — complex analytical questions
    chain_patterns = [
        r"(?:explain|samjhao|describe)\s+(?:in detail|deeply|thoroughly|step by step)",
        r"(?:analyze|analyse|evaluate|assess|compare)",
        r"(?:why does|why is|why are|kyun|kaise)\s+.{20,}",
        r"(?:debug|fix|solve)\s+(?:this|my|the)\s+(?:code|error|problem|issue)",
        r"(?:difference between|pros and cons|advantages|disadvantages)",
        r"(?:how does|how do|how is)\s+.{15,}\s+(?:work|function|operate)",
        r"(?:think deeply|soch ke bata|detail me bata|reasoning)",
    ]

    for pat in chain_patterns:
        if re.search(pat, lower):
            return "chain"

    # Multi-perspective triggers
    perspective_patterns = [
        r"(?:opinion|views?|perspectives?|suggestions?|advice|sujhao|salah)",
        r"(?:should i|kya mujhe|which is better|konsa acha|recommend)",
        r"(?:what do you think|tumhe kya lagta|sochte ho)",
    ]

    for pat in perspective_patterns:
        if re.search(pat, lower):
            return "perspective"

    return None


async def smart_reason(question: str, model: str, context: str = "") -> dict:
    """
    Automatically pick the best reasoning strategy.
    """
    reasoning_type = needs_deep_reasoning(question)

    if reasoning_type == "chain":
        return await chain_of_thought(question, model, context)
    elif reasoning_type == "perspective":
        return await multi_perspective(question, model, context)
    else:
        # Simple single-model query for normal questions
        answer = await single_query(model, question, "", timeout=30)
        return {
            "answer": answer,
            "method": "direct",
            "model_used": model
        }
