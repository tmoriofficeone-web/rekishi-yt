import json
import os
import re
from pathlib import Path

import yaml
from anthropic import Anthropic

ROOT = Path(__file__).resolve().parent.parent


def load_config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def abs_path(rel: str) -> Path:
    return ROOT / rel


def claude_json(prompt: str, system: str, cfg: dict) -> dict:
    """Claude に JSON のみを返させてパースする。"""
    client = Anthropic()  # ANTHROPIC_API_KEY を環境変数から読む
    resp = client.messages.create(
        model=cfg["claude"]["model"],
        max_tokens=cfg["claude"]["max_tokens"],
        system=system + "\n\n必ず有効なJSONのみを返してください。前置き・コードフェンス・説明文は一切不要です。",
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    return json.loads(text)


def read_json(path: Path, default):
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def slugify(s: str) -> str:
    return re.sub(r"[^0-9A-Za-z一-龠ぁ-んァ-ヶー]+", "_", s)[:40]
