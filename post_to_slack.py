#!/usr/bin/env python3
import json
import os
import sys
import time
import requests
from dotenv import load_dotenv

load_dotenv()
WEBHOOK = os.getenv("SLACK_WEBHOOK_URL", "").strip()
TIMEOUT = int(os.getenv("REQUEST_TIMEOUT_SEC", "15"))
SLACK_POST_DELAY = float(os.getenv("SLACK_POST_DELAY", "1"))

def post_one(payload: dict) -> None:
    r = requests.post(WEBHOOK, json=payload, timeout=TIMEOUT)
    if r.status_code >= 400:
        raise SystemExit(f"Slack webhook failed: {r.status_code} {r.text}")

def main() -> None:
    if not WEBHOOK:
        print("SLACK_WEBHOOK_URL is not set. Skipping post.")
        return
    if len(sys.argv) < 2:
        raise SystemExit("Usage: post_to_slack.py <payload_json_path>")
    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)

    # Support both list (new) and dict (legacy) formats
    if isinstance(payload, list):
        for i, p in enumerate(payload):
            if i > 0:
                time.sleep(SLACK_POST_DELAY)
            print(f"Posting message {i + 1}/{len(payload)}...")
            post_one(p)
        print(f"Posted {len(payload)} message(s) to Slack.")
    else:
        post_one(payload)
        print("Posted to Slack.")

if __name__ == "__main__":
    main()
