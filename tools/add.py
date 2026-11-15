#!/usr/bin/env python3
"""Turn a .haru file (exported from the haru-kit web app or Mac app) into a character of this registry.

    python tools/add.py Coach.haru --author yourname [--name coach] [--version 1.0]

It writes characters/<name>/ (the character file, the voices as Ogg Opus mono 48 kbps, the picture),
checks it, and updates characters/index.json. Needs ffmpeg. Then open a pull request with these changes.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
import unicodedata
import zipfile
from datetime import date
from pathlib import Path

from build import index_text
from check import check_character
from common import CHARACTERS, FORMAT, IMAGE_TYPES, INDEX, read_json, to_opus, write_json


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def main() -> int:
    parser = argparse.ArgumentParser(description="Add a character from a .haru file.")
    parser.add_argument("file", type=Path)
    parser.add_argument("--author", required=True, help="your name or GitHub user name")
    parser.add_argument("--name", help="folder name (default: the character's English or first title)")
    parser.add_argument("--version", default="1.0")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(args.file) as archive:
        archive.extractall(tmp)
        root = Path(tmp)
        index = read_json(root / "haru.json")
        if index.get("kind") != "haru-kit" or len(index.get("characters", [])) != 1:
            print("This must be a .haru file with one character (in the app: Export the character).")
            return 1
        source = read_json(root / "characters" / f"{index['characters'][0]}.character.json")
        versions = source["versions"]
        first = versions.get("en") or next(iter(versions.values()))
        name = slug(args.name or first["title"]) or "character"
        folder = CHARACTERS / name
        if folder.exists():
            print(f"characters/{name} exists. Choose another --name, or delete that folder to replace it.")
            return 1
        folder.mkdir(parents=True)

        renamed: dict[str, str] = {}
        for lang, version in versions.items():
            old = version["voice"]
            if old not in renamed:
                meta = read_json(root / "voices" / f"{old}.voice.json")
                new = f"{name}-{meta.get('language') or lang}"
                while new in renamed.values():
                    new += "-2"
                renamed[old] = new
                to_opus(root / "voices" / (meta.get("file") or f"{old}.flac"), folder / f"{new}.ogg")
                meta.update(id=new, file=f"{new}.ogg")
                meta.setdefault("author", args.author)
                write_json(folder / f"{new}.voice.json", meta)
            version["voice"] = renamed[old]

        image = ""
        picture = root / "images" / str(source.get("image") or "")
        if source.get("image") and picture.is_file() and picture.suffix.lower() in IMAGE_TYPES:
            image = f"picture{picture.suffix.lower()}"
            shutil.copyfile(picture, folder / image)

        write_json(folder / "character.json", {
            "format": FORMAT, "id": name, "author": args.author, "version": args.version,
            "updated": date.today().isoformat(), "image": image, "versions": versions})

    errors, warnings = check_character(folder)
    for line in warnings:
        print(f"warning: {line}")
    if errors:
        for line in errors:
            print(f"error: {line}")
        print(f"\ncharacters/{name} was written, but it does not pass the checks. Fix the errors above.")
        return 1
    INDEX.write_text(index_text(), encoding="utf-8")
    print(f"Added characters/{name} and updated characters/index.json. Open a pull request with both.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
