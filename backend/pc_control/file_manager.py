"""
File Manager commands for MJ.
Supports: list files, count, open folder, search, file info, delete old files.
"""

import os
import re
import subprocess
from pathlib import Path
from datetime import datetime


# Common user folders
USER_FOLDERS = {
    "desktop": Path.home() / "Desktop",
    "downloads": Path.home() / "Downloads",
    "documents": Path.home() / "Documents",
    "pictures": Path.home() / "Pictures",
    "videos": Path.home() / "Videos",
    "music": Path.home() / "Music",
}


def parse_file_command(text: str) -> dict | None:
    """Parse file management commands."""
    lower = text.lower().strip()

    # ---- LIST FILES ----
    list_patterns = [
        r"(?:list|show|dikhao|batao)\s+(?:all\s+)?(?:files?|items?)\s+(?:in\s+|me\s+)?(.+)",
        r"(.+)\s+(?:me|mein|folder me)\s+(?:kya|kitni|kitne|kaun)\s+(?:files?|hai)",
        r"(.+)\s+(?:me|mein)\s+(?:files?|items?)\s+(?:dikhao|batao|list)",
    ]
    for pat in list_patterns:
        m = re.search(pat, lower)
        if m:
            folder = _resolve_folder(m.group(1).strip())
            if folder:
                return {"action": "list_files", "folder": str(folder), "name": folder.name}

    # ---- COUNT FILES ----
    count_patterns = [
        r"(?:kitni|kitne|how many|count)\s+(?:files?|items?)\s+(?:in\s+|me\s+|mein\s+)?(.+)",
        r"(.+)\s+(?:me|mein)\s+(?:kitni|kitne|how many)\s+(?:files?|items?)",
    ]
    for pat in count_patterns:
        m = re.search(pat, lower)
        if m:
            folder = _resolve_folder(m.group(1).strip())
            if folder:
                return {"action": "count_files", "folder": str(folder), "name": folder.name}

    # ---- OPEN FOLDER ----
    open_patterns = [
        r"(?:open|kholo)\s+(.+)\s+(?:folder|directory)",
        r"(.+)\s+(?:folder|directory)\s+(?:kholo|open)",
    ]
    for pat in open_patterns:
        m = re.search(pat, lower)
        if m:
            folder = _resolve_folder(m.group(1).strip())
            if folder:
                return {"action": "open_folder", "folder": str(folder), "name": folder.name}

    # ---- SEARCH FILES ----
    search_patterns = [
        r"(?:find|search|dhundho|khojo)\s+(?:file\s+)?(.+)\s+(?:in\s+|me\s+)?(.+)?",
        r"(.+)\s+(?:file\s+)?(?:dhundho|khojo|find|search)\s*(?:in\s+)?(.+)?",
    ]
    for pat in search_patterns:
        m = re.search(pat, lower)
        if m:
            query = m.group(1).strip()
            folder_name = m.group(2).strip() if m.group(2) else "desktop"
            folder = _resolve_folder(folder_name)
            if folder and query:
                return {"action": "search_files", "folder": str(folder), "query": query, "name": folder.name}

    # ---- FOLDER SIZE ----
    if any(w in lower for w in ["folder size", "kitna space", "folder ka size", "size of"]):
        for fname, fpath in USER_FOLDERS.items():
            if fname in lower:
                return {"action": "folder_size", "folder": str(fpath), "name": fname}

    return None


