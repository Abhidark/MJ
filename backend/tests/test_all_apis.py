"""
MJ Assistant — Full API Test Suite
Tests all completed versions: V1,V3,V4,V5,V6,V7,V8,V11,V12,V15,V16,V17,V18

Usage (from backend/ folder on your PC):
  python tests/test_all_apis.py

Requirements:
  pip install requests

Make sure MJ backend is running: python main.py
Default: http://localhost:8000
"""

import requests
import json
import time
import sys

BASE = "http://localhost:8000"
TOKEN = None
PASS = 0
FAIL = 0
SKIP = 0
RESULTS = []


def log(status, test_name, detail=""):
    global PASS, FAIL, SKIP
    icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⚠️"}.get(status, "?")
    if status == "PASS":
        PASS += 1
    elif status == "FAIL":
        FAIL += 1
    else:
        SKIP += 1
    msg = f"  {icon} {test_name}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    RESULTS.append({"status": status, "test": test_name, "detail": detail})


def get(path, **kwargs):
    headers = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
    try:
        r = requests.get(f"{BASE}{path}", headers=headers, timeout=10, **kwargs)
        return r
    except Exception as e:
        return None


def post(path, data=None, **kwargs):
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"} if TOKEN else {"Content-Type": "application/json"}
    try:
        r = requests.post(f"{BASE}{path}", headers=headers, json=data, timeout=15, **kwargs)
        return r
    except Exception as e:
        return None


def delete(path):
    headers = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
    try:
        return requests.delete(f"{BASE}{path}", headers=headers, timeout=10)
    except Exception:
        return None


def ok(r):
    """Check if response is successful."""
    return r is not None and r.status_code in (200, 201)


# ============================================================
# V1 — JARVIS Core (Auth, Chat, Health)
# ============================================================
def test_v1():
    global TOKEN
    print("\n🔹 V1 — JARVIS Core")

    # Auth status
    r = get("/auth/status")
    if ok(r):
        log("PASS", "GET /auth/status", f"auth_enabled={r.json().get('auth_enabled')}")
    else:
        log("FAIL", "GET /auth/status")

    # Login
    r = post("/auth/login", {"password": "jarvis"})
    if ok(r) and r.json().get("success"):
        TOKEN = r.json().get("token", "")
        log("PASS", "POST /auth/login", "token received")
    else:
        log("SKIP", "POST /auth/login", "password may have been changed — trying without auth")

    # Health
    r = get("/health")
    if ok(r):
        log("PASS", "GET /health")
    else:
        log("FAIL", "GET /health")

    # System stats
    r = get("/system-stats")
    if ok(r):
        log("PASS", "GET /system-stats")
    else:
        log("FAIL", "GET /system-stats")

    # Chat (streaming)
    try:
        headers = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
        form = {"message": (None, "hello MJ, testing")}
        r = requests.post(f"{BASE}/chat", files=form, headers=headers, timeout=15, stream=True)
        if r.status_code == 200:
            # Read first chunk
            chunk = next(r.iter_content(512), b"")
            log("PASS", "POST /chat (stream)", f"got {len(chunk)} bytes")
            r.close()
        else:
            log("FAIL", "POST /chat", f"status={r.status_code}")
    except Exception as e:
        log("FAIL", "POST /chat", str(e))

    # Chat history
    r = get("/chats")
    if ok(r):
        log("PASS", "GET /chats")
    else:
        log("FAIL", "GET /chats")

    # Ollama status
    r = get("/ollama-status")
    if ok(r):
        log("PASS", "GET /ollama-status", f"status={r.json().get('status', '?')}")
    else:
        log("SKIP", "GET /ollama-status", "Ollama may not be running")

    # Models
    r = get("/models")
    if ok(r):
        log("PASS", "GET /models")
    else:
        log("FAIL", "GET /models")

    # Voice settings
    r = get("/voice-settings")
    if ok(r):
        log("PASS", "GET /voice-settings")
    else:
        log("FAIL", "GET /voice-settings")


