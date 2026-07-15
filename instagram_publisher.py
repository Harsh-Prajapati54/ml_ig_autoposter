"""
Thin wrapper around the Instagram Graph API's content publishing flow.

Docs: https://developers.facebook.com/docs/instagram-api/guides/content-publishing/

Flow for a single image:
  1. POST /{ig-user-id}/media          -> creates a media container, returns creation_id
  2. POST /{ig-user-id}/media_publish  -> publishes that container

Flow for a carousel:
  1. POST /{ig-user-id}/media (is_carousel_item=true) for each image -> child creation_ids
  2. POST /{ig-user-id}/media (media_type=CAROUSEL, children=[...]) -> parent creation_id
  3. POST /{ig-user-id}/media_publish  -> publishes the carousel container
"""
import time

import requests

import config

BASE = f"{config.GRAPH_BASE_URL}/{config.IG_USER_ID}"


def _post(path: str, params: dict) -> dict:
    resp = requests.post(f"{config.GRAPH_BASE_URL}/{path}", data=params)
    if not resp.ok:
        raise RuntimeError(f"Graph API error {resp.status_code}: {resp.text}")
    return resp.json()


def _get(path: str, params: dict) -> dict:
    resp = requests.get(f"{config.GRAPH_BASE_URL}/{path}", params=params)
    if not resp.ok:
        raise RuntimeError(f"Graph API error {resp.status_code}: {resp.text}")
    return resp.json()


def wait_until_ready(creation_id: str, timeout_s: int = 60) -> None:
    """Poll a container until Meta finishes processing it (usually instant for images)."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        status = _get(creation_id, {"fields": "status_code", "access_token": config.IG_ACCESS_TOKEN})
        code = status.get("status_code")
        if code == "FINISHED":
            return
        if code == "ERROR":
            raise RuntimeError(f"Container {creation_id} failed processing: {status}")
        time.sleep(2)
    # Images are near-instant in practice; don't hard-fail on a slow status field.


def create_image_container(image_url: str, caption: str = None, is_carousel_item: bool = False) -> str:
    params = {"image_url": image_url, "access_token": config.IG_ACCESS_TOKEN}
    if caption:
        params["caption"] = caption
    if is_carousel_item:
        params["is_carousel_item"] = "true"
    result = _post(f"{config.IG_USER_ID}/media", params)
    return result["id"]


def create_carousel_container(child_ids: list, caption: str) -> str:
    params = {
        "media_type": "CAROUSEL",
        "children": ",".join(child_ids),
        "caption": caption,
        "access_token": config.IG_ACCESS_TOKEN,
    }
    result = _post(f"{config.IG_USER_ID}/media", params)
    return result["id"]


def publish_container(creation_id: str) -> str:
    result = _post(
        f"{config.IG_USER_ID}/media_publish",
        {"creation_id": creation_id, "access_token": config.IG_ACCESS_TOKEN},
    )
    return result["id"]


def publish_single(image_url: str, caption: str) -> str:
    creation_id = create_image_container(image_url, caption=caption)
    wait_until_ready(creation_id)
    return publish_container(creation_id)


def publish_carousel(image_urls: list, caption: str) -> str:
    child_ids = [create_image_container(url, is_carousel_item=True) for url in image_urls]
    for cid in child_ids:
        wait_until_ready(cid)
    parent_id = create_carousel_container(child_ids, caption=caption)
    wait_until_ready(parent_id)
    return publish_container(parent_id)
