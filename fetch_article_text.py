#!/usr/bin/env python3
import json
import os
import re
from urllib.parse import urlparse
from datetime import date

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

try:
    from readability import Document
except Exception:
    Document = None  # readability-lxml not installed or broken

load_dotenv()

FETCH_ARTICLE_BODY = os.getenv("FETCH_ARTICLE_BODY", "false").lower() == "true"
BODY_FETCH_MAX = int(os.getenv("BODY_FETCH_MAX", "5"))
BODY_MODE = os.getenv("BODY_MODE", "ogp_only").strip()
TIMEOUT = int(os.getenv("REQUEST_TIMEOUT_SEC", "15"))
UA = os.getenv("USER_AGENT", "hn-digest-bot/1.0")
ALLOW = [d.strip() for d in os.getenv("ALLOW_DOMAINS", "").split(",") if d.strip()]
DENY = [d.strip() for d in os.getenv("DENY_DOMAINS", "").split(",") if d.strip()]
MAX_CHARS = int(os.getenv("MAX_SOURCE_CHARS", "12000"))

HN_COMMENTS_MAX = int(os.getenv("HN_COMMENTS_MAX", "15"))  # 0で無効

headers = {"User-Agent": UA}


def domain_of(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower().replace("www.", "")
    except Exception:
        return ""


def allowed_domain(domain: str) -> bool:
    if domain in DENY:
        return False
    if ALLOW:
        return domain in ALLOW
    return True


def extract_ogp_description(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    # Prefer og:description, then meta description
    for sel in [
        ("meta", {"property": "og:description"}),
        ("meta", {"name": "description"}),
        ("meta", {"property": "twitter:description"}),
    ]:
        tag = soup.find(*sel)
        if tag and tag.get("content"):
            return tag["content"].strip()
    return ""


def extract_readable_text(html: str) -> str:
    if Document is None:
        return ""
    doc = Document(html)
    content_html = doc.summary(html_partial=True)
    soup = BeautifulSoup(content_html, "lxml")
    text = soup.get_text("\n")
    # Normalize whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def fetch(url: str) -> str:
    r = requests.get(url, headers=headers, timeout=TIMEOUT)
    r.raise_for_status()
    # Respect encoding if provided
    r.encoding = r.apparent_encoding
    return r.text


def fetch_hn_comments_via_algolia(story_id: str, max_comments: int) -> list[str]:
    """
    Algolia HN Search API: comments of story X
    GET /api/v1/search?tags=comment,story_<id>&hitsPerPage=<n>
    comment_text is HTML.
    """
    if not story_id or max_comments <= 0:
        return []
    api = f"https://hn.algolia.com/api/v1/search?tags=comment,story_{story_id}&hitsPerPage={max_comments}"
    r = requests.get(api, headers=headers, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    hits = data.get("hits", [])
    texts: list[str] = []
    for h in hits:
        t = h.get("comment_text") or ""
        if not t:
            continue
        soup = BeautifulSoup(t, "lxml")
        txt = soup.get_text("\n").strip()
        if txt:
            texts.append(txt[:3000])
    return texts


def main() -> None:
    # Load HN list
    with open("data/hn.json", encoding="utf-8") as f:
        hn = json.load(f)
    items = hn["items"]

    fetched_body = 0
    for it in items:
        it["body_source"] = "none"
        it["source_text"] = ""
        it["domain"] = domain_of(it.get("url") or "")

        # ---- HN comments (always independent of article body fetching) ----
        it["comment_texts"] = []
        it["comment_count_fetched"] = 0
        if HN_COMMENTS_MAX > 0:
            try:
                story_id = str(it.get("hn_id") or "")
                c = fetch_hn_comments_via_algolia(story_id, HN_COMMENTS_MAX)
                it["comment_texts"] = c
                it["comment_count_fetched"] = len(c)
            except Exception as e:
                it["comment_texts"] = []
                it["comment_count_fetched"] = 0
                it["comment_fetch_error"] = type(e).__name__

        # ---- Article body / meta ----
        url = it.get("url") or ""
        if not url:
            it["body_source"] = "no_url"
            continue

        d = it.get("domain", "")

        if not FETCH_ARTICLE_BODY:
            it["body_source"] = "disabled"
            continue
        if fetched_body >= BODY_FETCH_MAX:
            it["body_source"] = "limit_reached"
            continue
        if not allowed_domain(d):
            it["body_source"] = "domain_blocked"
            continue

        try:
            html = fetch(url)
            if BODY_MODE == "readability":
                text = extract_readable_text(html)
                src = "readability"
            else:
                text = extract_ogp_description(html)
                src = "ogp_only"

            text = (text or "").strip()
            if text:
                it["source_text"] = text[:MAX_CHARS]
                it["body_source"] = src
                fetched_body += 1
            else:
                it["body_source"] = "no_text"
        except Exception as e:
            it["body_source"] = f"error:{type(e).__name__}"

    os.makedirs("data", exist_ok=True)
    out_path = "data/hn_with_text.json"
    hn["date"] = hn.get("date") or date.today().isoformat()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(hn, f, ensure_ascii=False, indent=2)

    print(f"Wrote -> {out_path} (fetched_body={fetched_body}, mode={BODY_MODE}, comments_max={HN_COMMENTS_MAX})")


if __name__ == "__main__":
    main()
