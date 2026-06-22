"""
MJ OCR Engine — Extract text from screenshots/images
Uses Windows built-in OCR (no Tesseract install needed).
Falls back to simple PowerShell OCR via Windows.Media.Ocr.
"""

import subprocess
import json
import re
import base64
from pathlib import Path
from typing import Optional

SCREENSHOT_DIR = Path(__file__).parent.parent / "screenshots"


def ocr_from_file(filepath: str) -> dict:
    """Extract text from an image file using Windows OCR."""
    path = Path(filepath)
    if not path.exists():
        return {"success": False, "text": "", "message": f"File not found: {filepath}"}

    # Use PowerShell with Windows.Media.Ocr (built-in, no install needed)
    ps_script = f'''
Add-Type -AssemblyName System.Runtime.WindowsRuntime

# Load Windows OCR
[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null
[Windows.Storage.StorageFile, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null

# Helper to await async operations
$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() |
    Where-Object {{ $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' }})[0]

Function Await($WinRtTask, $ResultType) {{
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}}

try {{
    $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync("{path.resolve()}")) ([Windows.Storage.StorageFile])
    $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])

    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
    $result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])

    $text = $result.Text
    $lineCount = ($result.Lines | Measure-Object).Count

    @{{ success = $true; text = $text; lines = $lineCount }} | ConvertTo-Json -Compress
}} catch {{
    @{{ success = $false; text = ""; error = $_.Exception.Message }} | ConvertTo-Json -Compress
}}
'''

    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=15
        )
        if r.stdout.strip():
            data = json.loads(r.stdout.strip())
            if data.get("success"):
                return {
                    "success": True,
                    "text": data["text"],
                    "lines": data.get("lines", 0),
                    "message": f"OCR extracted {data.get('lines', 0)} lines of text"
                }
            else:
                # Fallback to simpler method
                return _fallback_ocr(str(path.resolve()))
        else:
            return _fallback_ocr(str(path.resolve()))
    except subprocess.TimeoutExpired:
        return {"success": False, "text": "", "message": "OCR timed out"}
    except Exception as e:
        return _fallback_ocr(str(path.resolve()))


def _fallback_ocr(filepath: str) -> dict:
    """Fallback: Use PowerShell .NET bitmap + basic pixel analysis."""
    # Simple fallback — just confirm the file exists and suggest vision model
    return {
        "success": False,
        "text": "",
        "message": "Windows OCR unavailable. Use vision model (moondream) for image analysis."
    }


def ocr_screenshot() -> dict:
    """Take a fresh screenshot and OCR it."""
    from pc_control.executor import take_screenshot
    result = take_screenshot()
    if not result.get("success"):
        return {"success": False, "text": "", "message": "Screenshot failed"}

    filepath = result.get("filepath", "")
    if not filepath:
        # Find latest screenshot
        screenshots = sorted(SCREENSHOT_DIR.glob("screenshot_*.png"), reverse=True)
        if screenshots:
            filepath = str(screenshots[0])
        else:
            return {"success": False, "text": "", "message": "No screenshot found"}

    return ocr_from_file(filepath)


def detect_ocr_request(text: str) -> Optional[str]:
    """Detect if user wants OCR/screen reading."""
    lower = text.lower().strip()

    patterns = [
        r"(?:screen|screenshot)\s*(?:pe|par|me|mein)?\s*(?:kya|what)\s*(?:hai|is|likha|written)",
        r"(?:read|padh|dekh)\s*(?:the|my|meri|ye)?\s*(?:screen|screenshot)",
        r"(?:screen|screenshot)\s*(?:read|padh|text|extract|ocr)",
        r"(?:ocr|text\s+extract|extract\s+text)\s*(?:from|se)?\s*(?:screen|image|screenshot)?",
        r"(?:kya|what)\s*(?:likha|written|display|dikh)\s*(?:hai|is|raha)?\s*(?:screen|monitor)?",
        r"screen\s*(?:ka|ki|ke)?\s*(?:text|content|data)\s*(?:bata|nikaal|extract|read)",
        r"(?:screenshot\s+le\s+(?:ke|kar|aur)\s+(?:padh|read|bata))",
        r"(?:screen\s+capture\s+(?:and|aur)\s+(?:read|ocr|text))",
    ]

    for pat in patterns:
        if re.search(pat, lower):
            return "screen_ocr"

    # Check for file-based OCR
    file_patterns = [
        r"(?:image|photo|picture|pic|img)\s*(?:me|mein|se|from)?\s*(?:text|likha|written|kya|read|padh|extract)",
        r"(?:read|padh|extract)\s*(?:text|content)?\s*(?:from|se)?\s*(?:this|ye|is)?\s*(?:image|photo|picture|pic)",
    ]

    for pat in file_patterns:
        if re.search(pat, lower):
            return "image_ocr"

    return None
