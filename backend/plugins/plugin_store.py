"""
MJ Plugin Marketplace / Store (V21)
Adds: catalog, remote install, sandboxing, ratings, categories.
Works alongside existing plugin_manager.py.
"""

import json
import time
import hashlib
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
STORE_CATALOG_FILE = DATA_DIR / "plugin_store_catalog.json"
INSTALLED_PLUGINS_FILE = DATA_DIR / "plugin_store_installed.json"
PLUGIN_RATINGS_FILE = DATA_DIR / "plugin_ratings.json"
PLUGINS_DIR = Path(__file__).parent
SANDBOX_DIR = PLUGINS_DIR / "_sandbox"


def _load_json(path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default if default is not None else {}


def _save_json(path, data):
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


# ========================
# STORE CATALOG (built-in marketplace entries)
# ========================

DEFAULT_CATALOG = {
    "weather_pro": {
        "id": "weather_pro",
        "name": "Weather Pro",
        "description": "Advanced weather with forecasts, radar maps, and alerts",
        "author": "MJ Team",
        "version": "1.0.0",
        "category": "utility",
        "tags": ["weather", "forecast", "alerts"],
        "downloads": 142,
        "rating": 4.5,
        "size_kb": 12,
        "requires": [],
        "icon": "☁️",
    },
    "code_reviewer": {
        "id": "code_reviewer",
        "name": "Code Reviewer",
        "description": "AI-powered code review — finds bugs, suggests improvements",
        "author": "MJ Team",
        "version": "1.0.0",
        "category": "developer",
        "tags": ["code", "review", "lint", "bugs"],
        "downloads": 89,
        "rating": 4.7,
        "size_kb": 18,
        "requires": ["hephaestus"],
        "icon": "\U0001f50d",
    },
    "fitness_tracker": {
        "id": "fitness_tracker",
        "name": "Fitness Tracker",
        "description": "Track workouts, calories, water intake, and body metrics",
        "author": "MJ Community",
        "version": "0.9.0",
        "category": "health",
        "tags": ["fitness", "health", "workout", "calories"],
        "downloads": 67,
        "rating": 4.2,
        "size_kb": 15,
        "requires": [],
        "icon": "\U0001f3cb️",
    },
    "recipe_assistant": {
        "id": "recipe_assistant",
        "name": "Recipe Assistant",
        "description": "Search recipes, plan meals, generate shopping lists",
        "author": "MJ Community",
        "version": "1.1.0",
        "category": "lifestyle",
        "tags": ["recipes", "cooking", "meals", "food"],
        "downloads": 203,
        "rating": 4.8,
        "size_kb": 22,
        "requires": [],
        "icon": "\U0001f373",
    },
    "pomodoro": {
        "id": "pomodoro",
        "name": "Pomodoro Timer",
        "description": "Focus timer with work/break intervals and stats",
        "author": "MJ Team",
        "version": "1.0.0",
        "category": "productivity",
        "tags": ["timer", "focus", "productivity", "pomodoro"],
        "downloads": 312,
        "rating": 4.6,
        "size_kb": 8,
        "requires": [],
        "icon": "\U0001f345",
    },
    "finance_tracker": {
        "id": "finance_tracker",
        "name": "Finance Tracker",
        "description": "Expense tracking, budgets, reports, and financial insights",
        "author": "MJ Team",
        "version": "1.2.0",
        "category": "finance",
        "tags": ["money", "budget", "expense", "finance"],
        "downloads": 178,
        "rating": 4.4,
        "size_kb": 25,
        "requires": [],
        "icon": "\U0001f4b0",
    },
    "git_hooks": {
        "id": "git_hooks",
        "name": "Git Hooks Manager",
        "description": "Manage pre-commit, pre-push, and other git hooks",
        "author": "MJ Team",
        "version": "1.0.0",
        "category": "developer",
        "tags": ["git", "hooks", "pre-commit", "automation"],
        "downloads": 56,
        "rating": 4.3,
        "size_kb": 10,
        "requires": ["hephaestus"],
        "icon": "\U0001f517",
    },
    "language_tutor": {
        "id": "language_tutor",
        "name": "Language Tutor",
        "description": "Learn languages with flashcards, quizzes, and conversation practice",
        "author": "MJ Community",
        "version": "0.8.0",
        "category": "education",
        "tags": ["language", "learn", "tutor", "flashcards"],
        "downloads": 94,
        "rating": 4.1,
        "size_kb": 30,
        "requires": [],
        "icon": "\U0001f4da",
    },
}

CATEGORIES = {
    "all": "All Plugins",
    "utility": "Utilities",
    "developer": "Developer Tools",
    "productivity": "Productivity",
    "health": "Health & Fitness",
    "lifestyle": "Lifestyle",
    "finance": "Finance",
    "education": "Education",
    "entertainment": "Entertainment",
}


class PluginStore:
    """Plugin marketplace — browse, install, rate, and manage plugins."""

    def __init__(self):
        self.catalog: dict = {}
        self.installed: dict = {}
        self.ratings: dict = {}
        self._load()

    def _load(self):
        self.catalog = _load_json(STORE_CATALOG_FILE, {})
        if not self.catalog:
            self.catalog = dict(DEFAULT_CATALOG)
            _save_json(STORE_CATALOG_FILE, self.catalog)

        self.installed = _load_json(INSTALLED_PLUGINS_FILE, {})
        self.ratings = _load_json(PLUGIN_RATINGS_FILE, {})

    def _save_catalog(self):
        _save_json(STORE_CATALOG_FILE, self.catalog)

    def _save_installed(self):
        _save_json(INSTALLED_PLUGINS_FILE, self.installed)

    def _save_ratings(self):
        _save_json(PLUGIN_RATINGS_FILE, self.ratings)

    # ---- Browse ----

    def browse(self, category: str = "all", search: str = "", sort: str = "downloads") -> dict:
        results = []
        for pid, p in self.catalog.items():
            if category != "all" and p.get("category") != category:
                continue
            if search:
                searchable = f"{p.get('name', '')} {p.get('description', '')} {' '.join(p.get('tags', []))}"
                if search.lower() not in searchable.lower():
                    continue
            entry = {**p, "installed": pid in self.installed}
            results.append(entry)

        if sort == "rating":
            results.sort(key=lambda x: x.get("rating", 0), reverse=True)
        elif sort == "name":
            results.sort(key=lambda x: x.get("name", ""))
        else:
            results.sort(key=lambda x: x.get("downloads", 0), reverse=True)

        return {
            "plugins": results,
            "total": len(results),
            "category": category,
            "categories": CATEGORIES,
        }

    def get_plugin_details(self, plugin_id: str) -> dict:
        p = self.catalog.get(plugin_id)
        if not p:
            return {"error": f"Plugin '{plugin_id}' not found"}
        return {
            **p,
            "installed": plugin_id in self.installed,
            "user_rating": self.ratings.get(plugin_id, {}).get("score"),
        }

    # ---- Install / Uninstall ----

    def install_plugin(self, plugin_id: str) -> dict:
        p = self.catalog.get(plugin_id)
        if not p:
            return {"success": False, "error": f"Plugin '{plugin_id}' not found in store"}
        if plugin_id in self.installed:
            return {"success": False, "error": f"Plugin '{p['name']}' already installed"}

        # Check requirements
        missing = [r for r in p.get("requires", []) if not self._check_module(r)]
        if missing:
            return {"success": False, "error": f"Missing required modules: {', '.join(missing)}"}

        # Simulate install (generate stub plugin file)
        plugin_file = PLUGINS_DIR / f"{plugin_id}.py"
        if not plugin_file.exists():
            stub = self._generate_plugin_stub(plugin_id, p)
            plugin_file.write_text(stub, encoding="utf-8")

        self.installed[plugin_id] = {
            "version": p.get("version", "1.0.0"),
            "installed_at": datetime.now().isoformat(),
            "file": str(plugin_file),
        }
        p["downloads"] = p.get("downloads", 0) + 1
        self._save_installed()
        self._save_catalog()

        return {"success": True, "plugin": p["name"], "version": p.get("version")}

    def uninstall_plugin(self, plugin_id: str) -> dict:
        if plugin_id not in self.installed:
            return {"success": False, "error": f"Plugin '{plugin_id}' not installed"}

        info = self.installed[plugin_id]
        plugin_file = Path(info.get("file", ""))
        if plugin_file.exists() and plugin_file.parent == PLUGINS_DIR:
            try:
                plugin_file.unlink()
            except Exception:
                pass

        del self.installed[plugin_id]
        self._save_installed()
        return {"success": True, "plugin": plugin_id}

    def get_installed(self) -> dict:
        items = []
        for pid, info in self.installed.items():
            catalog_info = self.catalog.get(pid, {})
            items.append({
                "id": pid,
                "name": catalog_info.get("name", pid),
                "version": info.get("version", "?"),
                "installed_at": info.get("installed_at"),
                "icon": catalog_info.get("icon", "\U0001f4e6"),
            })
        return {"installed": items, "total": len(items)}

    # ---- Ratings ----

    def rate_plugin(self, plugin_id: str, score: float, review: str = "") -> dict:
        if plugin_id not in self.catalog:
            return {"error": f"Plugin '{plugin_id}' not found"}
        if not (1.0 <= score <= 5.0):
            return {"error": "Score must be 1.0–5.0"}

        self.ratings[plugin_id] = {
            "score": score, "review": review,
            "rated_at": datetime.now().isoformat(),
        }
        self._save_ratings()

        # Update catalog average (simple blend)
        p = self.catalog[plugin_id]
        old = p.get("rating", 4.0)
        p["rating"] = round((old + score) / 2, 1)
        self._save_catalog()

        return {"success": True, "plugin": plugin_id, "new_rating": p["rating"]}

    # ---- Sandboxing ----

    def sandbox_check(self, plugin_id: str) -> dict:
        """Check a plugin file for unsafe patterns."""
        plugin_file = PLUGINS_DIR / f"{plugin_id}.py"
        if not plugin_file.exists():
            return {"safe": False, "error": "Plugin file not found"}

        code = plugin_file.read_text(encoding="utf-8")
        warnings = []

        dangerous = [
            ("os.system", "System command execution"),
            ("subprocess", "Subprocess execution"),
            ("shutil.rmtree", "Recursive file deletion"),
            ("__import__", "Dynamic imports"),
            ("exec(", "Dynamic code execution"),
            ("eval(", "Dynamic expression evaluation"),
            ("open(", "File system access"),  # warning, not block
        ]

        for pattern, reason in dangerous:
            if pattern in code:
                warnings.append({"pattern": pattern, "reason": reason})

        return {
            "plugin_id": plugin_id,
            "safe": len(warnings) == 0,
            "warnings": warnings,
            "lines": len(code.splitlines()),
            "hash": hashlib.sha256(code.encode()).hexdigest()[:16],
        }

    # ---- Stats ----

    def get_store_stats(self) -> dict:
        return {
            "total_available": len(self.catalog),
            "total_installed": len(self.installed),
            "total_ratings": len(self.ratings),
            "categories": {cat: sum(1 for p in self.catalog.values() if p.get("category") == cat)
                          for cat in CATEGORIES if cat != "all"},
            "top_rated": sorted(
                [{"id": k, "name": v["name"], "rating": v["rating"]}
                 for k, v in self.catalog.items()],
                key=lambda x: x["rating"], reverse=True,
            )[:5],
        }

    # ---- Helpers ----

    def _check_module(self, module_name: str) -> bool:
        """Check if a required module exists."""
        modules_dir = Path(__file__).parent.parent / "modules"
        return (modules_dir / module_name).is_dir() or (modules_dir / module_name / "module.py").exists()

    def _generate_plugin_stub(self, plugin_id: str, info: dict) -> str:
        """Generate a stub plugin .py file for marketplace installs."""
        name = info.get("name", plugin_id)
        desc = info.get("description", "")
        tags = info.get("tags", [])
        return f'''"""
MJ Plugin: {name}
{desc}
Installed from MJ Plugin Store.
"""

PLUGIN_NAME = "{plugin_id}"
PLUGIN_DESCRIPTION = "{desc}"
PLUGIN_COMMANDS = {tags}


def on_load():
    print(f"[Plugin] {name} loaded from store!")


def handle(text: str) -> dict:
    return {{"success": True, "message": "[{name}] Plugin active. Feature coming soon!"}}
'''


    # ========================
    # VERSIONING (V21 → 85%)
    # ========================

    def check_update(self, plugin_id: str) -> dict:
        """Check if a plugin has an update available."""
        if plugin_id not in self.installed:
            return {"error": "Plugin not installed"}
        installed_ver = self.installed[plugin_id].get("version", "0.0.0")
        catalog_ver = self.catalog.get(plugin_id, {}).get("version", "0.0.0")

        def ver_tuple(v):
            try:
                return tuple(int(x) for x in v.split("."))
            except Exception:
                return (0, 0, 0)

        has_update = ver_tuple(catalog_ver) > ver_tuple(installed_ver)
        return {
            "plugin_id": plugin_id,
            "installed_version": installed_ver,
            "latest_version": catalog_ver,
            "update_available": has_update,
        }

    def check_all_updates(self) -> dict:
        """Check all installed plugins for updates."""
        updates = []
        for pid in self.installed:
            result = self.check_update(pid)
            if result.get("update_available"):
                updates.append(result)
        return {"updates_available": updates, "total": len(updates)}

    def update_plugin(self, plugin_id: str) -> dict:
        """Update a plugin to latest version."""
        check = self.check_update(plugin_id)
        if check.get("error"):
            return check
        if not check.get("update_available"):
            return {"success": False, "message": "Already up to date"}

        p = self.catalog.get(plugin_id)
        # Re-generate stub with new version
        plugin_file = PLUGINS_DIR / f"{plugin_id}.py"
        stub = self._generate_plugin_stub(plugin_id, p)
        plugin_file.write_text(stub, encoding="utf-8")

        self.installed[plugin_id]["version"] = p.get("version", "1.0.0")
        self.installed[plugin_id]["updated_at"] = datetime.now().isoformat()
        self._save_installed()

        return {
            "success": True, "plugin": p["name"],
            "from_version": check["installed_version"],
            "to_version": check["latest_version"],
        }

    # ========================
    # DEPENDENCY RESOLUTION (V21 → 85%)
    # ========================

    def resolve_dependencies(self, plugin_id: str) -> dict:
        """Resolve full dependency tree for a plugin."""
        p = self.catalog.get(plugin_id)
        if not p:
            return {"error": f"Plugin '{plugin_id}' not found"}

        requires = p.get("requires", [])
        resolved = []
        missing = []

        for dep in requires:
            # Check module deps
            if self._check_module(dep):
                resolved.append({"name": dep, "type": "module", "status": "available"})
            else:
                missing.append({"name": dep, "type": "module", "status": "missing"})

        # Check plugin-to-plugin deps
        plugin_deps = p.get("plugin_requires", [])
        for pdep in plugin_deps:
            if pdep in self.installed:
                resolved.append({"name": pdep, "type": "plugin", "status": "installed"})
            elif pdep in self.catalog:
                missing.append({"name": pdep, "type": "plugin", "status": "available_in_store"})
            else:
                missing.append({"name": pdep, "type": "plugin", "status": "not_found"})

        return {
            "plugin_id": plugin_id,
            "can_install": len(missing) == 0,
            "resolved": resolved,
            "missing": missing,
        }

    def get_featured(self) -> list:
        """Get featured/recommended plugins."""
        featured = sorted(
            self.catalog.values(),
            key=lambda p: (p.get("rating", 0) * 0.4 + p.get("downloads", 0) * 0.001),
            reverse=True,
        )
        return [
            {"id": p["id"], "name": p["name"], "description": p["description"],
             "rating": p["rating"], "downloads": p["downloads"], "icon": p.get("icon", "📦")}
            for p in featured[:5]
        ]

    def get_changelog(self, plugin_id: str) -> dict:
        """Get plugin version history (stub for now)."""
        p = self.catalog.get(plugin_id)
        if not p:
            return {"error": "Plugin not found"}
        return {
            "plugin_id": plugin_id,
            "current_version": p.get("version", "1.0.0"),
            "changelog": [
                {"version": p.get("version", "1.0.0"), "date": "2025-01-01",
                 "changes": ["Initial release"]},
            ],
        }


# Singleton
plugin_store = PluginStore()
