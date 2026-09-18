"""毎日1本: ネタ選定 → 台本 → 音声 → 動画 → サムネ → 予約投稿 → ログ。

使い方:
  python pipeline/run_daily.py            # 投稿まで実行
  python pipeline/run_daily.py --dry-run  # 投稿せず output/ に動画を残す（初期検証用）
  python pipeline/run_daily.py --stats    # 過去動画の再生数を取り込む（週1で実行）
"""
import argparse
import json
import random
import shutil
import sys
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from common import abs_path, append_jsonl, load_config, read_json, slugify, write_json  # noqa: E402
from script import make_script  # noqa: E402
from thumbnail import make_thumbnail  # noqa: E402
from topics import pick_topic  # noqa: E402
from tts import concat_audio, synthesize_chapters  # noqa: E402
from upload import fetch_stats, upload  # noqa: E402
from video import render  # noqa: E402


def sync_stats() -> None:
    cfg = load_config()
    db_path = abs_path(cfg["paths"]["topics_db"])
    db = read_json(db_path, {"unused": [], "used": []})
    ids = [t["video_id"] for t in db["used"] if t.get("video_id")]
    if not ids:
        print("no uploaded videos yet")
        return
    stats = fetch_stats(ids)
    for t in db["used"]:
        if t.get("video_id") in stats:
            t["views"] = stats[t["video_id"]]
    write_json(db_path, db)
    print(f"updated {len(stats)} videos")


def run(dry_run: bool) -> None:
    cfg = load_config()
    stamp = datetime.now().strftime("%Y%m%d")
    topic = pick_topic()
    work = abs_path(cfg["paths"]["output_dir"]) / f"{stamp}_{slugify(topic['title'])}"
    work.mkdir(parents=True, exist_ok=True)
    print("topic:", topic["title"])

    script = make_script(topic)
    write_json(work / "script.json", script)
    chapters = synthesize_chapters(script["chapters"], work / "audio")
    audio = concat_audio(chapters, work / "narration.mp3")
    total = sum(c["duration"] for c in chapters)
    print(f"audio: {total/60:.1f} min")

    video = render(chapters, audio, work / "video.mp4")
    bgs = sorted(abs_path(cfg["video"]["backgrounds_dir"]).glob("*.[jp][pn]g"))
    title = script["title_candidates"][0]
    thumb = make_thumbnail(random.choice(bgs), script["thumbnail_text"], title, work / "thumb.jpg")

    record = {"date": stamp, "topic": topic["title"], "title": title, "minutes": round(total / 60, 1), "dir": str(work)}
    if dry_run:
        print("dry-run: skip upload ->", video)
    else:
        vid = upload(video, thumb, title, script["description"], script["tags"])
        record["video_id"] = vid
        db_path = abs_path(cfg["paths"]["topics_db"])
        db = read_json(db_path, {"unused": [], "used": []})
        for t in db["used"]:
            if t["title"] == topic["title"]:
                t["video_id"] = vid
        write_json(db_path, db)
        # 中間ファイルを削除して容量節約
        shutil.rmtree(work / "audio", ignore_errors=True)
        for p in work.glob("seg*.mp4"):
            p.unlink()
        (work / "joined.mp4").unlink(missing_ok=True)
        print("uploaded:", f"https://youtu.be/{vid}")
    append_jsonl(abs_path(cfg["paths"]["history_log"]), record)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--stats", action="store_true")
    a = ap.parse_args()
    try:
        sync_stats() if a.stats else run(a.dry_run)
    except Exception:
        traceback.print_exc()
        append_jsonl(abs_path(load_config()["paths"]["history_log"]),
                     {"date": datetime.now().isoformat(), "error": traceback.format_exc()[-2000:]})
        sys.exit(1)
