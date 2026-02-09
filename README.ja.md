# hn-slack-digest-bot

macOS 上で毎日（`launchd` / 手動）実行し、

1) Hacker News のフロントページ上位を取得  
2) （任意）リンク先記事の本文抽出 + HNコメント取得  
3) **Codex CLI（ChatGPTログイン / APIキー不要）**で要約  
4) Slack（Incoming Webhook）へ投稿  

を行うボットです。

## 投稿内容
各記事について：
- 3〜5文の短い要約
- 箇条書きのポイント
- **コメント要約（賛成 / 反対 / 論点）**（各0〜3点、短く）

言語は切り替え可能です（デフォルトは **英語**）。

---

## 必要なもの
- macOS
- Python 3.10+
- Node.js（Codex CLI用）
- Slack Incoming Webhook URL
- Codex CLI のインストールとログイン：
  ```bash
  npm i -g @openai/codex
  codex   # ブラウザが開くのでChatGPTでログイン
  ```

---

## セットアップ

### 1) venv作成と依存導入
```bash
cd ~/hn-slack-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`BODY_MODE=readability` を使う場合は `lxml_html_clean` が必要です：
```bash
pip install lxml_html_clean
python3 -c "from readability import Document; print('readability OK')"
```

### 2) `.env` を作る
```bash
cp .env.example .env
```

`.env` を編集して最低限これを設定：
- `SLACK_WEBHOOK_URL=...`（コミットしない）
- 言語：
  - `PROMPT_LANG=en`（デフォルト）
  - `PROMPT_LANG=ja`

### 3) ローカル実行
```bash
./run.sh
```

生成物：
- `data/hn.json`（HN取得結果）
- `data/hn_with_text.json`（本文/コメント等を追加した入力）
- `data/summaries.json`（Codex要約結果）
- `out/slack_payload_YYYY-MM-DD.json`（Slack投稿payload）

---

## macOSで毎日実行（launchd）

1) plistを配置：
```bash
mkdir -p ~/Library/LaunchAgents
cp launchd/com.example.hn-slack-bot.plist ~/Library/LaunchAgents/com.example.hn-slack-bot.plist
```

2) plistを編集：
- 実行時刻（`StartCalendarInterval`）
- プロジェクトパス（例：`~/hn-slack-bot`）

3) 読み込み：
```bash
launchctl load ~/Library/LaunchAgents/com.example.hn-slack-bot.plist
```

ログ：
- `/tmp/hn-slack-bot.out.log`
- `/tmp/hn-slack-bot.err.log`

※Macがスリープしていると定刻実行されません。必要なら実行時刻付近は起動状態にしてください。

---

## 主な `.env` 設定
- `PROMPT_LANG`: `en`（デフォルト）/ `ja`
- `HN_TOP_N`: 取得する上位件数
- `HN_COMMENTS_MAX`: 各記事で取得するコメント数（0で無効）
- `FETCH_ARTICLE_BODY`: リンク先本文取得（true/false）
- `BODY_MODE`: `ogp_only`（安全）/ `readability`（ベストエフォート）
- `BODY_FETCH_MAX`: 1回で本文取得する記事数の上限
- `ALLOW_DOMAINS` / `DENY_DOMAINS`: 本文取得対象ドメインの制御
- `MAX_SOURCE_CHARS`: 要約入力に渡す本文文字数上限

---

## 注意点
- JS描画サイト/取得拒否サイトは `readability` で本文が取れないことがあります。安定性優先なら `ogp_only` や `ALLOW_DOMAINS` を使ってください。
- 著作権・規約面のリスクを下げるため、本文をSlackに転載せず、要約のみを投稿します。
