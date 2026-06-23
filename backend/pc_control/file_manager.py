"""
File Manager commands for MJ.
Supports: list, count, open, search, size, create, delete, move, copy, rename.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
try:
    from send2trash import send2trash as _send2trash
except ImportError:
    _send2trash = None  # Fallback: permanent delete if send2trash not installed


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

    # ---- CREATE FILE / FOLDER ----
    create_patterns = [
        r"(?:create|banao|bana do|make|new)\s+(?:a\s+)?(?:file|folder|directory)\s+(?:named?\s+)?(.+?)(?:\s+(?:in|me|mein)\s+(.+))?$",
        r"(.+?)\s+(?:naam|name)\s+(?:ka|ki|se)\s+(?:file|folder)\s+(?:banao|bana|create)\s*(?:in\s+(.+))?$",
    ]
    for pat in create_patterns:
        m = re.search(pat, lower)
        if m:
            name = m.group(1).strip().strip('"\'')
            dest_text = m.group(2).strip() if m.group(2) else "desktop"
            dest = _resolve_folder(dest_text)
            if dest:
                is_folder = any(w in lower for w in ["folder", "directory"])
                return {"action": "create_item", "folder": str(dest), "item_name": name, "is_folder": is_folder}

    # ---- DELETE FILE ----
    delete_patterns = [
        r"(?:delete|remove|hatao|mita|mita do|del)\s+(?:the\s+)?(?:file|folder)?\s*(.+?)(?:\s+(?:from|se|in|me)\s+(.+))?$",
        r"(.+?)\s+(?:ko|file|folder)\s+(?:delete|hatao|mita|remove)\s*(?:(?:from|se)\s+(.+))?$",
    ]
    for pat in delete_patterns:
        m = re.search(pat, lower)
        if m:
            name = m.group(1).strip().strip('"\'')
            src_text = m.group(2).strip() if m.group(2) else "desktop"
            src = _resolve_folder(src_text)
            if src and name:
                return {"action": "delete_item", "folder": str(src), "item_name": name}

    # ---- RENAME FILE ----
    rename_patterns = [
        r"(?:rename|naam badlo|naam change)\s+(.+?)\s+(?:to|se|ko)\s+(.+?)(?:\s+(?:in|me)\s+(.+))?$",
    ]
    for pat in rename_patterns:
        m = re.search(pat, lower)
        if m:
            old_name = m.group(1).strip().strip('"\'')
            new_name = m.group(2).strip().strip('"\'')
            folder_text = m.group(3).strip() if m.group(3) else "desktop"
            folder = _resolve_folder(folder_text)
            if folder and old_name and new_name:
                return {"action": "rename_item", "folder": str(folder), "old_name": old_name, "new_name": new_name}

    # ---- MOVE FILE ----
    move_patterns = [
        r"(?:move|shift|transfer|bhejo|le jao)\s+(.+?)\s+(?:to|me|mein|ko)\s+(.+)",
    ]
    for pat in move_patterns:
        m = re.search(pat, lower)
        if m:
            src_name = m.group(1).strip().strip('"\'')
            dest_text = m.group(2).strip()
            dest = _resolve_folder(dest_text)
            if dest:
                return {"action": "move_item", "item_name": src_name, "dest": str(dest), "dest_name": dest.name}

    # ---- COPY FILE ----
    copy_patterns = [
        r"(?:copy|duplicate|naqal|copy karo)\s+(.+?)\s+(?:to|me|mein|ko)\s+(.+)",
    ]
    for pat in copy_patterns:
        m = re.search(pat, lower)
        if m:
            src_name = m.group(1).strip().strip('"\'')
            dest_text = m.group(2).strip()
            dest = _resolve_folder(dest_text)
            if dest:
                return {"action": "copy_item", "item_name": src_name, "dest": str(dest), "dest_name": dest.name}

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
        elif action == "create_item":
            return create_item(cmd["folder"], cmd["item_name"], cmd.get("is_folder", False))
        elif action == "delete_item":
            return delete_item(cmd["folder"], cmd["item_name"])
        elif action == "rename_item":
            return rename_item(cmd["folder"], cmd["old_name"], cmd["new_name"])
        elif action == "move_item":
            return move_item(cmd["item_name"], cmd["dest"], cmd["dest_name"])
        elif action == "copy_item":
            return copy_item(cmd["item_name"], cmd["dest"], cmd["dest_name"])
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


def create_item(folder: str, item_name: str, is_folder: bool = False) -> dict:
    """Create a new file or folder."""
    p = Path(folder) / item_name
    if p.exists():
        kind = "Folder" if p.is_dir() else "File"
        return {"success": False, "message": f"{kind} '{item_name}' already exists."}

    try:
        if is_folder:
            p.mkdir(parents=True, exist_ok=True)
            return {"success": True, "message": f"Folder '{item_name}' bana diya: {p}"}
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.touch()
            return {"success": True, "message": f"File '{item_name}' bana diya: {p}"}
    except PermissionError:
        return {"success": False, "message": f"Permission denied — '{item_name}' create nahi ho paya."}


def delete_item(folder: str, item_name: str) -> dict:
    """Delete a file or folder (sends to Recycle Bin if possible)."""
    p = Path(folder) / item_name
    if not p.exists():
        # Try glob match
        matches = list(Path(folder).glob(f"*{item_name}*"))
        if len(matches) == 1:
            p = matches[0]
        elif len(matches) > 1:
            names = [m.name for m in matches[:5]]
            return {"success": False, "message": f"Multiple matches: {', '.join(names)}. Exact name do."}
        else:
            return {"success": False, "message": f"'{item_name}' nahi mila {Path(folder).name} me."}

    try:
        if _send2trash:
            _send2trash(str(p))
            return {"success": True, "message": f"'{p.name}' Recycle Bin me bhej diya."}
        raise RuntimeError("send2trash not available")
    except Exception:
        # Fallback: permanent delete
        try:
            if p.is_dir():
                shutil.rmtree(str(p))
            else:
                p.unlink()
            return {"success": True, "message": f"'{p.name}' permanently delete ho gaya."}
        except PermissionError:
            return {"success": False, "message": f"Permission denied — '{p.name}' delete nahi ho paya."}


def rename_item(folder: str, old_name: str, new_name: str) -> dict:
    """Rename a file or folder."""
    old_path = Path(folder) / old_name
    if not old_path.exists():
        return {"success": False, "message": f"'{old_name}' nahi mila {Path(folder).name} me."}

    new_path = Path(folder) / new_name
    if new_path.exists():
        return {"success": False, "message": f"'{new_name}' pehle se exist karta hai."}

    try:
        old_path.rename(new_path)
        return {"success": True, "message": f"'{old_name}' ka naam '{new_name}' kar diya."}
    except PermissionError:
        return {"success": False, "message": f"Permission denied — rename nahi ho paya."}


def move_item(item_name: str, dest: str, dest_name: str) -> dict:
    """Move file/folder to destination."""
    # Find source in known folders
    src_path = _find_item(item_name)
    if not src_path:
        return {"success": False, "message": f"'{item_name}' nahi mila kisi folder me."}

    dest_path = Path(dest) / src_path.name
    if dest_path.exists():
        return {"success": False, "message": f"'{src_path.name}' already exists in {dest_name}."}

    try:
        shutil.move(str(src_path), str(dest_path))
        return {"success": True, "message": f"'{src_path.name}' ko {dest_name} me move kar diya."}
    except PermissionError:
        return {"success": False, "message": f"Permission denied — move nahi ho paya."}


def copy_item(item_name: str, dest: str, dest_name: str) -> dict:
    """Copy file/folder to destination."""
    src_path = _find_item(item_name)
    if not src_path:
        return {"success": False, "message": f"'{item_name}' nahi mila kisi folder me."}

    dest_path = Path(dest) / src_path.name
    if dest_path.exists():
        return {"success": False, "message": f"'{src_path.name}' already exists in {dest_name}."}

    try:
        if src_path.is_dir():
            shutil.copytree(str(src_path), str(dest_path))
        else:
            shutil.copy2(str(src_path), str(dest_path))
        return {"success": True, "message": f"'{src_path.name}' ko {dest_name} me copy kar diya."}
    except PermissionError:
        return {"success": False, "message": f"Permission denied — copy nahi ho paya."}


def _find_item(name: str) -> Path | None:
    """Search known folders for a file/folder by name."""
    for folder_path in USER_FOLDERS.values():
        candidate = folder_path / name
        if candidate.exists():
            return candidate
    # Try glob in each folder
    for folder_path in USER_FOLDERS.values():
        matches = list(folder_path.glob(f"*{name}*"))
        if len(matches) == 1:
            return matches[0]
    return None


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
