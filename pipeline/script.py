"""台本生成: 固定の型で章立て台本＋タイトル候補＋説明文＋タグを一括生成。"""
from common import claude_json, load_config

SYSTEM = """あなたは歴史雑学YouTubeチャンネル「{name}」の台本作家です。
コンセプト: {concept}

## 台本の固定型（必ずこの順）
1. フック（30秒）: 結論となる「意外な事実」を先出しして視聴者を引き込む。「実は〜だった」「〜の本当の理由は〜」
2. 前提（1分）: その出来事を知らない人向けの最低限の背景
3. 裏側（5〜7分）: なぜそうなったのか。3つ前後の具体的エピソードで語る。数字・固有名詞・年代を入れる
4. 現代とのつながり（1〜2分）: 今の私たちの生活・常識にどう残っているか
5. 締め（30秒）: ひとことの余韻＋「次回は〜」で回遊を促す。チャンネル登録の呼びかけは1回だけ

## 文体
- ナレーション音声で読み上げるため、話し言葉。一文は短く。漢字の読みが紛らわしい語は「ひらがな」か読みがなを括弧で添える
- 断定は裏付けのある事実のみ。諸説ある箇所は「〜という説が有力です」と明示
- 差別的表現・現存する人物や団体への中傷は禁止
- 尺: 全体で約{minutes}分（日本語で1分≈300字。合計{chars}字前後）"""


def make_script(topic: dict) -> dict:
    cfg = load_config()
    minutes = cfg["channel"]["target_minutes"]
    prompt = f"""次のテーマで台本を書いてください。

テーマ: {topic['title']}
フック案: {topic['hook']}
時代・地域: {topic['era']}
切り口: {topic['angle']}

## 出力形式
{{
  "title_candidates": ["視聴者がクリックしたくなるタイトル案を5つ。28字以内。『〇〇が△△だった本当の理由』『なぜ〇〇は△△したのか』型を含める"],
  "chapters": [
    {{"heading": "章タイトル（画面に表示。12字以内）", "narration": "この章のナレーション全文"}}
  ],
  "description": "YouTube説明文。冒頭2行で内容を要約し、その後に章立て一覧。最後に『この動画は公開されている歴史資料をもとに構成しています』と入れる",
  "tags": ["この動画固有のタグを8個"],
  "thumbnail_text": "サムネに載せる短い煽り文。10字以内。例: 『本当の理由』『教科書の嘘』"
}}
章は5〜7個。chapters の narration を全部つなげたものが動画の全ナレーションになります。"""
    system = SYSTEM.format(
        name=cfg["channel"]["name"],
        concept=cfg["channel"]["concept"],
        minutes=minutes,
        chars=minutes * 300,
    )
    return claude_json(prompt, system, cfg)


if __name__ == "__main__":
    import json, sys
    t = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {
        "title": "ナポレオンがロシア遠征で敗れた本当の理由", "hook": "敵は寒さではなく発疹チフスだった",
        "era": "19世紀ヨーロッパ", "angle": "軍医の記録から読み解く"}
    print(json.dumps(make_script(t), ensure_ascii=False, indent=2))
