#!/usr/bin/env bash
set -euo pipefail

# Always run from project directory
cd "$(dirname "$0")"

# Prefer venv python if available
PY="./.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="$(command -v python3)"
fi

# Load .env into shell (only simple KEY=VALUE lines; ignores comments/blank lines)
if [[ -f .env ]]; then
  while IFS= read -r line; do
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]] || continue
    export "$line"
  done < .env
fi

# Prompt switching:
# - PROMPT_LANG=ja|en (default: en)
# - or set PROMPT_FILE to a custom path
PROMPT_LANG="${PROMPT_LANG:-en}"
PROMPT_FILE="${PROMPT_FILE:-$PWD/prompts/${PROMPT_LANG}.txt}"

if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "[hn-bot] ERROR: prompt file not found: $PROMPT_FILE" >&2
  echo "Set PROMPT_LANG=ja|en or PROMPT_FILE=/path/to/prompt.txt" >&2
  exit 1
fi

echo "[hn-bot] Fetch HN..."
"$PY" fetch_hn.py

echo "[hn-bot] Fetch article text + HN comments..."
"$PY" fetch_article_text.py

echo "[hn-bot] Summarize via Codex (needs prior login)..."
PROMPT="$(cat "$PROMPT_FILE")"
codex exec "$PROMPT" --output-schema ./schema.json -o ./data/summaries.json --full-auto

echo "[hn-bot] Build Slack payload..."
PAYLOAD_PATH=$("$PY" build_slack_payload.py)

echo "[hn-bot] Post to Slack..."
"$PY" post_to_slack.py "$PAYLOAD_PATH"

echo "[hn-bot] Done."
