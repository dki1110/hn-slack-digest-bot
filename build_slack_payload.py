#!/usr/bin/env python3
import json
import os
from datetime import date
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

HN_TOP_N = int(os.getenv("HN_TOP_N", "20"))
SLACK_PREFIX = os.getenv("SLACK_PREFIX", "").strip()

def md_link(text: str, url: str) -> str:
    if not url:
        return text
    return f"<{url}|{text}>"

def fmt_section(title: str, points: list[str], max_n: int = 3) -> list[str]:
    if not points:
        return []
    out = [f"   *{title}*"]
    for p in points[:max_n]:
        out.append(f"   • {p}")
    return out

def labels(lang: str):
    if lang == "en":
        return {
            "digest": "Hacker News Digest",
            "top": "Top",
            "pro": "Pro",
            "con": "Con",
            "points": "Points",
            "note": "Note: comment summaries are based on fetched HN comments (up to HN_COMMENTS_MAX). If article body is unavailable, summaries rely on metadata."
        }
    return {
        "digest": "Hacker News Digest",
        "top": "上位",
        "pro": "賛成",
        "con": "反対",
        "points": "論点",
        "note": "注: コメント要約は取得できたコメント（最大HN_COMMENTS_MAX件）からの要約です。本文未取得の記事はメタ情報ベースになります。"
    }

def main() -> None:
    with open("data/hn_with_text.json", encoding="utf-8") as f:
        hn = json.load(f)
    with open("data/summaries.json", encoding="utf-8") as f:
        sm = json.load(f)

    lang = sm.get("lang", "ja")
    L = labels(lang)

    sm_by_id = {x["hn_id"]: x for x in sm["items"]}

    today = hn.get("date") or date.today().isoformat()
    header = f"{SLACK_PREFIX}\n*{L['digest']}* ({today})  {L['top']}{HN_TOP_N}"
    lines = [header, ""]

    body_sources = Counter(i.get("body_source") for i in hn.get("items", []))
    if body_sources:
        lines.append(f"_body_source: {dict(body_sources)}_")
        lines.append("")

    for idx, it in enumerate(hn["items"], start=1):
        sid = str(it.get("hn_id",""))
        s = sm_by_id.get(sid)
        title = it.get("title","") or "(no title)"
        url = it.get("url","")
        pts = it.get("points")
        com = it.get("comments")
        domain = it.get("domain","")
        meta = f"▲{pts} / 💬{com} / {domain}"

        if not s:
            lines.append(f"{idx}. {md_link(title, url)}  _{meta}_")
            lines.append("")
            continue

        used = "body" if s.get("used_body") else "meta"
        conf = s.get("confidence","")
        src = s.get("body_source","")
        comment_fetched = int(it.get("comment_count_fetched") or 0)
        comment_tag = f"comments:{comment_fetched}"

        lines.append(f"{idx}. {md_link(title, url)}  _{meta}_  `{used}` `{conf}` `{src}` `{comment_tag}`")
        lines.append(f"   {s.get('summary','').strip()}")

        bullets = s.get("bullets", [])[:8]
        for b in bullets[:5]:
            lines.append(f"   • {b}")

        pro = s.get("comment_pro", []) or []
        con = s.get("comment_con", []) or []
        pts2 = s.get("comment_points", []) or []

        if comment_fetched > 0 and (pro or con or pts2):
            lines += fmt_section(L["pro"], pro, max_n=3)
            lines += fmt_section(L["con"], con, max_n=3)
            lines += fmt_section(L["points"], pts2, max_n=3)

        lines.append("")

    lines.append(f"_{L['note']}_")

    payload = {"text": "\n".join(lines)}
    os.makedirs("out", exist_ok=True)
    out_path = f"out/slack_payload_{today}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(out_path)

if __name__ == "__main__":
    main()
