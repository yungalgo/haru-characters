"""Rules and helpers shared by the registry tools (standard library only, plus ffmpeg/ffprobe for audio)."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENTRIES = ROOT / "entries"
FORMAT = 1
LANGUAGES = ("en", "ja", "zh", "ko", "es", "fr", "de", "pt", "ru")
CARD_FIELDS = ("persona", "name", "gender", "backchannel", "other_name", "relationship", "situation")
ID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".webp"}

MIN_SECONDS, MAX_SECONDS = 3.0, 180.0
MAX_CLIP_BYTES = 1_500_000  # 3 minutes of Opus at 48 kbps is about 1.1 MB
MAX_IMAGE_BYTES = 512_000
MAX_BITRATE = 64_000
BITRATE = "48k"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def probe(path: Path) -> dict:
    """codec, channels, seconds, bitrate of an audio file (ffprobe)."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
         "stream=codec_name,channels:format=duration,bit_rate,format_name", "-of", "json", str(path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return {}
    data = json.loads(result.stdout or "{}")
    stream = (data.get("streams") or [{}])[0]
    fmt = data.get("format") or {}
    return {
        "codec": stream.get("codec_name"), "channels": stream.get("channels"), "container": fmt.get("format_name"),
        "seconds": float(fmt.get("duration") or 0), "bitrate": int(fmt.get("bit_rate") or 0),
    }


def to_opus(source: Path, target: Path) -> None:
    """Any audio file -> Ogg Opus, mono, 48 kbps (the one type that the registry takes)."""
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(source), "-ac", "1",
                    "-c:a", "libopus", "-b:a", BITRATE, "-vbr", "on", str(target)], check=True)
