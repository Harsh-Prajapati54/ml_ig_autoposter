"""
Central config loader. Reads from a local .env file when present (local
dev) and otherwise falls back to real environment variables (GitHub
Actions secrets are injected as env vars, so this works unchanged there).
"""
import os
from dotenv import load_dotenv

load_dotenv()  # no-op if .env doesn't exist, e.g. inside GitHub Actions


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Copy .env.example to .env and fill it in (or set it as a "
            f"GitHub Actions secret)."
        )
    return value


# Groq
GROQ_API_KEY = _require("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# "drive"     -> generate + save each post to a Google Drive folder for manual upload
# "instagram" -> generate + publish straight to Instagram via the Graph API
# Switch this (no code changes needed) once your IG Business account is linked.
PUBLISH_MODE = os.getenv("PUBLISH_MODE", "drive").lower()
if PUBLISH_MODE not in ("drive", "instagram"):
    raise RuntimeError("PUBLISH_MODE must be 'drive' or 'instagram'")

# Instagram Graph API — only required when PUBLISH_MODE=instagram
if PUBLISH_MODE == "instagram":
    IG_ACCESS_TOKEN = _require("IG_ACCESS_TOKEN")
    IG_USER_ID = _require("IG_USER_ID")
else:
    IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")
    IG_USER_ID = os.getenv("IG_USER_ID")
GRAPH_API_VERSION = os.getenv("GRAPH_API_VERSION", "v21.0")
GRAPH_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

# Google Drive — only required when PUBLISH_MODE=drive. See authorize_drive.py
# for how to obtain a refresh token.
if PUBLISH_MODE == "drive":
    GOOGLE_CLIENT_ID = _require("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = _require("GOOGLE_CLIENT_SECRET")
    GOOGLE_REFRESH_TOKEN = _require("GOOGLE_REFRESH_TOKEN")
else:
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN")
# Optional: a Drive folder ID to nest all post-folders inside. Leave unset to
# create them at the root of "My Drive".
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID") or None

# GitHub image hosting
GITHUB_TOKEN = _require("GITHUB_TOKEN")
GITHUB_OWNER = _require("GITHUB_OWNER")
GITHUB_REPO = _require("GITHUB_REPO")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

# Local paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(BASE_DIR, "assets", "fonts")
OUTPUT_DIR = os.path.join(BASE_DIR, "generated")
DATA_DIR = os.path.join(BASE_DIR, "data")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Brand / account handle shown on the generated image cards
IG_HANDLE = os.getenv("IG_HANDLE", "@your.handle")
