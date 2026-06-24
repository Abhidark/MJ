"""
MJ Intelligence: Vision Engine (V12)
- Screenshot Upgrade: multi-monitor, region capture, auto-annotate
- Camera Capture: webcam snapshot with face detection placeholder
- Object Detection: label-based detection using color/shape heuristics + YOLO-ready
- Screen AI: UI element detection, layout analysis, text region extraction
"""

import json
import time
import re
import logging
import subprocess
import base64
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import Counter

logger = logging.getLogger("mj.vision")

DATA_DIR = Path(__file__).parent.parent / "vision_data"
DATA_DIR.mkdir(exist_ok=True)
SCREENSHOT_DIR = Path(__file__).parent.parent / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)
CAPTURES_DIR = DATA_DIR / "captures"
CAPTURES_DIR.mkdir(exist_ok=True)

HISTORY_FILE = DATA_DIR / "vision_history.json"
DETECTIONS_FILE = DATA_DIR / "detections.json"
SCREEN_ANALYSIS_FILE = DATA_DIR / "screen_analysis.json"


class VisionEngine:
    """
    Complete vision system for MJ — screenshot, camera, detection, screen AI.
    Runs on Windows without GPU; ready for YOLO/moondream upgrade on PC.
    """

    def __init__(self):
        self.history: List[dict] = self._load(HISTORY_FILE, [])
        self.detections: List[dict] = self._load(DETECTIONS_FILE, [])
        self.screen_analyses: List[dict] = self._load(SCREEN_ANALYSIS_FILE, [])

        # Object detection label categories (for heuristic + YOLO-ready)
        self.OBJECT_CATEGORIES = {
            "ui_elements": [
                "button", "textbox", "checkbox", "dropdown", "slider",
                "menu", "toolbar", "scrollbar", "tab", "dialog", "modal",
                "icon", "link", "input_field", "search_bar",
            ],
            "common_objects": [
                "person", "face", "hand", "phone", "laptop", "monitor",
                "keyboard", "mouse", "cup", "bottle", "book", "pen",
                "chair", "desk", "window", "door", "car", "plant",
            ],
            "screen_content": [
                "text_block", "image", "chart", "table", "code_block",
                "video_player", "notification", "popup", "sidebar",
                "header", "footer", "navigation", "form", "card",
            ],
        }

    # ========================
    # SCREENSHOT (UPGRADED)
    # ========================

    def take_screenshot(self, region: Optional[Dict] = None,
                        monitor: int = 0, annotate: bool = False) -> dict:
        """
        Take a screenshot with optional region crop and monitor selection.
        Returns filepath and metadata.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = SCREENSHOT_DIR / filename

        try:
            if region:
                # Region capture via PowerShell
                x, y, w, h = region.get("x", 0), region.get("y", 0), \
                    region.get("width", 800), region.get("height", 600)
                ps_script = f'''
Add-Type -AssemblyName System.Drawing
$bmp = New-Object System.Drawing.Bitmap({w}, {h})
$gfx = [System.Drawing.Graphics]::FromImage($bmp)
$gfx.CopyFromScreen({x}, {y}, 0, 0, (New-Object System.Drawing.Size({w}, {h})))
$bmp.Save("{filepath.resolve()}")
$gfx.Dispose()
$bmp.Dispose()
Write-Output "OK"
'''
            else:
                # Full screen / specific monitor
                ps_script = f'''
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
$screens = [System.Windows.Forms.Screen]::AllScreens
$idx = {monitor}
if ($idx -ge $screens.Count) {{ $idx = 0 }}
$bounds = $screens[$idx].Bounds
$bmp = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height)
$gfx = [System.Drawing.Graphics]::FromImage($bmp)
$gfx.CopyFromScreen($bounds.X, $bounds.Y, 0, 0, $bounds.Size)
$bmp.Save("{filepath.resolve()}")
$gfx.Dispose()
$bmp.Dispose()

# Return monitor info
$info = @{{
    monitor = $idx
    total_monitors = $screens.Count
    width = $bounds.Width
    height = $bounds.Height
    x = $bounds.X
    y = $bounds.Y
}}
$info | ConvertTo-Json -Compress
'''
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True, text=True, timeout=10
            )

            if filepath.exists():
                # Parse monitor info if available
                monitor_info = {}
                output = result.stdout.strip()
                if output and output.startswith("{"):
                    try:
                        monitor_info = json.loads(output)
                    except Exception:
                        pass

                entry = {
                    "type": "screenshot",
                    "filepath": str(filepath),
                    "filename": filename,
                    "region": region,
                    "monitor": monitor,
                    "monitor_info": monitor_info,
                    "timestamp": time.time(),
                    "size_bytes": filepath.stat().st_size,
                }
                self.history.append(entry)
                self.history = self.history[-200:]
                self._save(HISTORY_FILE, self.history)

                return {
                    "success": True,
                    "filepath": str(filepath),
                    "filename": filename,
                    "monitor_info": monitor_info,
                    "size_bytes": filepath.stat().st_size,
                    "message": f"Screenshot saved: {filename}",
                }
            else:
                return {"success": False, "message": "Screenshot file was not created"}

        except subprocess.TimeoutExpired:
            return {"success": False, "message": "Screenshot timed out"}
        except Exception as e:
            logger.error(f"Screenshot error: {e}")
            return {"success": False, "message": f"Screenshot failed: {e}"}

    def get_monitors(self) -> dict:
        """List all connected monitors with resolution info."""
        ps_script = '''
Add-Type -AssemblyName System.Windows.Forms
$screens = [System.Windows.Forms.Screen]::AllScreens
$result = @()
foreach ($s in $screens) {
    $result += @{
        name = $s.DeviceName
        primary = $s.Primary
        width = $s.Bounds.Width
        height = $s.Bounds.Height
        x = $s.Bounds.X
        y = $s.Bounds.Y
        working_width = $s.WorkingArea.Width
        working_height = $s.WorkingArea.Height
    }
}
$result | ConvertTo-Json -Compress
'''
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True, text=True, timeout=5
            )
            if r.stdout.strip():
                data = json.loads(r.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                return {"success": True, "monitors": data, "count": len(data)}
        except Exception as e:
            logger.warning(f"Monitor detection failed: {e}")
        return {"success": True, "monitors": [{"name": "Primary", "primary": True}], "count": 1}

    # ========================
    # CAMERA CAPTURE
    # ========================

    def capture_camera(self, camera_index: int = 0, save: bool = True) -> dict:
        """
        Capture a frame from webcam using PowerShell + .NET or ffmpeg.
        Falls back to test frame if no camera available.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"camera_{timestamp}.png"
        filepath = CAPTURES_DIR / filename

        # Try ffmpeg first (most reliable on Windows)
        try:
            ffmpeg_cmd = [
                "ffmpeg", "-f", "dshow", "-i",
                f"video=@device_pnp_\\\\?\\usb" if camera_index > 0 else "video=0",
                "-frames:v", "1", "-y", str(filepath.resolve())
            ]
            # Use simpler approach — list devices first
            list_cmd = [
                "ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", "dummy"
            ]
            list_result = subprocess.run(
                list_cmd, capture_output=True, text=True, timeout=5
            )
            # Extract video device names from stderr
            devices = []
            for line in list_result.stderr.split("\n"):
                if '"' in line and "video" in line.lower():
                    match = re.search(r'"([^"]+)"', line)
                    if match:
                        devices.append(match.group(1))

            if devices:
                device = devices[min(camera_index, len(devices) - 1)]
                capture_cmd = [
                    "ffmpeg", "-f", "dshow", "-i", f"video={device}",
                    "-frames:v", "1", "-y", str(filepath.resolve())
                ]
                result = subprocess.run(
                    capture_cmd, capture_output=True, text=True, timeout=10
                )
                if filepath.exists():
                    entry = {
                        "type": "camera",
                        "filepath": str(filepath),
                        "filename": filename,
                        "camera_index": camera_index,
                        "device": device,
                        "timestamp": time.time(),
                    }
                    self.history.append(entry)
                    self.history = self.history[-200:]
                    self._save(HISTORY_FILE, self.history)

                    return {
                        "success": True,
                        "filepath": str(filepath),
                        "filename": filename,
                        "device": device,
                        "available_cameras": devices,
                        "message": f"Camera captured: {filename}",
                    }

            return {
                "success": False,
                "available_cameras": devices,
                "message": "No camera available or capture failed. "
                           "Install ffmpeg and ensure camera is connected.",
            }
        except FileNotFoundError:
            return {
                "success": False,
                "message": "ffmpeg not found. Install ffmpeg for camera capture. "
                           "Or connect camera and install OpenCV on PC.",
            }
        except Exception as e:
            return {"success": False, "message": f"Camera capture failed: {e}"}

    def list_cameras(self) -> dict:
        """List available cameras on the system."""
        try:
            list_cmd = [
                "ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", "dummy"
            ]
            result = subprocess.run(
                list_cmd, capture_output=True, text=True, timeout=5
            )
            devices = []
            for line in result.stderr.split("\n"):
                if '"' in line and ("video" in line.lower() or "camera" in line.lower()):
                    match = re.search(r'"([^"]+)"', line)
                    if match:
                        devices.append(match.group(1))

            return {
                "success": True,
                "cameras": devices,
                "count": len(devices),
            }
        except FileNotFoundError:
            return {"success": False, "cameras": [], "message": "ffmpeg not installed"}
        except Exception as e:
            return {"success": False, "cameras": [], "message": str(e)}

    # ========================
    # OBJECT DETECTION
    # ========================

    def detect_objects(self, image_path: str, use_ocr: bool = True) -> dict:
        """
        Detect objects in an image using heuristic analysis + OCR.
        Ready for YOLO model upgrade on PC.
        """
        path = Path(image_path)
        if not path.exists():
            return {"success": False, "message": f"Image not found: {image_path}"}

        detections = []
        metadata = {"width": 0, "height": 0, "format": path.suffix}

        # Step 1: Get image dimensions via PowerShell
        try:
            ps_dim = f'''
Add-Type -AssemblyName System.Drawing
$img = [System.Drawing.Image]::FromFile("{path.resolve()}")
@{{ width = $img.Width; height = $img.Height; format = $img.RawFormat.ToString() }} | ConvertTo-Json -Compress
$img.Dispose()
'''
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_dim],
                capture_output=True, text=True, timeout=5
            )
            if r.stdout.strip():
                dim = json.loads(r.stdout.strip())
                metadata["width"] = dim.get("width", 0)
                metadata["height"] = dim.get("height", 0)
        except Exception:
            pass

        # Step 2: Color region analysis (detect dominant regions)
        try:
            ps_color = f'''
Add-Type -AssemblyName System.Drawing
$img = [System.Drawing.Image]::FromFile("{path.resolve()}")
$w = $img.Width; $h = $img.Height
$bmp = New-Object System.Drawing.Bitmap($img)

# Sample a grid of pixels for color analysis
$colors = @{{}}
$step = [Math]::Max(1, [Math]::Floor([Math]::Min($w, $h) / 20))
for ($y = 0; $y -lt $h; $y += $step) {{
    for ($x = 0; $x -lt $w; $x += $step) {{
        $px = $bmp.GetPixel($x, $y)
        # Classify into broad color regions
        $r = $px.R; $g = $px.G; $b = $px.B
        $brightness = ($r + $g + $b) / 3
        if ($brightness -lt 40) {{ $cat = "dark_region" }}
        elseif ($brightness -gt 220) {{ $cat = "light_region" }}
        elseif ($r -gt 150 -and $g -lt 100 -and $b -lt 100) {{ $cat = "red_element" }}
        elseif ($g -gt 150 -and $r -lt 100 -and $b -lt 100) {{ $cat = "green_element" }}
        elseif ($b -gt 150 -and $r -lt 100 -and $g -lt 100) {{ $cat = "blue_element" }}
        elseif ($r -gt 200 -and $g -gt 200 -and $b -lt 80) {{ $cat = "yellow_element" }}
        else {{ $cat = "neutral" }}

        if (-not $colors.ContainsKey($cat)) {{ $colors[$cat] = 0 }}
        $colors[$cat]++
    }}
}}
$bmp.Dispose(); $img.Dispose()
$colors | ConvertTo-Json -Compress
'''
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_color],
                capture_output=True, text=True, timeout=10
            )
            if r.stdout.strip():
                color_data = json.loads(r.stdout.strip())
                total_samples = sum(color_data.values()) or 1

                for region, count in color_data.items():
                    pct = round(count / total_samples * 100, 1)
                    if pct > 2 and region != "neutral":
                        detections.append({
                            "label": region,
                            "type": "color_region",
                            "confidence": min(0.9, pct / 100 + 0.3),
                            "coverage_pct": pct,
                        })
        except Exception as e:
            logger.warning(f"Color analysis failed: {e}")

        # Step 3: OCR-based text detection
        if use_ocr:
            try:
                from intelligence.ocr_engine import ocr_from_file
                ocr_result = ocr_from_file(str(path.resolve()))
                if ocr_result.get("success") and ocr_result.get("text"):
                    text = ocr_result["text"]
                    lines = ocr_result.get("lines", 0)
                    detections.append({
                        "label": "text_content",
                        "type": "text",
                        "confidence": 0.85,
                        "text_preview": text[:200],
                        "line_count": lines,
                    })

                    # Detect UI elements from text patterns
                    ui_detected = self._detect_ui_from_text(text)
                    detections.extend(ui_detected)
            except Exception as e:
                logger.warning(f"OCR detection failed: {e}")

        # Step 4: Try YOLO via Python (if available on PC)
        yolo_result = self._try_yolo_detection(str(path.resolve()))
        if yolo_result:
            detections.extend(yolo_result)

        # Record detection
        entry = {
            "image": str(path),
            "detections": detections,
            "metadata": metadata,
            "timestamp": time.time(),
        }
        self.detections.append(entry)
        self.detections = self.detections[-100:]
        self._save(DETECTIONS_FILE, self.detections)

        return {
            "success": True,
            "image": str(path),
            "metadata": metadata,
            "detections": detections,
            "count": len(detections),
            "message": f"Detected {len(detections)} elements in image",
        }

    def _detect_ui_from_text(self, text: str) -> List[dict]:
        """Detect UI elements from OCR text patterns."""
        detections = []
        lower = text.lower()

        # Button patterns
        button_patterns = [
            r"\b(ok|cancel|submit|save|close|yes|no|apply|next|back|done|login|sign\s*in|sign\s*up)\b",
            r"\b(click here|press|tap)\b",
        ]
        for pat in button_patterns:
            matches = re.findall(pat, lower)
            if matches:
                for m in set(matches):
                    detections.append({
                        "label": f"button:{m.strip()}",
                        "type": "ui_element",
                        "element": "button",
                        "confidence": 0.7,
                    })

        # Menu/Navigation
        if re.search(r"\b(file|edit|view|tools|help|settings|options|preferences)\b", lower):
            detections.append({
                "label": "menu_bar",
                "type": "ui_element",
                "element": "menu",
                "confidence": 0.75,
            })

        # Input fields
        if re.search(r"\b(search|type here|enter|username|password|email)\b", lower):
            detections.append({
                "label": "input_field",
                "type": "ui_element",
                "element": "textbox",
                "confidence": 0.65,
            })

        # Error / notification patterns
        if re.search(r"\b(error|warning|failed|success|info|alert)\b", lower):
            detections.append({
                "label": "notification",
                "type": "ui_element",
                "element": "notification",
                "confidence": 0.7,
            })

        return detections

    def _try_yolo_detection(self, image_path: str) -> List[dict]:
        """
        Try YOLO object detection (requires ultralytics on PC).
        Returns empty list if not available — no error.
        """
        try:
            from ultralytics import YOLO
            model = YOLO("yolov8n.pt")
            results = model(image_path, verbose=False)

            detections = []
            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    label = model.names[cls_id]
                    x1, y1, x2, y2 = box.xyxy[0].tolist()

                    if conf >= 0.3:
                        detections.append({
                            "label": label,
                            "type": "yolo_object",
                            "confidence": round(conf, 3),
                            "bbox": {
                                "x1": round(x1), "y1": round(y1),
                                "x2": round(x2), "y2": round(y2),
                            },
                        })
            return detections
        except ImportError:
            return []
        except Exception as e:
            logger.debug(f"YOLO not available: {e}")
            return []

    # ========================
    # SCREEN AI
    # ========================

    def analyze_screen(self, image_path: Optional[str] = None) -> dict:
        """
        Analyze screen content — detect UI layout, text regions,
        interactive elements, and content type.
        """
        # Take fresh screenshot if no image provided
        if not image_path:
            ss = self.take_screenshot()
            if not ss.get("success"):
                return {"success": False, "message": "Could not capture screen"}
            image_path = ss["filepath"]

        path = Path(image_path)
        if not path.exists():
            return {"success": False, "message": f"Image not found: {image_path}"}

        analysis = {
            "image": str(path),
            "timestamp": time.time(),
            "layout": {},
            "text_regions": [],
            "ui_elements": [],
            "content_type": "unknown",
            "active_app": "",
            "suggestions": [],
        }

        # 1. Get active window info
        try:
            ps_win = '''
Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public class WinAPI {
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
}
"@
$hwnd = [WinAPI]::GetForegroundWindow()
$sb = New-Object System.Text.StringBuilder(256)
[WinAPI]::GetWindowText($hwnd, $sb, 256) | Out-Null
$rect = New-Object WinAPI+RECT
[WinAPI]::GetWindowRect($hwnd, [ref]$rect) | Out-Null
@{
    title = $sb.ToString()
    x = $rect.Left; y = $rect.Top
    width = $rect.Right - $rect.Left
    height = $rect.Bottom - $rect.Top
} | ConvertTo-Json -Compress
'''
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_win],
                capture_output=True, text=True, timeout=5
            )
            if r.stdout.strip():
                win_info = json.loads(r.stdout.strip())
                analysis["active_app"] = win_info.get("title", "")
                analysis["layout"]["active_window"] = win_info
        except Exception:
            pass

        # 2. OCR for text regions
        try:
            from intelligence.ocr_engine import ocr_from_file
            ocr_result = ocr_from_file(str(path.resolve()))
            if ocr_result.get("success") and ocr_result.get("text"):
                text = ocr_result["text"]
                # Split into regions by line grouping
                lines = text.split("\n")
                current_region = []
                regions = []

                for line in lines:
                    stripped = line.strip()
                    if stripped:
                        current_region.append(stripped)
                    elif current_region:
                        regions.append(" ".join(current_region))
                        current_region = []
                if current_region:
                    regions.append(" ".join(current_region))

                for i, region in enumerate(regions[:20]):
                    analysis["text_regions"].append({
                        "index": i,
                        "text": region[:300],
                        "word_count": len(region.split()),
                        "type": self._classify_text_region(region),
                    })

                # Detect UI elements
                analysis["ui_elements"] = self._detect_ui_from_text(text)

                # Classify content type
                analysis["content_type"] = self._classify_screen_content(text, analysis["active_app"])
        except Exception as e:
            logger.warning(f"Screen OCR failed: {e}")

        # 3. Generate suggestions based on analysis
        analysis["suggestions"] = self._generate_screen_suggestions(analysis)

        # Store analysis
        self.screen_analyses.append(analysis)
        self.screen_analyses = self.screen_analyses[-50:]
        self._save(SCREEN_ANALYSIS_FILE, self.screen_analyses)

        return {
            "success": True,
            **analysis,
            "message": f"Screen analyzed: {analysis['content_type']} — "
                       f"{len(analysis['text_regions'])} text regions, "
                       f"{len(analysis['ui_elements'])} UI elements",
        }

    def _classify_text_region(self, text: str) -> str:
        """Classify a text region by content type."""
        lower = text.lower()
        if re.search(r"\b(def |class |function |import |const |var |let )\b", text):
            return "code"
        if re.search(r"\b(error|exception|traceback|failed|warning)\b", lower):
            return "error_message"
        if re.search(r"https?://|www\.", lower):
            return "url"
        if re.search(r"\b(from|to|subject|date|reply)\b", lower) and "@" in text:
            return "email"
        if len(text.split()) <= 5:
            return "label"
        if len(text.split()) > 50:
            return "paragraph"
        return "text"

    def _classify_screen_content(self, text: str, app_title: str) -> str:
        """Classify what type of content is on screen."""
        lower = text.lower()
        title_lower = app_title.lower()

        if any(x in title_lower for x in ["chrome", "firefox", "edge", "brave"]):
            return "web_browser"
        if any(x in title_lower for x in ["code", "studio", "vim", "notepad++", "pycharm"]):
            return "code_editor"
        if any(x in title_lower for x in ["word", "docs", "writer"]):
            return "document_editor"
        if any(x in title_lower for x in ["excel", "sheets", "calc"]):
            return "spreadsheet"
        if any(x in title_lower for x in ["terminal", "cmd", "powershell", "bash"]):
            return "terminal"
        if any(x in title_lower for x in ["outlook", "gmail", "mail", "thunderbird"]):
            return "email_client"
        if any(x in title_lower for x in ["slack", "discord", "teams", "telegram"]):
            return "chat_app"

        # Content-based classification
        if re.search(r"\b(def |class |import |function |=>)\b", text):
            return "code_content"
        if re.search(r"\b(inbox|from:|subject:|re:)\b", lower):
            return "email_content"

        return "general"

    def _generate_screen_suggestions(self, analysis: dict) -> List[str]:
        """Generate contextual suggestions based on screen analysis."""
        suggestions = []
        content_type = analysis.get("content_type", "")
        ui_elements = analysis.get("ui_elements", [])
        text_regions = analysis.get("text_regions", [])

        # Check for errors
        error_regions = [r for r in text_regions if r.get("type") == "error_message"]
        if error_regions:
            suggestions.append("Errors detected on screen. Ask me to analyze and fix them.")

        # Code-related
        if content_type in ("code_editor", "code_content"):
            suggestions.append("I can review the code visible on screen.")
            suggestions.append("Ask me to explain or debug what you see.")

        # Email
        if content_type in ("email_client", "email_content"):
            suggestions.append("I can help draft a reply to this email.")

        # Many UI elements
        if len(ui_elements) > 5:
            suggestions.append("Complex UI detected. I can describe the layout.")

        # Long text
        long_text = [r for r in text_regions if r.get("word_count", 0) > 100]
        if long_text:
            suggestions.append("Long text detected. Want me to summarize it?")

        return suggestions[:5]

    def compare_screenshots(self, path1: str, path2: str) -> dict:
        """
        Compare two screenshots for differences.
        Useful for UI testing, change detection.
        """
        p1, p2 = Path(path1), Path(path2)
        if not p1.exists() or not p2.exists():
            return {"success": False, "message": "One or both images not found"}

        try:
            ps_compare = f'''
Add-Type -AssemblyName System.Drawing
$img1 = New-Object System.Drawing.Bitmap("{p1.resolve()}")
$img2 = New-Object System.Drawing.Bitmap("{p2.resolve()}")

$same_size = ($img1.Width -eq $img2.Width) -and ($img1.Height -eq $img2.Height)
$diff_pixels = 0
$total_pixels = 0

if ($same_size) {{
    $step = [Math]::Max(1, [Math]::Floor([Math]::Min($img1.Width, $img1.Height) / 50))
    for ($y = 0; $y -lt $img1.Height; $y += $step) {{
        for ($x = 0; $x -lt $img1.Width; $x += $step) {{
            $total_pixels++
            $px1 = $img1.GetPixel($x, $y)
            $px2 = $img2.GetPixel($x, $y)
            $diff = [Math]::Abs($px1.R - $px2.R) + [Math]::Abs($px1.G - $px2.G) + [Math]::Abs($px1.B - $px2.B)
            if ($diff -gt 30) {{ $diff_pixels++ }}
        }}
    }}
}}

$img1.Dispose(); $img2.Dispose()
@{{
    same_size = $same_size
    total_sampled = $total_pixels
    different = $diff_pixels
    similarity = if ($total_pixels -gt 0) {{ [Math]::Round((1 - $diff_pixels / $total_pixels) * 100, 1) }} else {{ 0 }}
}} | ConvertTo-Json -Compress
'''
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_compare],
                capture_output=True, text=True, timeout=15
            )
            if r.stdout.strip():
                data = json.loads(r.stdout.strip())
                return {
                    "success": True,
                    "image1": str(p1),
                    "image2": str(p2),
                    "same_size": data.get("same_size", False),
                    "similarity_pct": data.get("similarity", 0),
                    "different_samples": data.get("different", 0),
                    "total_samples": data.get("total_sampled", 0),
                    "message": f"Images are {data.get('similarity', 0)}% similar",
                }
        except Exception as e:
            return {"success": False, "message": f"Comparison failed: {e}"}

        return {"success": False, "message": "Comparison failed"}

    # ========================
    # HISTORY & STATS
    # ========================

    def get_history(self, limit: int = 50, type_filter: str = "") -> List[dict]:
        """Get vision operation history."""
        history = self.history
        if type_filter:
            history = [h for h in history if h.get("type") == type_filter]
        return history[-limit:]

    def get_recent_detections(self, limit: int = 20) -> List[dict]:
        return self.detections[-limit:]

    def get_recent_analyses(self, limit: int = 10) -> List[dict]:
        return self.screen_analyses[-limit:]

    def get_stats(self) -> dict:
        """Get vision engine statistics."""
        type_counts = Counter(h.get("type", "unknown") for h in self.history)
        return {
            "total_captures": len(self.history),
            "screenshots": type_counts.get("screenshot", 0),
            "camera_captures": type_counts.get("camera", 0),
            "total_detections": len(self.detections),
            "screen_analyses": len(self.screen_analyses),
            "by_type": dict(type_counts),
        }

    # ========================
    # PERSISTENCE
    # ========================

    @staticmethod
    def _load(filepath: Path, default):
        if filepath.exists():
            try:
                return json.loads(filepath.read_text(encoding="utf-8"))
            except Exception:
                pass
        return default if not callable(default) else default()

    @staticmethod
    def _save(filepath: Path, data):
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(
                json.dumps(data, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"Failed to save {filepath.name}: {e}")


# Singleton
vision_engine = VisionEngine()
