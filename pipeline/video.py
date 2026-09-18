"""動画合成: 背景画像を章ごとに切替 → 章タイトル＋字幕を焼き込み → 音声をミックス。"""
import re
import subprocess
from pathlib import Path

from common import abs_path, load_config


def _srt_time(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(chapters: list[dict], out_path: Path) -> Path:
    """章内の文を文字数比で時間配分して字幕を作る（ElevenLabsの timestamps API を使えばより正確）。"""
    lines, idx, t = [], 1, 0.0
    for ch in chapters:
        sents = [s for s in re.split(r"(?<=[。！？!?])\s*", ch["narration"]) if s.strip()]
        total = sum(len(s) for s in sents) or 1
        for s in sents:
            d = ch["duration"] * len(s) / total
            lines.append(f"{idx}\n{_srt_time(t)} --> {_srt_time(t + d)}\n{s.strip()}\n")
            idx += 1
            t += d
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def render(chapters: list[dict], audio: Path, out_path: Path) -> Path:
    cfg = load_config()
    v = cfg["video"]
    w, h, fps = v["width"], v["height"], v["fps"]
    bgs = sorted(abs_path(v["backgrounds_dir"]).glob("*.[jp][pn]g"))
    if not bgs:
        raise RuntimeError("assets/backgrounds に背景画像を入れてください")
    font = abs_path(v["font_path"])
    work = out_path.parent

    # 1) 章ごとの背景セグメント（章タイトル入り）
    seg_paths = []
    for i, ch in enumerate(chapters):
        bg = bgs[i % len(bgs)]
        seg = work / f"seg{i:02d}.mp4"
        heading = ch["heading"].replace("'", "’").replace(":", "：")
        vf = (
            f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
            f"zoompan=z='min(zoom+0.0004,1.08)':d={int(ch['duration'] * fps) + 1}:s={w}x{h}:fps={fps},"
            f"drawbox=x=0:y=0:w=iw:h=110:color=black@0.45:t=fill,"
            f"drawtext=fontfile='{font}':text='{heading}':fontsize=44:fontcolor=white:x=40:y=32"
        )
        subprocess.run(
            ["ffmpeg", "-y", "-loop", "1", "-i", str(bg), "-t", f"{ch['duration']:.3f}",
             "-vf", vf, "-r", str(fps), "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "veryfast", str(seg)],
            check=True, capture_output=True,
        )
        seg_paths.append(seg)

    lst = work / "segs.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in seg_paths), encoding="utf-8")
    joined = work / "joined.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(joined)],
                   check=True, capture_output=True)

    # 2) 字幕焼き込み + 音声（＋任意BGM）
    srt = build_srt(chapters, work / "subs.srt")
    style = (f"FontName=Noto Sans JP,FontSize={v['subtitle_fontsize']},Bold=1,PrimaryColour=&H00FFFFFF,"
             f"OutlineColour=&H00000000,Outline=3,Shadow=1,MarginV=60")
    cmd = ["ffmpeg", "-y", "-i", str(joined), "-i", str(audio)]
    filter_a = "[1:a]anull[a]"
    if v.get("bgm_path"):
        cmd += ["-stream_loop", "-1", "-i", str(abs_path(v["bgm_path"]))]
        filter_a = f"[2:a]volume={v['bgm_volume']}[bgm];[1:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[a]"
    cmd += [
        "-filter_complex", f"[0:v]subtitles='{srt}':fontsdir='{font.parent}':force_style='{style}'[v];{filter_a}",
        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_path
