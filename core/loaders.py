# ============================================================
# core/loaders.py
# ------------------------------------------------------------
# Helpers για φόρτωση/αποθήκευση JSON και JS data files.
#
# Χρήση:
#     from core.loaders import load_json, save_json, load_js_data
# ============================================================

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


# ============================================================
# JSON
# ============================================================
def load_json(path: Path | str) -> Any:
    """Φορτώνει JSON από αρχείο (utf-8)."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"JSON not found: {p}")
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path | str, data: Any, indent: int = 2) -> None:
    """Αποθηκεύει JSON με ensure_ascii=False (ελληνικά σωστά)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


# ============================================================
# JS DATA FILES
# ------------------------------------------------------------
# Μορφή:
#     const VAR = {...};
#     // ή
#     var VAR = {...};
#     // ή
#     window.VAR = {...};
# ============================================================

_JS_PATTERN = re.compile(
    r"^\s*(?:const|var|let|window\.)?\s*([A-Za-z_$][\w$]*)\s*=\s*(.+?);?\s*$",
    re.DOTALL,
)


def load_js_data(path: Path | str) -> tuple[str, Any]:
    """
    Φορτώνει JS data file και επιστρέφει (var_name, data).
    Δουλεύει με const/var/let/window.VAR.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"JS file not found: {p}")

    text = p.read_text(encoding="utf-8").strip()
    m = _JS_PATTERN.match(text)
    if not m:
        raise ValueError(f"Cannot parse JS data file: {p}")

    var_name = m.group(1)
    json_str = m.group(2).strip()
    if json_str.endswith(";"):
        json_str = json_str[:-1]

    data = json.loads(json_str)
    return var_name, data


def save_js_data(path: Path | str, var_name: str, data: Any) -> None:
    """
    Αποθηκεύει JS data file στη μορφή:
        const VAR_NAME = {...};
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    text = f"const {var_name} = {body};\n"
    p.write_text(text, encoding="utf-8")


# ============================================================
# PATH HELPERS
# ============================================================
def rel_to_root(path: Path | str) -> str:
    """Επιστρέφει path σχετικό με το ROOT (για logs)."""
    from core.paths import ROOT
    try:
        return str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def describe(path: Path | str) -> str:
    """Γρήγορο description για logs: '<relative> (<size>)'."""
    from core.paths import ROOT
    p = Path(path)
    if not p.exists():
        return f"{rel_to_root(p)} (missing)"
    size = p.stat().st_size
    if size < 1024:
        human = f"{size} B"
    elif size < 1024 * 1024:
        human = f"{size / 1024:.1f} KB"
    else:
        human = f"{size / (1024 * 1024):.1f} MB"
    return f"{rel_to_root(p)} ({human})"