# ============================================================
# V3 — Tool Engine
# ============================================================
def test_v3():
    print("\n🔹 V3 — Tool Engine")

    # Weather
    r = get("/weather?city=Delhi&days=1")
    if ok(r):
        log("PASS", "GET /weather", f"city=Delhi")
    else:
        log("FAIL", "GET /weather")

    # Reminders
    r = get("/reminders")
    if ok(r):
        log("PASS", "GET /reminders")
    else:
        log("FAIL", "GET /reminders")

    # Scheduled tasks
    r = get("/scheduled-tasks")
    if ok(r):
        log("PASS", "GET /scheduled-tasks")
    else:
        log("FAIL", "GET /scheduled-tasks")

    # Clipboard history
    r = get("/clipboard/history")
    if ok(r):
        log("PASS", "GET /clipboard/history")
    else:
        log("FAIL", "GET /clipboard/history")

    # App usage
    r = get("/app-usage")
    if ok(r):
        log("PASS", "GET /app-usage")
    else:
        log("FAIL", "GET /app-usage")

    # Suggestions
    r = get("/suggestions")
    if ok(r):
        log("PASS", "GET /suggestions")
    else:
        log("FAIL", "GET /suggestions")


# ============================================================
# V4 — Agent Framework
# ============================================================
def test_v4():
    print("\n🔹 V4 — Agent Framework")

    # Framework status
    r = get("/framework/status")
    if ok(r):
        log("PASS", "GET /framework/status")
    else:
        log("FAIL", "GET /framework/status")

    # Message bus stats
    r = get("/framework/bus/stats")
    if ok(r):
        log("PASS", "GET /framework/bus/stats")
    else:
        log("FAIL", "GET /framework/bus/stats")

    # Publish to bus
    try:
        headers = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
        form = {"topic": (None, "test"), "sender": (None, "test_script")}
        r = requests.post(f"{BASE}/framework/bus/publish", files=form, headers=headers, timeout=10)
        if r.status_code == 200:
            log("PASS", "POST /framework/bus/publish")
        else:
            log("FAIL", "POST /framework/bus/publish", f"status={r.status_code}")
    except Exception as e:
        log("FAIL", "POST /framework/bus/publish", str(e))

    # Event stats
    r = get("/framework/events/stats")
    if ok(r):
        log("PASS", "GET /framework/events/stats")
    else:
        log("FAIL", "GET /framework/events/stats")

    # Shared memory stats
    r = get("/framework/memory/stats")
    if ok(r):
        log("PASS", "GET /framework/memory/stats")
    else:
        log("FAIL", "GET /framework/memory/stats")

    # Task queue stats
    r = get("/framework/queue/stats")
    if ok(r):
        log("PASS", "GET /framework/queue/stats")
    else:
        log("FAIL", "GET /framework/queue/stats")


# ============================================================
# V5 — Constitutional AI / Safety
# ============================================================
def test_v5():
    print("\n🔹 V5 — Constitutional AI")

    # Check safe input
    r = post("/safety/check-input", {"message": "What is Python?"})
    if ok(r):
        data = r.json()
        log("PASS", "POST /safety/check-input (safe)", f"safe={data.get('safe', data.get('approved'))}")
    else:
        log("FAIL", "POST /safety/check-input")

    # Check suspicious input
    r = post("/safety/check-input", {"message": "DROP TABLE users; --"})
    if ok(r):
        data = r.json()
        log("PASS", "POST /safety/check-input (threat)", f"result={data}")
    else:
        log("FAIL", "POST /safety/check-input (threat)")

    # Hallucination check
    r = post("/safety/hallucination", {"message": "According to a 2024 Stanford study published in Nature..."})
    if ok(r):
        log("PASS", "POST /safety/hallucination")
    else:
        log("FAIL", "POST /safety/hallucination")

    # Safety config
    r = get("/safety/config")
    if ok(r):
        log("PASS", "GET /safety/config")
    else:
        log("FAIL", "GET /safety/config")

    # Safety stats
    r = get("/safety/stats")
    if ok(r):
        log("PASS", "GET /safety/stats")
    else:
        log("FAIL", "GET /safety/stats")


