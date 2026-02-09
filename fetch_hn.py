#!/usr/bin/env python3
import json
import os
from datetime import date

import requests
from dotenv import load_dotenv

load_dotenv()

HN_TOP_N = int(os.getenv("HN_TOP_N", "20"))
TIMEOUT = int(os.getenv("REQUEST_TIMEOUT_SEC", "15"))
URL = f"https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage={HN_TOP_N}"
CACHE_PATH = "data/hn.json"

def load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def save_cache(payload):
    os.makedirs("data", exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def main() -> None:
    try:
        r = requests.get(URL, timeout=TIMEOUT)
        r.raise_for_status()
        payload = r.json()

        hits = payload.get("hits", [])
        items = []
        for h in hits:
            items.append({
                "hn_id": str(h.get("objectID", "")),
                "title": h.get("title") or h.get("story_title") or "",
                "url": h.get("url") or h.get("story_url") or "",
                "points": h.get("points"),
                "comments": h.get("num_comments"),
            })

        out = {"date": date.today().isoformat(), "items": items}
        save_cache(out)
        print(f"Wrote {len(items)} items -> {CACHE_PATH}")
        return

    except Exception as e:
        cached = load_cache()
        if cached:
            print(f"[WARN] Fetch failed ({type(e).__name__}). Using cached {CACHE_PATH}")
            return
        raise

if __name__ == "__main__":
    main()
