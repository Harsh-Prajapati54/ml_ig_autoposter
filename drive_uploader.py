"""
Uploads generated post assets (images + caption) to a dated Google Drive
folder, for the interim period before Instagram is linked — you open the
folder, grab everything, and post manually.

Auth: uses a pre-authorized OAuth refresh token (see authorize_drive.py for
the one-time setup). Scope used is drive.file — non-sensitive, so it needs
no Google verification review.
"""
import os
import json
import mimetypes
import time
import requests

import config

TOKEN_URL = "https://oauth2.googleapis.com/token"
DRIVE_API = "https://www.googleapis.com/drive/v3"
DRIVE_UPLOAD_API = "https://www.googleapis.com/upload/drive/v3/files"

_token_cache = {"access_token": None, "expires_at": 0}


def _get_access_token() -> str:
    if _token_cache["access_token"] and time.time() < _token_cache["expires_at"] - 30:
        return _token_cache["access_token"]

    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id": config.GOOGLE_CLIENT_ID,
            "client_secret": config.GOOGLE_CLIENT_SECRET,
            "refresh_token": config.GOOGLE_REFRESH_TOKEN,
            "grant_type": "refresh_token",
        },
    )
    if not resp.ok:
        raise RuntimeError(
            f"Google token refresh failed ({resp.status_code}): {resp.text}\n"
            f"If this says invalid_grant, your refresh token likely expired — "
            f"re-run authorize_drive.py, and make sure the OAuth consent screen "
            f"is set to 'In production' in Google Cloud Console."
        )
    data = resp.json()
    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + data.get("expires_in", 3600)
    return data["access_token"]


def _auth_header() -> dict:
    return {"Authorization": f"Bearer {_get_access_token()}"}


def create_folder(name: str, parent_id: str = None) -> dict:
    metadata = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        metadata["parents"] = [parent_id]

    resp = requests.post(
        f"{DRIVE_API}/files",
        params={"fields": "id,webViewLink"},
        headers={**_auth_header(), "Content-Type": "application/json"},
        data=json.dumps(metadata),
    )
    resp.raise_for_status()
    return resp.json()


def upload_file(local_path: str, parent_id: str, name: str = None) -> dict:
    name = name or os.path.basename(local_path)
    mime_type, _ = mimetypes.guess_type(local_path)
    mime_type = mime_type or "application/octet-stream"
    metadata = {"name": name, "parents": [parent_id]}

    with open(local_path, "rb") as f:
        files = {
            "metadata": (None, json.dumps(metadata), "application/json"),
            "file": (name, f, mime_type),
        }
        resp = requests.post(
            DRIVE_UPLOAD_API,
            params={"uploadType": "multipart", "fields": "id,webViewLink"},
            headers=_auth_header(),
            files=files,
        )
    resp.raise_for_status()
    return resp.json()

def upload_post(post_dir: str, folder_name: str) -> str:
    """
    Creates a folder in Google Drive and uploads every file 
    found inside the local post_dir to it.
    """
    # Create the folder in Google Drive
    folder = create_folder(folder_name, parent_id=config.GOOGLE_DRIVE_FOLDER_ID)
    folder_id = folder["id"]

    # Sweep through the local folder and upload everything (images + caption.txt)
    for filename in sorted(os.listdir(post_dir)):
        file_path = os.path.join(post_dir, filename)
        if os.path.isfile(file_path):
            upload_file(file_path, folder_id, name=filename)

    return folder.get("webViewLink") or f"https://drive.google.com/drive/folders/{folder_id}"