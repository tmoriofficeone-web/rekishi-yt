"""音声生成: 章ごとに ElevenLabs で生成し、尺を取って字幕タイミングに使う。"""
import os
import subprocess
from pathlib import Path

import requests

from common import load_config

API = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


def _duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def synthesize_chapters(chapters: list[dict], out_dir: Path) -> list[dict]:
    """各章の narration を mp3 化し、{'path','duration'} を付与して返す。"""
    cfg = load_config()["elevenlabs"]
    out_dir.mkdir(parents=True, exist_ok=True)
    headers = {"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "Content-Type": "application/json"}
    result = []
    for i, ch in enumerate(chapters):
        path = out_dir / f"ch{i:02d}.mp3"
        r = requests.post(
            API.format(voice_id=cfg["voice_id"]),
            headers=headers,
            json={
                "text": ch["narration"],
                "model_id": cfg["model_id"],
                "voice_settings": {"stability": cfg["stability"], "similarity_boost": cfg["similarity_boost"]},
            },
            timeout=300,
        )
        r.raise_for_status()
        path.write_bytes(r.content)
        result.append({**ch, "audio": str(path), "duration": _duration(path)})
    return result


def concat_audio(chapters: list[dict], out_path: Path) -> Path:
    lst = out_path.parent / "concat.txt"
    lst.write_text("".join(f"file '{Path(c['audio']).resolve()}'\n" for c in chapters), encoding="utf-8")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out_path)],
        check=True, capture_output=True,
    )
    return out_path
