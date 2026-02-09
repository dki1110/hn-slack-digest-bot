# hn-slack-digest-bot

A macOS-first bot that runs daily (via `launchd` or manually) to:

1) fetch Hacker News front-page stories,  
2) (optionally) fetch linked article text + HN comments,  
3) summarize with **Codex CLI using ChatGPT sign-in (no API key)**,  
4) post a digest to Slack via **Incoming Webhook**.

## What it posts
For each story:
- a short summary (3–5 sentences),
- key bullets,
- **HN comments summarized as Pro / Con / Points** (short, 0–3 items each).

Language is switchable (default: **English**).

---

## Requirements
- macOS
- Python 3.10+
- Node.js (for Codex CLI)
- Slack Incoming Webhook URL
- Codex CLI installed and signed in:
  ```bash
  npm i -g @openai/codex
  codex   # sign in via browser (ChatGPT)
  ```

---

## Setup

### 1) Create venv & install deps
```bash
cd ~/hn-slack-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If you use `BODY_MODE=readability`, ensure `lxml_html_clean` is installed:
```bash
pip install lxml_html_clean
python3 -c "from readability import Document; print('readability OK')"
```

### 2) Configure `.env`
```bash
cp .env.example .env
```

Edit `.env` and set:
- `SLACK_WEBHOOK_URL=...` (keep secret; do NOT commit)
- optional fetching options
- language:
  - `PROMPT_LANG=en` (default)
  - `PROMPT_LANG=ja`

### 3) Run locally
```bash
./run.sh
```

Outputs:
- `data/hn.json` (HN items)
- `data/hn_with_text.json` (plus optional article text + HN comments)
- `data/summaries.json` (Codex output)
- `out/slack_payload_YYYY-MM-DD.json` (payload sent to Slack)

---

## Daily run on macOS (launchd)

1) Copy plist:
```bash
mkdir -p ~/Library/LaunchAgents
cp launchd/com.example.hn-slack-bot.plist ~/Library/LaunchAgents/com.example.hn-slack-bot.plist
```

2) Edit the plist:
- adjust time (`StartCalendarInterval`)
- ensure the path points to your project folder (e.g. `~/hn-slack-bot`)

3) Load:
```bash
launchctl load ~/Library/LaunchAgents/com.example.hn-slack-bot.plist
```

Logs:
- `/tmp/hn-slack-bot.out.log`
- `/tmp/hn-slack-bot.err.log`

> Note: if your Mac sleeps, the job won’t run at the exact scheduled time. Consider keeping it awake around the schedule.

---

## Key configuration (.env)
- `PROMPT_LANG`: `en` (default) or `ja`
- `HN_TOP_N`: number of front-page items
- `HN_COMMENTS_MAX`: max HN comments fetched per story (0 disables)
- `FETCH_ARTICLE_BODY`: fetch linked article body (`true/false`)
- `BODY_MODE`: `ogp_only` (safer) or `readability` (best-effort)
- `BODY_FETCH_MAX`: max linked articles fetched per run
- `ALLOW_DOMAINS` / `DENY_DOMAINS`: control which domains can be fetched
- `MAX_SOURCE_CHARS`: cap extracted article text length passed to summarizer

---

## Notes & caveats
- Many sites render content with JS or block scrapers; `readability` may fail. Use `ogp_only` or `ALLOW_DOMAINS` for stability.
- To avoid copyright issues, the bot does **not** paste full article text into Slack; it only summarizes.

---

## Japanese README
See: `README.ja.md`
