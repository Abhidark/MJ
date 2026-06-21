"""
MJ AI Image Generation
Uses Stable Diffusion via Ollama (if available), or free Pollinations.ai API.
No API key needed for Pollinations.
"""

import httpx
import re
import base64
from pathlib import Path
from datetime import datetime
from typing import Optional
from urllib.parse import quote

IMAGES_DIR = Path(__file__).parent.parent / "generated_images"
IMAGES_DIR.mkdir(exist_ok=True)

# Pollinations.ai — free, no API key, no signup
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/"


async def generate_image(prompt: str, style: str = "") -> dict:
    """
    Generate an image from text prompt.
    Uses Pollinations.ai (free, no key needed).
    """
    # Enhance prompt with style
    full_prompt = prompt.strip()
    if style:
        full_prompt += f", {style}"

    # Add quality enhancers
    if not any(w in full_prompt.lower() for w in ["4k", "hd", "realistic", "detailed"]):
        full_prompt += ", high quality, detailed"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"mj_img_{timestamp}.png"
    filepath = IMAGES_DIR / filename

    try:
        # Pollinations.ai — just GET request with prompt in URL
        encoded = quote(full_prompt)
        url = f"{POLLINATIONS_URL}{encoded}?width=768&height=768&nologo=true"

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(url)

            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image"):
                # Save image
                filepath.write_bytes(resp.content)

                return {
                    "success": True,
                    "message": f"Image generate ho gayi! Prompt: {prompt[:50]}",
                    "filename": filename,
                    "path": str(filepath),
                    "url": f"/static/generated/{filename}",
                    "size_kb": len(resp.content) // 1024,
                }
            else:
                return {
                    "success": False,
                    "message": f"Image generation failed (status {resp.status_code}). Try again.",
                }

    except httpx.TimeoutException:
        return {
            "success": False,
            "message": "Image generation timeout — server busy. Thodi der baad try karo.",
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Image generation error: {str(e)}",
        }


def parse_image_command(text: str) -> Optional[dict]:
    """Parse image generation commands."""
    lower = text.lower().strip()

    # Generate image patterns
    patterns = [
        r"(?:generate|create|bana|banao|draw|make)\s+(?:a\s+|ek\s+)?(?:image|photo|picture|tasveer|pic|img)\s+(?:of\s+|ki\s+)?(.+)",
        r"(?:image|photo|picture|tasveer|pic)\s+(?:bana|banao|generate|create|draw)\s+(.+)",
        r"(?:ek\s+)?(.+)\s+(?:ki|ka|ke)\s+(?:image|photo|picture|tasveer)\s+(?:bana|banao|generate)",
    ]

    for pat in patterns:
        m = re.search(pat, lower)
        if m:
            prompt = m.group(1).strip()
            # Clean up
            for filler in ["please", "karo", "do", "na", "de", "dedo"]:
                prompt = prompt.replace(filler, "").strip()
            if prompt and len(prompt) > 2:
                # Extract style if mentioned
                style = ""
                style_keywords = {
                    "realistic": "photorealistic, 8k",
                    "cartoon": "cartoon style, colorful",
                    "anime": "anime style, detailed",
                    "painting": "oil painting style",
                    "sketch": "pencil sketch style",
                    "watercolor": "watercolor painting",
                    "3d": "3D render, detailed",
                    "pixel": "pixel art style",
                    "cyberpunk": "cyberpunk style, neon",
                    "fantasy": "fantasy art, magical",
                }
                for key, val in style_keywords.items():
                    if key in prompt.lower():
                        style = val
                        break

                return {"action": "generate", "prompt": prompt, "style": style}

    # List generated images
    if any(w in lower for w in ["show images", "generated images", "meri images", "image list"]):
        return {"action": "list"}

    return None


def list_generated_images(count: int = 10) -> dict:
    """List recently generated images."""
    images = sorted(IMAGES_DIR.glob("*.png"), key=lambda x: x.stat().st_mtime, reverse=True)

    if not images:
        return {"success": True, "message": "Koi generated image nahi hai abhi."}

    lines = [f"Last {min(len(images), count)} generated images:"]
    for img in images[:count]:
        size = img.stat().st_size // 1024
        lines.append(f"  • {img.name} ({size} KB)")

    return {"success": True, "message": "\n".join(lines)}


async def handle_image_command(cmd: dict) -> dict:
    """Handle image generation commands."""
    if cmd["action"] == "generate":
        return await generate_image(cmd["prompt"], cmd.get("style", ""))
    elif cmd["action"] == "list":
        return list_generated_images()
    return {"success": False, "message": "Unknown image command."}
