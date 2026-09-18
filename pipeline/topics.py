"""ネタ出し: 未使用テーマを補充し、今日の1本を選ぶ。過去の再生実績を反映する。"""
from datetime import datetime

from common import abs_path, claude_json, load_config, read_json, write_json

SYSTEM = """あなたは歴史雑学YouTubeチャンネルの企画担当です。
チャンネルコンセプト: {concept}
視聴者は20〜50代の日本人。学校で習った歴史の「裏側」「意外な理由」「知られざるつながり」に興味があります。
各テーマは1本8〜12分の動画として成立し、公開情報（教科書・一般書・百科事典レベル）で裏付けられる内容にしてください。
陰謀論・未検証の俗説・特定の民族/宗教/現存する政治勢力への中傷になりうるものは避けてください。"""


def pick_topic() -> dict:
    cfg = load_config()
    db_path = abs_path(cfg["paths"]["topics_db"])
    db = read_json(db_path, {"unused": [], "used": []})

    if len(db["unused"]) < 3:
        used_titles = [t["title"] for t in db["used"]][-200:]
        top = sorted(db["used"], key=lambda t: t.get("views", 0), reverse=True)[:10]
        feedback = "\n".join(f"- {t['title']}（{t.get('views', 0)}回再生）" for t in top) or "（まだ実績なし）"
        prompt = f"""新しい動画テーマを20本提案してください。

## 直近の使用済みテーマ（重複禁止）
{chr(10).join('- ' + t for t in used_titles) or '（なし）'}

## 過去に伸びたテーマ（この傾向を参考に、似た切り口を増やす）
{feedback}

## 出力形式
{{"topics": [{{"title": "動画テーマ（動画タイトルではなく内容の要約）", "hook": "冒頭で提示する意外な事実を1文で", "era": "時代・地域", "angle": "この動画でしか語らない切り口"}}]}}
世界史と日本史を混ぜ、時代・地域が偏らないようにしてください。"""
        res = claude_json(prompt, SYSTEM.format(concept=cfg["channel"]["concept"]), cfg)
        db["unused"].extend(res["topics"])

    topic = db["unused"].pop(0)
    topic["picked_at"] = datetime.now().isoformat(timespec="seconds")
    db["used"].append(topic)
    write_json(db_path, db)
    return topic


if __name__ == "__main__":
    print(pick_topic())
