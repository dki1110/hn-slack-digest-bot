#!/usr/bin/env python3
import json
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()
WEBHOOK = os.getenv("SLACK_WEBHOOK_URL", "").strip()
TIMEOUT = int(os.getenv("REQUEST_TIMEOUT_SEC", "15"))

def main() -> None:
    if not WEBHOOK:
        print("SLACK_WEBHOOK_URL is not set. Skipping post.")
        return
    if len(sys.argv) < 2:
        raise SystemExit("Usage: post_to_slack.py <payload_json_path>")
    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)

    r = requests.post(WEBHOOK, json=payload, timeout=TIMEOUT)
    if r.status_code >= 400:
        raise SystemExit(f"Slack webhook failed: {r.status_code} {r.text}")
    print("Posted to Slack.")

if __name__ == "__main__":
    main()