# ============================================================
# V6 — Zeus (Master Brain)
# ============================================================
def test_v6():
    print("\n🔹 V6 — Zeus Master Brain")

    # Modules list
    r = get("/zeus/modules")
    if ok(r):
        modules = r.json()
        count = len(modules) if isinstance(modules, list) else modules.get("count", "?")
        log("PASS", "GET /zeus/modules", f"count={count}")
    else:
        log("FAIL", "GET /zeus/modules")

    # Route a message
    r = post("/zeus/route", {"message": "what time is it"})
    if ok(r):
        log("PASS", "POST /zeus/route", f"routed to: {r.json().get('module', '?')}")
    else:
        log("FAIL", "POST /zeus/route")

    # Smart route
    r = post("/zeus/smart-route", {"message": "send email to boss"})
    if ok(r):
        log("PASS", "POST /zeus/smart-route")
    else:
        log("FAIL", "POST /zeus/smart-route")

    # Zeus stats
    r = get("/zeus/stats")
    if ok(r):
        log("PASS", "GET /zeus/stats")
    else:
        log("FAIL", "GET /zeus/stats")

    # Plan
    r = post("/zeus/plan", {"message": "organize my morning routine"})
    if ok(r):
        log("PASS", "POST /zeus/plan")
    else:
        log("FAIL", "POST /zeus/plan")

    # Workflows
    r = get("/zeus/workflows")
    if ok(r):
        log("PASS", "GET /zeus/workflows")
    else:
        log("FAIL", "GET /zeus/workflows")

    # Recovery
    r = get("/zeus/recovery")
    if ok(r):
        log("PASS", "GET /zeus/recovery")
    else:
        log("FAIL", "GET /zeus/recovery")


# ============================================================
# V7 — Hermes (Messaging)
# ============================================================
def test_v7():
    print("\n🔹 V7 — Hermes Messaging")

    # Config
    r = get("/hermes/messaging/config")
    if ok(r):
        log("PASS", "GET /hermes/messaging/config")
    else:
        log("FAIL", "GET /hermes/messaging/config")

    # Platforms
    r = get("/hermes/messaging/platforms")
    if ok(r):
        log("PASS", "GET /hermes/messaging/platforms")
    else:
        log("FAIL", "GET /hermes/messaging/platforms")

    # History
    r = get("/hermes/messaging/history?limit=5")
    if ok(r):
        log("PASS", "GET /hermes/messaging/history")
    else:
        log("FAIL", "GET /hermes/messaging/history")

    # Stats
    r = get("/hermes/messaging/stats")
    if ok(r):
        log("PASS", "GET /hermes/messaging/stats")
    else:
        log("FAIL", "GET /hermes/messaging/stats")

    # Note: actual send tests require webhook URLs configured
    log("SKIP", "POST /hermes/messaging/send", "needs webhook config")


# ============================================================
# V8 — Athena (Knowledge)
# ============================================================
def test_v8():
    print("\n🔹 V8 — Athena Knowledge")

    # KB stats
    r = get("/knowledge-base")
    if ok(r):
        log("PASS", "GET /knowledge-base")
    else:
        log("FAIL", "GET /knowledge-base")

    # KB search
    r = post("/knowledge-base/search", {"query": "test"})
    if ok(r):
        log("PASS", "POST /knowledge-base/search")
    else:
        log("FAIL", "POST /knowledge-base/search")

    # Knowledge graph stats
    r = get("/knowledge/graph/stats")
    if ok(r):
        log("PASS", "GET /knowledge/graph/stats")
    else:
        log("FAIL", "GET /knowledge/graph/stats")

    # Graph search
    r = get("/knowledge/graph/search?q=python&limit=5")
    if ok(r):
        log("PASS", "GET /knowledge/graph/search")
    else:
        log("FAIL", "GET /knowledge/graph/search")

    # Citations
    r = get("/citations")
    if ok(r):
        log("PASS", "GET /citations")
    else:
        log("FAIL", "GET /citations")

    # Citation stats
    r = get("/citations/stats")
    if ok(r):
        log("PASS", "GET /citations/stats")
    else:
        log("FAIL", "GET /citations/stats")

    # Deep research (might be slow)
    r = post("/research", {"message": "what is FastAPI"})
    if ok(r):
        log("PASS", "POST /research", "deep research worked")
    else:
        log("SKIP", "POST /research", "may need internet")


