"""
Orchestrates one full posting run:

  pick topic -> generate content (Groq) -> render image(s) (Pillow)
  -> save to local folder -> host image(s) publicly (GitHub) -> publish (Instagram Graph API)
  -> log the result (GitHub)

Usage:
    python main.py              # generates AND publishes
    python main.py --dry-run    # generates + saves locally, skips posting
"""
import argparse
import sys
import time
import traceback
import os

import config
import content_generator
import drive_uploader
import github_host
import image_generator
import instagram_publisher
import topics

LOG_PATH = "data/posts_log.json"


def log_result(entry: dict) -> None:
    history = github_host.download_json(LOG_PATH) or {"posts": []}
    history["posts"].append(entry)
    github_host.upload_json(LOG_PATH, history, message="chore: log post result")


def run(dry_run: bool = False) -> None:
    topic = topics.pick_topic()
    print(f"[1/4] Topic: {topic}")

    content = content_generator.generate_with_retry(topic)
    print(f"[2/4] Format: {content['format']} | Title: {content['title']}")

    # Render images and get the local folder details
    post_data = image_generator.render_post(content, handle=config.IG_HANDLE)
    post_dir = post_data["post_dir"]
    folder_name = post_data["folder_name"]
    print(f"[3/4] Rendered assets to local folder: {post_dir}")

    full_caption = content["caption"] + "\n\n" + " ".join(content["hashtags"])

    if dry_run:
        print(f"[dry-run] Skipping {config.PUBLISH_MODE} step.")
        print(f"Caption:\n{content['caption']}\n")
        print(f"Hashtags: {' '.join(content['hashtags'])}")
        return

    if config.PUBLISH_MODE == "drive":
        # New Drive Logic: Pass the local directory and folder name
        folder_link = drive_uploader.upload_post(post_dir, folder_name)
        print(f"[4/4] Saved to Drive: {folder_link}")
        result = {"status": "saved_to_drive", "drive_link": folder_link}

    else:  # config.PUBLISH_MODE == "instagram"
        # Extract just the PNG files from the new local folder in order
        image_files = sorted([f for f in os.listdir(post_dir) if f.endswith(".png")])
        image_paths = [os.path.join(post_dir, f) for f in image_files]
        
        image_urls = [github_host.upload_image(p) for p in image_paths]
        
        if content["format"] == "single":
            media_id = instagram_publisher.publish_single(image_urls[0], full_caption)
        else:
            media_id = instagram_publisher.publish_carousel(image_urls, full_caption)
            
        print(f"[4/4] Published to Instagram! media_id={media_id}")
        result = {"status": "published", "media_id": media_id}

    log_result(
        {
            "timestamp": int(time.time()),
            "topic": topic,
            "format": content["format"],
            "title": content["title"],
            **result,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Generate content/images without posting")
    args = parser.parse_args()

    try:
        run(dry_run=args.dry_run)
    except Exception:
        print("Run failed:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)