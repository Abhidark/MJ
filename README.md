# MJ Assistant — Phase 1 (Chat Only)

## Structure
```
MJ-Assistant/
├── frontend/
│   └── index.html      ← Chat UI
├── backend/
│   ├── main.py          ← FastAPI server
│   └── requirements.txt
├── start.bat            ← One-click launcher
└── README.md
```

## How to Run

### Prerequisites
1. Python 3.10+
2. Ollama installed & running → `ollama run llama3.2`

### Start
Double-click `start.bat` — OR manually:

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```
Then open `frontend/index.html` in browser.

## Flow
```
User → Frontend (index.html) → Backend (FastAPI :8000) → Ollama (llama3.2) → Reply
```