# ============================================================
# V12 — Argus (Vision)
# ============================================================
def test_v12():
    print("\n🔹 V12 — Argus Vision")

    # Monitors
    r = get("/vision/monitors")
    if ok(r):
        data = r.json()
        log("PASS", "GET /vision/monitors", f"count={data.get('count', '?')}")
    else:
        log("FAIL", "GET /vision/monitors")

    # Screenshot
    r = post("/vision/screenshot", {"message": ""})
    if ok(r):
        data = r.json()
        log("PASS", "POST /vision/screenshot", f"file={data.get('filename', '?')}")
    else:
        log("FAIL", "POST /vision/screenshot")

    # Camera list
    r = get("/vision/cameras")
    if ok(r):
        data = r.json()
        log("PASS", "GET /vision/cameras", f"cameras={data.get('count', '?')}")
    else:
        log("SKIP", "GET /vision/cameras", "ffmpeg may not be installed")

    # Detect objects (from last screenshot)
    r = post("/vision/detect", {"message": ""})
    if ok(r):
        data = r.json()
        log("PASS", "POST /vision/detect", f"detections={data.get('count', '?')}")
    else:
        log("FAIL", "POST /vision/detect")

    # Analyze screen
    r = post("/vision/analyze", {"message": ""})
    if ok(r):
        data = r.json()
        log("PASS", "POST /vision/analyze", f"type={data.get('content_type', '?')}")
    else:
        log("FAIL", "POST /vision/analyze")

    # Vision history
    r = get("/vision/history?limit=5")
    if ok(r):
        log("PASS", "GET /vision/history")
    else:
        log("FAIL", "GET /vision/history")

    # Vision stats
    r = get("/vision/stats")
    if ok(r):
        log("PASS", "GET /vision/stats")
    else:
        log("FAIL", "GET /vision/stats")


# ============================================================
# V15 — Sentinel (Security)
# ============================================================
def test_v15():
    print("\n🔹 V15 — Sentinel Security")

    # Roles
    r = get("/sentinel/roles")
    if ok(r):
        data = r.json()
        log("PASS", "GET /sentinel/roles", f"roles={list(data.get('roles', {}).keys())}")
    else:
        log("FAIL", "GET /sentinel/roles")

    # Check permission
    r = post("/sentinel/check-permission", {"message": "default|chat"})
    if ok(r):
        data = r.json()
        log("PASS", "POST /sentinel/check-permission", f"allowed={data.get('allowed')}")
    else:
        log("FAIL", "POST /sentinel/check-permission")

    # Store a test secret
    r = post("/sentinel/vault/store", {"message": "test_key|test_value_123|testing"})
    if ok(r):
        log("PASS", "POST /sentinel/vault/store")
    else:
        log("FAIL", "POST /sentinel/vault/store")

    # List secrets
    r = get("/sentinel/vault")
    if ok(r):
        data = r.json()
        log("PASS", "GET /sentinel/vault", f"count={data.get('count', '?')}")
    else:
        log("FAIL", "GET /sentinel/vault")

    # Get secret
    r = get("/sentinel/vault/test_key")
    if ok(r):
        data = r.json()
        log("PASS", "GET /sentinel/vault/test_key", f"success={data.get('success')}")
    else:
        log("FAIL", "GET /sentinel/vault/test_key")

    # Delete test secret
    r = delete("/sentinel/vault/test_key")
    if ok(r):
        log("PASS", "DELETE /sentinel/vault/test_key")
    else:
        log("FAIL", "DELETE /sentinel/vault/test_key")

    # Scan safe input
    r = post("/sentinel/scan", {"message": "Hello how are you"})
    if ok(r):
        data = r.json()
        log("PASS", "POST /sentinel/scan (safe)", f"safe={data.get('safe')}")
    else:
        log("FAIL", "POST /sentinel/scan (safe)")

    # Scan threat
    r = post("/sentinel/scan", {"message": "'; DROP TABLE users; --"})
    if ok(r):
        data = r.json()
        log("PASS", "POST /sentinel/scan (threat)", f"safe={data.get('safe')}, threats={data.get('count')}")
    else:
        log("FAIL", "POST /sentinel/scan (threat)")

    # Audit log
    r = get("/sentinel/audit?limit=5")
    if ok(r):
        log("PASS", "GET /sentinel/audit")
    else:
        log("FAIL", "GET /sentinel/audit")

    # Audit stats
    r = get("/sentinel/audit/stats")
    if ok(r):
        log("PASS", "GET /sentinel/audit/stats")
    else:
        log("FAIL", "GET /sentinel/audit/stats")

    # Threats
    r = get("/sentinel/threats?limit=5")
    if ok(r):
        log("PASS", "GET /sentinel/threats")
    else:
        log("FAIL", "GET /sentinel/threats")

    # Threat stats
    r = get("/sentinel/threats/stats")
    if ok(r):
        log("PASS", "GET /sentinel/threats/stats")
    else:
        log("FAIL", "GET /sentinel/threats/stats")

    # Health check
    r = get("/sentinel/health")
    if ok(r):
        data = r.json()
        log("PASS", "GET /sentinel/health", f"health={data.get('health')}, score={data.get('score')}")
    else:
        log("FAIL", "GET /sentinel/health")

    # Config
    r = get("/sentinel/config")
    if ok(r):
        log("PASS", "GET /sentinel/config")
    else:
        log("FAIL", "GET /sentinel/config")

    # Stats
    r = get("/sentinel/stats")
    if ok(r):
        log("PASS", "GET /sentinel/stats")
    else:
        log("FAIL", "GET /sentinel/stats")


