"""Paths, settings (config/settings.json) and the secret key."""

from __future__ import annotations

import hashlib
import json
import secrets
from fractions import Fraction
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "config"
SETTINGS_PATH = CONFIG_DIR / "settings.json"
DATA_DIR = REPO_ROOT / "data"
SOURCES_DIR = DATA_DIR / "sources"
PASSAGES_DIR = DATA_DIR / "passages"
WATERMARKED_DIR = DATA_DIR / "watermarked"
MANIFEST_PATH = DATA_DIR / "manifest.csv"
SYNONYMS_PATH = DATA_DIR / "synonyms.tsv"
RESULTS_DIR = REPO_ROOT / "results"
QUALITY_DIR = REPO_ROOT / "quality_checks"
REVIEWS_PATH = QUALITY_DIR / "reviews.csv"


# ---------------------------------------------------------------- settings

def load_settings() -> dict:
    with open(SETTINGS_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_settings(settings: dict) -> None:
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")


def require_frozen(settings: dict) -> None:
    """Stop evaluation scripts from running before settings are fixed."""
    if not settings.get("frozen"):
        raise SystemExit(
            "Settings are not frozen. Finish calibration and run "
            "scripts/freeze_settings.py before touching evaluation passages."
        )


def threshold_of(settings: dict) -> Fraction:
    if settings.get("threshold") is None:
        raise SystemExit("No threshold set in config/settings.json yet.")
    return Fraction(str(settings["threshold"]))


# --------------------------------------------------------------------- key

def key_path(settings: dict | None = None) -> Path:
    settings = settings or load_settings()
    return REPO_ROOT / settings["key_file"]


def generate_key(path: Path) -> bytes:
    if path.exists():
        raise SystemExit(
            f"{path} already exists. The project uses ONE key for the whole "
            "experiment; generating a new one to get nicer scores biases results."
        )
    key = secrets.token_bytes(32)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(key.hex() + "\n", encoding="utf-8")
    return key


def load_key(settings: dict | None = None) -> bytes:
    path = key_path(settings)
    if not path.exists():
        raise SystemExit(f"No key at {path}. Run: python scripts/generate_key.py")
    key = bytes.fromhex(path.read_text(encoding="utf-8").strip())
    if len(key) != 32:
        raise SystemExit(f"Key in {path} is {len(key)} bytes, expected 32.")
    return key


def key_fingerprint(key: bytes) -> str:
    """Short public identifier for the key (safe to put in the report)."""
    return hashlib.sha256(key).hexdigest()[:16]
