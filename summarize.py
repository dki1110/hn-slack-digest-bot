#!/usr/bin/env python3
"""Per-item codex exec wrapper.

Reads data/hn_with_text.json, calls codex exec once per item,
merges results into data/summaries.json.
"""
import glob
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

CODEX_RETRY_MAX = int(os.getenv("CODEX_RETRY_MAX", "2"))
CODEX_TIMEOUT = int(os.getenv("CODEX_TIMEOUT", "300"))  # 5 minutes
PROMPT_LANG = os.getenv("PROMPT_LANG", "en")
PROMPT_FILE = os.getenv("PROMPT_FILE", f"prompts/{PROMPT_LANG}.txt")

DATA_DIR = Path("data")
PARTS_DIR = DATA_DIR / "_summaries_parts"
SCHEMA_FILE = Path("schema.json")
OUTPUT_FILE = DATA_DIR / "summaries.json"


def load_prompt() -> str:
    with open(PROMPT_FILE, encoding="utf-8") as f:
        return f.read()


def make_single_item_input(item: dict, idx: int, hn_meta: dict) -> Path:
    """Create a temp input JSON containing only one item."""
    single = {
        "date": hn_meta.get("date", ""),
        "items": [item],
    }
    path = DATA_DIR / f"_batch_input_{idx:03d}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(single, f, ensure_ascii=False, indent=2)
    return path


def run_codex_for_item(prompt: str, input_path: Path, output_path: Path) -> dict | None:
    """Run codex exec for a single item. Returns parsed JSON or None."""
    modified_prompt = prompt.replace("data/hn_with_text.json", str(input_path))

    for attempt in range(1, CODEX_RETRY_MAX + 1):
        try:
            result = subprocess.run(
                [
                    "codex", "exec", modified_prompt,
                    "--output-schema", str(SCHEMA_FILE),
                    "-o", str(output_path),
                    "--full-auto",
                ],
                capture_output=True,
                text=True,
                timeout=CODEX_TIMEOUT,
            )
            if result.returncode == 0 and output_path.exists():
                with open(output_path, encoding="utf-8") as f:
                    return json.load(f)
            print(
                f"  [attempt {attempt}/{CODEX_RETRY_MAX}] codex exec failed "
                f"(rc={result.returncode})",
                file=sys.stderr,
            )
            if result.stderr:
                print(f"    stderr: {result.stderr[:500]}", file=sys.stderr)
        except subprocess.TimeoutExpired:
            print(
                f"  [attempt {attempt}/{CODEX_RETRY_MAX}] codex exec timed out "
                f"({CODEX_TIMEOUT}s)",
                file=sys.stderr,
            )
        except Exception as e:
            print(
                f"  [attempt {attempt}/{CODEX_RETRY_MAX}] error: {e}",
                file=sys.stderr,
            )

    return None


def merge_results(parts: list[dict], date_str: str, lang: str) -> dict:
    """Merge individual codex results into final summaries.json."""
    all_items = []
    for part in parts:
        if part and "items" in part:
            all_items.extend(part["items"])
    return {"date": date_str, "lang": lang, "items": all_items}


def cleanup_temp_files() -> None:
    for f in glob.glob(str(DATA_DIR / "_batch_input_*.json")):
        os.remove(f)


def main() -> None:
    with open(DATA_DIR / "hn_with_text.json", encoding="utf-8") as f:
        hn = json.load(f)

    items = hn.get("items", [])
    date_str = hn.get("date", "")
    prompt = load_prompt()
    lang = "ja" if "ja" in PROMPT_LANG else "en"

    PARTS_DIR.mkdir(parents=True, exist_ok=True)

    parts: list[dict] = []
    for idx, item in enumerate(items):
        num = idx + 1
        hn_id = item.get("hn_id", "?")
        title = (item.get("title") or "(no title)")[:60]
        print(f"[summarize] {num}/{len(items)}: {hn_id} – {title}")

        input_path = make_single_item_input(item, num, hn)
        output_path = PARTS_DIR / f"part_{num:03d}.json"

        result = run_codex_for_item(prompt, input_path, output_path)
        if result:
            parts.append(result)
            print(f"  -> OK")
        else:
            print(f"  -> SKIPPED (all retries failed)", file=sys.stderr)

    merged = merge_results(parts, date_str, lang)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    print(f"[summarize] Wrote {OUTPUT_FILE} ({len(merged['items'])} items)")

    cleanup_temp_files()


if __name__ == "__main__":
    main()
