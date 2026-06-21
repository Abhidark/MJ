"""
Archivist Module -- File Management & Organization
"""

import re
import os
from pathlib import Path
from modules.base_module import BaseModule


class ArchivistModule(BaseModule):
    name = "archivist"
    display_name = "Archivist"
    icon = "\U0001f4c2"
    description = "File operations: search, list, organize, and manage files"
    version = "1.0"
    category = "utility"
    enabled = True

    KEYWORDS = [
        "find file", "list files", "file search", "folder",
        "organize", "search file", "directory", "files in",
        "show files", "what files", "list folder", "browse",
        "file manager", "open folder",
    ]

    def __init__(self):
        self.default_directory = str(Path.home() / "Desktop")

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        lower = text.lower()

        for kw in self.KEYWORDS:
            if kw in lower:
                return 0.9

        if intent in ("file_management", "file_search", "directory_listing"):
            return 0.85

        if re.search(r"\.(txt|pdf|docx|xlsx|py|jpg|png|mp4|zip)\b", lower):
            if re.search(r"\b(find|search|where|locate|list)\b", lower):
                return 0.8

        return 0.0

    def execute(self, text: str, context: dict) -> dict:
        lower = text.lower()

        if "find" in lower or "search" in lower or "locate" in lower:
            return self._search_files(text)
        elif "list" in lower or "show" in lower or "browse" in lower:
            return self._list_files(text)
        elif "organize" in lower:
            return self._organize_info(text)
        else:
            return self._list_files(text)

    def _extract_directory(self, text: str) -> str:
        """Extract a directory path from text, or use the default."""
        # Look for explicit paths (Windows or Unix style)
        match = re.search(r'["\']?([a-zA-Z]:\\[^\s"\']+|~/[^\s"\']+|/[^\s"\']+)["\']?', text)
        if match:
            path = match.group(1)
            expanded = os.path.expanduser(path)
            if os.path.isdir(expanded):
                return expanded

        # Look for common folder names
        folder_map = {
            "desktop": str(Path.home() / "Desktop"),
            "downloads": str(Path.home() / "Downloads"),
            "documents": str(Path.home() / "Documents"),
            "pictures": str(Path.home() / "Pictures"),
            "music": str(Path.home() / "Music"),
            "videos": str(Path.home() / "Videos"),
        }
        lower = text.lower()
        for name, path in folder_map.items():
            if name in lower and os.path.isdir(path):
                return path

        return self.default_directory

    def _extract_search_term(self, text: str) -> str | None:
        """Extract what the user is searching for."""
        # "find file named X", "search for X", "find X files"
        patterns = [
            r'(?:find|search|locate)\s+(?:file\s+)?(?:named?\s+)?["\']?(\S+)["\']?',
            r'(?:find|search)\s+(?:for\s+)?["\']?(.+?)["\']?\s*(?:in|on|$)',
            r'\*\.(\w+)\b',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _list_files(self, text: str) -> dict:
        """List files in a directory."""
        directory = self._extract_directory(text)

        if not os.path.isdir(directory):
            return {
                "response": f"Directory not found: {directory}",
                "data": None,
                "action": "error",
            }

        try:
            entries = []
            for item in sorted(Path(directory).iterdir()):
                entry = {
                    "name": item.name,
                    "type": "folder" if item.is_dir() else "file",
                }
                if item.is_file():
                    try:
                        entry["size_bytes"] = item.stat().st_size
                        size = entry["size_bytes"]
                        if size >= 1_048_576:
                            entry["size"] = f"{size / 1_048_576:.1f} MB"
                        elif size >= 1024:
                            entry["size"] = f"{size / 1024:.1f} KB"
                        else:
                            entry["size"] = f"{size} B"
                    except OSError:
                        entry["size"] = "?"
                    entry["extension"] = item.suffix
                entries.append(entry)

            # Limit output
            total = len(entries)
            display = entries[:50]

            lines = [f"Contents of: {directory} ({total} items)"]
            for e in display:
                icon = "\U0001f4c1" if e["type"] == "folder" else "\U0001f4c4"
                size_str = f" ({e.get('size', '')})" if e.get("size") else ""
                lines.append(f"  {icon} {e['name']}{size_str}")

            if total > 50:
                lines.append(f"  ... and {total - 50} more items")

            return {
                "response": "\n".join(lines),
                "data": {"directory": directory, "entries": display, "total": total},
                "action": "list_files",
            }

        except PermissionError:
            return {
                "response": f"Permission denied: {directory}",
                "data": None,
                "action": "error",
            }

    def _search_files(self, text: str) -> dict:
        """Search for files by name or extension."""
        directory = self._extract_directory(text)
        search_term = self._extract_search_term(text)

        if not search_term:
            return {
                "response": "What should I search for? Provide a filename or extension (e.g., '.pdf', 'report').",
                "data": None,
                "action": "need_input",
            }

        if not os.path.isdir(directory):
            return {
                "response": f"Directory not found: {directory}",
                "data": None,
                "action": "error",
            }

        results = []
        search_lower = search_term.lower()

        try:
            for root, dirs, files in os.walk(directory):
                # Skip hidden/system directories
                dirs[:] = [d for d in dirs if not d.startswith((".", "_"))]
                for fname in files:
                    if search_lower in fname.lower():
                        full_path = os.path.join(root, fname)
                        results.append({
                            "name": fname,
                            "path": full_path,
                            "directory": root,
                        })
                        if len(results) >= 50:
                            break
                if len(results) >= 50:
                    break

        except PermissionError:
            pass

        if results:
            lines = [f"Found {len(results)} file(s) matching '{search_term}' in {directory}:"]
            for r in results:
                lines.append(f"  \U0001f4c4 {r['name']}  ({r['directory']})")
            response = "\n".join(lines)
        else:
            response = f"No files matching '{search_term}' found in {directory}."

        return {
            "response": response,
            "data": {"search_term": search_term, "directory": directory, "results": results},
            "action": "file_search",
        }

    def _organize_info(self, text: str) -> dict:
        """Provide file organization advice."""
        return {
            "response": (
                "File Organization Tips:\n"
                "  1. Group files by type (documents, images, code, etc.)\n"
                "  2. Use date-based folders for projects (YYYY-MM format)\n"
                "  3. Archive old files you don't access regularly\n"
                "  4. Keep your Desktop clean -- move files to proper folders\n"
                "  5. Use consistent naming: lowercase, hyphens, no spaces"
            ),
            "data": None,
            "action": "organize_tips",
        }

    def get_system_prompt_addition(self) -> str:
        return (
            "You can list files, search by name or extension, "
            "and help organize the user's files and folders."
        )

    def get_context_for_llm(self, text: str, context: dict) -> str:
        return "[Archivist File Module] User is asking about files or directories."

    def get_settings(self) -> dict:
        return {
            "enabled": self.enabled,
            "default_directory": self.default_directory,
        }

    def update_settings(self, settings: dict):
        if "enabled" in settings:
            self.enabled = settings["enabled"]
        if "default_directory" in settings:
            path = settings["default_directory"]
            if os.path.isdir(path):
                self.default_directory = path

    def get_settings_schema(self) -> list:
        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled},
            {
                "key": "default_directory",
                "label": "Default Directory",
                "type": "text",
                "value": self.default_directory,
            },
        ]