def execute_file_command(cmd: dict) -> dict:
    """Execute a file management command."""
    action = cmd["action"]

    try:
        if action == "list_files":
            return list_files(cmd["folder"], cmd["name"])
        elif action == "count_files":
            return count_files(cmd["folder"], cmd["name"])
        elif action == "open_folder":
            return open_folder(cmd["folder"], cmd["name"])
        elif action == "search_files":
            return search_files(cmd["folder"], cmd["query"], cmd["name"])
        elif action == "folder_size":
            return folder_size(cmd["folder"], cmd["name"])
        else:
            return {"success": False, "message": f"Unknown file action: {action}"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


def list_files(folder: str, name: str) -> dict:
    """List files in a folder."""
    p = Path(folder)
    if not p.exists():
        return {"success": False, "message": f"{name.title()} folder nahi mila."}

    items = list(p.iterdir())
    if not items:
        return {"success": True, "message": f"{name.title()} folder empty hai."}

    files = [f for f in items if f.is_file()]
    dirs = [f for f in items if f.is_dir()]

    msg_parts = [f"{name.title()} me {len(files)} files aur {len(dirs)} folders hain."]

    # Show first 10 files
    if files:
        msg_parts.append("Files:")
        for f in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
            size = _format_size(f.stat().st_size)
            msg_parts.append(f"  • {f.name} ({size})")
        if len(files) > 10:
            msg_parts.append(f"  ... aur {len(files) - 10} files.")

    return {"success": True, "message": "\n".join(msg_parts)}


def count_files(folder: str, name: str) -> dict:
    """Count files in a folder."""
    p = Path(folder)
    if not p.exists():
        return {"success": False, "message": f"{name.title()} folder nahi mila."}

    files = [f for f in p.iterdir() if f.is_file()]
    dirs = [f for f in p.iterdir() if f.is_dir()]

    # Count by extension
    ext_count = {}
    for f in files:
        ext = f.suffix.lower() or "(no ext)"
        ext_count[ext] = ext_count.get(ext, 0) + 1

    msg = f"{name.title()} me {len(files)} files aur {len(dirs)} folders hain."
    if ext_count:
        top = sorted(ext_count.items(), key=lambda x: x[1], reverse=True)[:5]
        breakdown = ", ".join([f"{c} {e}" for e, c in top])
        msg += f" Types: {breakdown}."

    return {"success": True, "message": msg}


def open_folder(folder: str, name: str) -> dict:
    """Open folder in File Explorer."""
    p = Path(folder)
    if not p.exists():
        return {"success": False, "message": f"{name.title()} folder nahi mila."}

    os.startfile(str(p))
    return {"success": True, "message": f"{name.title()} folder khol diya."}


def search_files(folder: str, query: str, name: str) -> dict:
    """Search for files matching query."""
    p = Path(folder)
    if not p.exists():
        return {"success": False, "message": f"{name.title()} folder nahi mila."}

    matches = []
    for f in p.rglob("*"):
        if f.is_file() and query.lower() in f.name.lower():
            matches.append(f)
        if len(matches) >= 20:
            break

    if not matches:
        return {"success": True, "message": f"'{query}' se koi file nahi mili {name} me."}

    msg_parts = [f"{len(matches)} files mili '{query}' se {name} me:"]
    for f in matches[:10]:
        size = _format_size(f.stat().st_size)
        rel = f.relative_to(p)
        msg_parts.append(f"  • {rel} ({size})")

    return {"success": True, "message": "\n".join(msg_parts)}


def folder_size(folder: str, name: str) -> dict:
    """Get total folder size."""
    p = Path(folder)
    if not p.exists():
        return {"success": False, "message": f"{name.title()} folder nahi mila."}

    total = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    return {"success": True, "message": f"{name.title()} folder ka size: {_format_size(total)}."}


def _resolve_folder(text: str) -> Path | None:
    """Resolve folder name to path."""
    text = text.strip().lower()
    for filler in ["the", "my", "mera", "meri", "folder", "directory", "ka", "ki", "ke"]:
        text = text.replace(filler, "").strip()

    for name, path in USER_FOLDERS.items():
        if name in text:
            return path

    # Try as absolute path
    if os.path.isdir(text):
        return Path(text)

    return None


def _format_size(bytes_size: int) -> str:
    """Format file size."""
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size / (1024*1024):.1f} MB"
    else:
        return f"{bytes_size / (1024*1024*1024):.1f} GB"