# ============================================================
# V16 — Reflection Engine
# ============================================================
def test_v16():
    print("\n🔹 V16 — Reflection Engine")

    # Log a test success
    r = post("/reflection/log-success", {"message": "test_module"})
    if ok(r):
        log("PASS", "POST /reflection/log-success")
    else:
        log("FAIL", "POST /reflection/log-success")

    # Log a test mistake
    r = post("/reflection/log-mistake", {"message": "test_module|wrong_answer|test query|bad response"})
    if ok(r):
        log("PASS", "POST /reflection/log-mistake")
    else:
        log("FAIL", "POST /reflection/log-mistake")

    # Get mistakes
    r = get("/reflection/mistakes?limit=5")
    if ok(r):
        log("PASS", "GET /reflection/mistakes")
    else:
        log("FAIL", "GET /reflection/mistakes")

    # Get scores
    r = get("/reflection/scores")
    if ok(r):
        log("PASS", "GET /reflection/scores")
    else:
        log("FAIL", "GET /reflection/scores")

    # Suggestions
    r = get("/reflection/suggestions")
    if ok(r):
        log("PASS", "GET /reflection/suggestions")
    else:
        log("FAIL", "GET /reflection/suggestions")

    # Daily reflection
    r = get("/reflection/daily")
    if ok(r):
        log("PASS", "GET /reflection/daily")
    else:
        log("FAIL", "GET /reflection/daily")

    # Generate report
    r = post("/reflection/report?days=7")
    if ok(r):
        log("PASS", "POST /reflection/report")
    else:
        log("FAIL", "POST /reflection/report")

    # Stats
    r = get("/reflection/stats")
    if ok(r):
        log("PASS", "GET /reflection/stats")
    else:
        log("FAIL", "GET /reflection/stats")


# ============================================================
# V17 — Learning Engine
# ============================================================
def test_v17():
    print("\n🔹 V17 — Learning Engine")

    # Record action
    r = post("/learning/record", {"message": "test_action|test_module"})
    if ok(r):
        log("PASS", "POST /learning/record")
    else:
        log("FAIL", "POST /learning/record")

    # Learn preference
    r = post("/learning/learn", {"message": "bhai mujhe code karna hai Python mein"})
    if ok(r):
        log("PASS", "POST /learning/learn")
    else:
        log("FAIL", "POST /learning/learn")

    # Get habits
    r = get("/learning/habits")
    if ok(r):
        log("PASS", "GET /learning/habits")
    else:
        log("FAIL", "GET /learning/habits")

    # Detect habits
    r = post("/learning/habits/detect")
    if ok(r):
        log("PASS", "POST /learning/habits/detect")
    else:
        log("FAIL", "POST /learning/habits/detect")

    # Get preferences
    r = get("/learning/preferences")
    if ok(r):
        data = r.json()
        log("PASS", "GET /learning/preferences", f"inferred={data.get('inferred', {})}")
    else:
        log("FAIL", "GET /learning/preferences")

    # Preference prompt
    r = get("/learning/preference-prompt")
    if ok(r):
        log("PASS", "GET /learning/preference-prompt")
    else:
        log("FAIL", "GET /learning/preference-prompt")

    # Prompt stats
    r = get("/learning/prompt-stats")
    if ok(r):
        log("PASS", "GET /learning/prompt-stats")
    else:
        log("FAIL", "GET /learning/prompt-stats")

    # Workflows
    r = get("/learning/workflows")
    if ok(r):
        log("PASS", "GET /learning/workflows")
    else:
        log("FAIL", "GET /learning/workflows")

    # Stats
    r = get("/learning/stats")
    if ok(r):
        log("PASS", "GET /learning/stats")
    else:
        log("FAIL", "GET /learning/stats")


