"""YouTube投稿: 予約公開（publishAt）でアップロードし、サムネを設定する。"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from common import abs_path, load_config

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]
JST = timezone(timedelta(hours=9))


def get_service():
    cfg = load_config()["youtube"]
    token = abs_path(cfg["token_file"])
    creds = Credentials.from_authorized_user_file(str(token), SCOPES) if token.exists() else None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # 初回のみブラウザで認可（ローカルPCで一度実行して token.json を作る）
            flow = InstalledAppFlow.from_client_secrets_file(str(abs_path(cfg["client_secrets"])), SCOPES)
            creds = flow.run_local_server(port=0)
        token.parent.mkdir(parents=True, exist_ok=True)
        token.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


def publish_at_utc() -> str:
    c = load_config()["channel"]
    day = datetime.now(JST).date() + timedelta(days=c["days_ahead"])
    dt = datetime(day.year, day.month, day.day, c["publish_hour_jst"], 0, tzinfo=JST)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def upload(video: Path, thumb: Path, title: str, description: str, tags: list[str]) -> str:
    cfg = load_config()
    yt = get_service()
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": (cfg["channel"]["tags_base"] + tags)[:30],
            "categoryId": cfg["youtube"]["category_id"],
            "defaultLanguage": "ja",
            "defaultAudioLanguage": "ja",
        },
        "status": {
            "privacyStatus": cfg["youtube"]["privacy"],
            "publishAt": publish_at_utc(),
            "selfDeclaredMadeForKids": cfg["youtube"]["made_for_kids"],
            # AI生成コンテンツの開示（YouTubeの合成コンテンツ表示）
            "containsSyntheticMedia": True,
        },
    }
    media = MediaFileUpload(str(video), chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/mp4")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    vid = resp["id"]
    yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb))).execute()
    return vid


def fetch_stats(video_ids: list[str]) -> dict[str, int]:
    """再生数を取得（ネタ出しのフィードバック用）。"""
    yt = get_service()
    out = {}
    for i in range(0, len(video_ids), 50):
        res = yt.videos().list(part="statistics", id=",".join(video_ids[i:i + 50])).execute()
        for it in res.get("items", []):
            out[it["id"]] = int(it["statistics"].get("viewCount", 0))
    return out
