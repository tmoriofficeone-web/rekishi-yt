"""サムネ生成: 背景画像＋大きな煽り文＋タイトル短縮版。1280x720。"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from common import abs_path, load_config


def _wrap(text: str, n: int) -> list[str]:
    return [text[i:i + n] for i in range(0, len(text), n)]


def make_thumbnail(bg: Path, headline: str, subline: str, out_path: Path) -> Path:
    cfg = load_config()
    font_path = abs_path(cfg["video"]["font_path"])
    W, H = 1280, 720
    img = Image.open(bg).convert("RGB")
    ratio = max(W / img.width, H / img.height)
    img = img.resize((int(img.width * ratio), int(img.height * ratio)))
    img = img.crop(((img.width - W) // 2, (img.height - H) // 2, (img.width - W) // 2 + W, (img.height - H) // 2 + H))
    img = img.filter(ImageFilter.GaussianBlur(1.2))
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rectangle([0, H // 2, W, H], fill=(0, 0, 0, 150))
    img = Image.alpha_composite(img.convert("RGBA"), overlay)

    d = ImageDraw.Draw(img)
    big = ImageFont.truetype(str(font_path), 120)
    small = ImageFont.truetype(str(font_path), 60)

    def stroke_text(xy, text, font, fill, stroke=8):
        d.text(xy, text, font=font, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))

    stroke_text((60, 60), headline[:10], big, (255, 230, 0))
    y = H // 2 + 40
    for line in _wrap(subline, 14)[:2]:
        stroke_text((60, y), line, small, (255, 255, 255), 6)
        y += 80
    img.convert("RGB").save(out_path, quality=92)
    return out_path