# ============================================================
# V11 — Ares (Execution) — basic endpoint checks
# ============================================================
def test_v11():
    print("\n🔹 V11 — Ares Execution")

    # Processes
    r = get("/processes")
    if ok(r):
        log("PASS", "GET /processes")
    else:
        log("FAIL", "GET /processes")

    # Top processes
    r = get("/top-processes")
    if ok(r):
        log("PASS", "GET /top-processes")
    else:
        log("FAIL", "GET /top-processes")

    # Network stats
    r = get("/network-stats")
    if ok(r):
        log("PASS", "GET /network-stats")
    else:
        log("FAIL", "GET /network-stats")

    # Note: execute commands skipped for safety
    log("SKIP", "POST /execute", "skipped for safety — test manually")


# ============================================================
# V18 — Dashboard (frontend-only, check static serve)
# ============================================================
def test_v18():
    print("\n🔹 V18 — Dashboard")

    r = get("/")
    if r and r.status_code == 200:
        log("PASS", "GET / (frontend served)")
    else:
        log("SKIP", "GET /", "frontend may not be built yet")


# ============================================================
# MISC — OCR, Git, Alerts, Errors
# ============================================================
def test_misc():
    print("\n🔹 Misc — OCR, Git, Alerts, Errors")

    # OCR screen
    r = get("/ocr/screen")
    if ok(r):
        log("PASS", "GET /ocr/screen")
    else:
        log("SKIP", "GET /ocr/screen", "OCR may not be available")

    # Git status
    r = get("/git/status")
    if ok(r):
        log("PASS", "GET /git/status")
    else:
        log("FAIL", "GET /git/status")

    # Alerts
    r = get("/alerts")
    if ok(r):
        log("PASS", "GET /alerts")
    else:
        log("FAIL", "GET /alerts")

    # Active alerts
    r = get("/alerts/active")
    if ok(r):
        log("PASS", "GET /alerts/active")
    else:
        log("FAIL", "GET /alerts/active")

    # Errors
    r = get("/errors")
    if ok(r):
        log("PASS", "GET /errors")
    else:
        log("FAIL", "GET /errors")

    # Diagnostics
    r = get("/diagnostics")
    if ok(r):
        log("PASS", "GET /diagnostics")
    else:
        log("FAIL", "GET /diagnostics")

    # Intelligence status
    r = get("/intelligence")
    if ok(r):
        log("PASS", "GET /intelligence")
    else:
        log("FAIL", "GET /intelligence")


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  MJ ASSISTANT — FULL API TEST SUITE")
    print("=" * 60)
    print(f"  Target: {BASE}")
    print(f"  Time:   {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Check if server is running
    try:
        r = requests.get(f"{BASE}/health", timeout=5)
        print(f"\n  Server is UP (status={r.status_code})")
    except Exception:
        print(f"\n  ❌ Server not reachable at {BASE}")
        print("  Start it first: cd backend && python main.py")
        sys.exit(1)

    # Run all tests
    test_v1()
    test_v3()
    test_v4()
    test_v5()
    test_v6()
    test_v7()
    test_v8()
    test_v11()
    test_v12()
    test_v15()
    test_v16()
    test_v17()
    test_v18()
    test_misc()

    # Summary
    total = PASS + FAIL + SKIP
    print("\n" + "=" * 60)
    print(f"  RESULTS: {total} tests")
    print(f"  ✅ PASS: {PASS}")
    print(f"  ❌ FAIL: {FAIL}")
    print(f"  ⚠️  SKIP: {SKIP}")
    pct = round(PASS / total * 100) if total > 0 else 0
    print(f"  Score: {pct}%")
    print("=" * 60)

    if FAIL > 0:
        print("\n  Failed tests:")
        for r in RESULTS:
            if r["status"] == "FAIL":
                print(f"    ❌ {r['test']} — {r['detail']}")

    print()
