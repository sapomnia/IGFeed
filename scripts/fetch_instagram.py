#!/usr/bin/env python3
"""
Scarica gli ultimi post Instagram via Instagram Graph API (graph.instagram.com),
estrae l'URL posto dopo il marcatore 🔗 in fondo alla caption, salva le immagini
nella cartella images/ e genera feed.json.

Variabili d'ambiente richieste:
  INSTAGRAM_TOKEN   long-lived user token (permesso instagram_basic)

Opzionali:
  IG_API_VERSION    default "v21.0"
  IG_MAX_POSTS      default 24
  IG_LINK_MARKER    default "🔗"
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = ROOT / "images"
FEED_PATH = ROOT / "feed.json"

API_VERSION = os.environ.get("IG_API_VERSION", "v21.0")
MAX_POSTS = int(os.environ.get("IG_MAX_POSTS", "24"))
LINK_MARKER = os.environ.get("IG_LINK_MARKER", "🔗")

FIELDS = "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp"

URL_RE = re.compile(r"https?://\S+")


def log(msg: str) -> None:
    print(msg, flush=True)


def die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


def get_token() -> str:
    token = os.environ.get("INSTAGRAM_TOKEN")
    if not token:
        die("INSTAGRAM_TOKEN non impostato")
    return token


def fetch_media(token: str) -> list[dict]:
    """Scarica i metadati degli ultimi MAX_POSTS post."""
    url = f"https://graph.instagram.com/{API_VERSION}/me/media"
    params = {
        "fields": FIELDS,
        "limit": MAX_POSTS,
        "access_token": token,
    }
    r = requests.get(url, params=params, timeout=30)
    if r.status_code != 200:
        die(f"Instagram API error {r.status_code}: {r.text}")
    data = r.json().get("data", [])
    return data[:MAX_POSTS]


def extract_link(caption: str | None) -> str | None:
    """Trova il primo URL http(s) che segue il marcatore 🔗 nella caption."""
    if not caption:
        return None
    idx = caption.rfind(LINK_MARKER)
    if idx == -1:
        return None
    tail = caption[idx + len(LINK_MARKER):]
    m = URL_RE.search(tail)
    if not m:
        return None
    return m.group(0).rstrip(".,;)]}'\"")


def caption_without_link(caption: str | None) -> str:
    """Rimuove il blocco marcatore + URL dalla caption per mostrarla pulita."""
    if not caption:
        return ""
    idx = caption.rfind(LINK_MARKER)
    if idx == -1:
        return caption.strip()
    return caption[:idx].strip()


def pick_image_url(post: dict) -> str | None:
    """Per VIDEO usa thumbnail_url, per IMAGE/CAROUSEL_ALBUM usa media_url."""
    mtype = post.get("media_type")
    if mtype == "VIDEO":
        return post.get("thumbnail_url") or post.get("media_url")
    return post.get("media_url")


def guess_ext(url: str, content_type: str | None) -> str:
    if content_type:
        ct = content_type.lower()
        if "jpeg" in ct or "jpg" in ct:
            return ".jpg"
        if "png" in ct:
            return ".png"
        if "webp" in ct:
            return ".webp"
        if "gif" in ct:
            return ".gif"
    path = urlparse(url).path.lower()
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        if path.endswith(ext):
            return ".jpeg" if ext == ".jpeg" else ext
    return ".jpg"


def download_image(url: str, dest_stem: Path) -> Path | None:
    """Scarica un'immagine se non esiste già su disco. Ritorna il path locale."""
    # Se esiste già un file con qualsiasi estensione nota, riusalo
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        existing = dest_stem.with_suffix(ext)
        if existing.exists():
            return existing

    try:
        r = requests.get(url, timeout=60, stream=True)
        r.raise_for_status()
        ext = guess_ext(url, r.headers.get("Content-Type"))
        dest = dest_stem.with_suffix(ext)
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return dest
    except Exception as e:
        log(f"  ! download fallito: {e}")
        return None


def main() -> int:
    token = get_token()
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    log(f"Fetching up to {MAX_POSTS} posts from Instagram…")
    posts = fetch_media(token)
    log(f"Ricevuti {len(posts)} post")

    feed: list[dict] = []
    kept_files: set[str] = set()

    for post in posts:
        pid = post.get("id")
        link = extract_link(post.get("caption"))
        if not link:
            log(f"  - {pid}: nessun 🔗 nella caption, skip")
            continue

        img_url = pick_image_url(post)
        if not img_url:
            log(f"  - {pid}: nessuna immagine disponibile, skip")
            continue

        stem = IMAGES_DIR / str(pid)
        local = download_image(img_url, stem)
        if not local:
            log(f"  - {pid}: download fallito, skip")
            continue

        rel = local.relative_to(ROOT).as_posix()
        kept_files.add(local.name)

        feed.append({
            "id": pid,
            "caption": caption_without_link(post.get("caption")),
            "url": link,
            "image": rel,
            "permalink": post.get("permalink"),
            "timestamp": post.get("timestamp"),
            "media_type": post.get("media_type"),
        })
        log(f"  + {pid}: {link}")

    # Scrivi feed.json (ordinato dal più recente — l'API già lo fa)
    FEED_PATH.write_text(
        json.dumps({"updated_at": posts[0].get("timestamp") if posts else None,
                    "count": len(feed),
                    "items": feed}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log(f"Scritto {FEED_PATH.relative_to(ROOT)} con {len(feed)} item")

    # Pulizia immagini orfane
    removed = 0
    for f in IMAGES_DIR.iterdir():
        if f.is_file() and f.name not in kept_files and not f.name.startswith("."):
            f.unlink()
            removed += 1
    if removed:
        log(f"Rimosse {removed} immagini orfane")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
