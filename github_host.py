"""
Uses a public GitHub repo as free, publicly-reachable file hosting.

Why: the Instagram Graph API's content publishing endpoints require a
public `image_url` — they do not accept raw binary uploads for photos.
Since the images are generated fresh on every run anyway, committing them
straight to a public GitHub repo via the Contents API and serving them
from raw.githubusercontent.com is a free, zero-infra way to satisfy that
requirement. The same mechanism is reused to persist small JSON state
files (used topics, post history) across GitHub Actions runs.
"""
import base64
import time

import requests

import config

API_BASE = f"https://api.github.com/repos/{config.GITHUB_OWNER}/{config.GITHUB_REPO}/contents"
HEADERS = {
    "Authorization": f"Bearer {config.GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def _get_sha(path: str):
    """Return the current blob sha for a file, or None if it doesn't exist."""
    resp = requests.get(f"{API_BASE}/{path}", headers=HEADERS, params={"ref": config.GITHUB_BRANCH})
    if resp.status_code == 200:
        return resp.json()["sha"]
    return None


def upload_bytes(path: str, data: bytes, message: str) -> str:
    """
    Create or update a file in the repo. Returns a public raw URL for it.
    """
    payload = {
        "message": message,
        "content": base64.b64encode(data).decode("utf-8"),
        "branch": config.GITHUB_BRANCH,
    }
    sha = _get_sha(path)
    if sha:
        payload["sha"] = sha

    resp = requests.put(f"{API_BASE}/{path}", headers=HEADERS, json=payload)
    resp.raise_for_status()
    return resp.json()["content"]["download_url"]


def upload_image(local_path: str, repo_subdir: str = "posts") -> str:
    """Upload a local PNG and return its public raw.githubusercontent.com URL."""
    filename = f"{repo_subdir}/{int(time.time())}_{local_path.split('/')[-1]}"
    with open(local_path, "rb") as f:
        data = f.read()
    url = upload_bytes(filename, data, message=f"post: add {filename}")

    # Give GitHub's CDN a moment to make the file fetchable before Instagram
    # tries to download it.
    time.sleep(4)
    return url


def download_json(path: str):
    """Return parsed JSON content of a repo file, or None if missing."""
    resp = requests.get(f"{API_BASE}/{path}", headers=HEADERS, params={"ref": config.GITHUB_BRANCH})
    if resp.status_code != 200:
        return None
    content = base64.b64decode(resp.json()["content"]).decode("utf-8")
    import json
    return json.loads(content)


def upload_json(path: str, obj: dict, message: str) -> str:
    import json
    data = json.dumps(obj, indent=2).encode("utf-8")
    return upload_bytes(path, data, message=message)
