# MJ Assistant — JARVIS-Style AI Assistant

A local-first AI assistant with cyberpunk HUD interface, 22 agent modules, and full PC control. Runs entirely on your hardware via Ollama.

## Quick Start

### Prerequisites
- Python 3.11+
- Ollama installed and running (`ollama serve`)
- At least one model pulled (`ollama pull qwen2.5:7b`)

### Run
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```
Then open `frontend/index.html` in your browser.

Or double-click `start.bat`.

## Architecture

```
Frontend (index.html) ←→ Backend (FastAPI :8000) ←→ Ollama (local LLM)
                              ├── Zeus Brain (22 agent modules)
                              ├── Intelligence Layer (search, KB, memory, OCR)
                              ├── PC Control (15 modules)
                              ├── Voice Layer (TTS + STT)
                              └── Self-Healing System
```

## Features

- 3D particle orb with emotion-driven animations
- 22 AI agent modules (code, git, notifications, knowledge, creative, security, stats, etc.)
- Zeus smart routing with intent classification and auto-recovery
- RAG knowledge base with PDF/DOCX support and citations
- PC control (apps, files, screenshots, volume, clipboard, etc.)
- Web search, live data (weather, cricket), OCR
- Voice input/output (Whisper STT + Edge-TTS)
- Self-healing error system with alerts
- Image generation via Pollinations.ai

## Roadmap

See [ROADMAP.md](ROADMAP.md) for detailed progress (currently 63% complete).

## Dev Workflow
- **Office Laptop**: Code + git push
- **Personal PC** (RTX 3060, 32GB RAM): Pull, run backend with Ollama, test
