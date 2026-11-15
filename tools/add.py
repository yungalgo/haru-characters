#!/usr/bin/env python3
"""Turn a .haru file (exported from the haru-kit web app or Mac app) into an entry of this registry.

    python tools/add.py my-character.haru --author yourname [--name coach] [--version 1.0]

It writes entries/<author>-<name>/ with the character file, the voices converted to Ogg Opus (mono, 48 kbps),
and the picture, then runs the checks. Needs ffmpeg. Then open a pull request with the new folder.
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

from check import check_entry
from common import ENTRIES, FORMAT, IMAGE_TYPES, read_json, to_opus, write_json


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("file", type=Path)
    parser.add_argument("--author", required=True, help="your name or GitHub user name")
    parser.add_argument("--name", help="short name for the id (default: the character's English or first title)")
    parser.add_argument("--version", default="1.0")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(args.file) as archive:
        archive.extractall(tmp)
        root = Path(tmp)
        index = read_json(root / "haru.json")
        if index.get("kind") != "haru-kit" or len(index.get("characters", [])) != 1:
            print("This file must be a .haru file with one character (export a character from the app).")
            return 1
        source = read_json(root / "characters" / f"{index['characters'][0]}.character.json")
        versions = source["versions"]
        first = versions.get("en") or next(iter(versions.values()))
        entry = f"{slug(args.author)}-{slug(args.name or first['title']) or 'character'}"
        folder = ENTRIES / entry
        if folder.exists():
            print(f"entries/{entry} exists. Use another --name, or delete the folder first to replace it.")
            return 1
        (folder / "voices").mkdir(parents=True)

        renamed: dict[str, str] = {}
        for lang, version in versions.items():
            old = version["voice"]
            if old in renamed:
                version["voice"] = renamed[old]
                continue
            meta = read_json(root / "voices" / f"{old}.voice.json")
            new = f"{entry}-{meta.get('language') or lang}"
            while new in renamed.values():
                new += "-2"
            renamed[old] = version["voice"] = new
            clip = root / "voices" / (meta.get("file") or f"{old}.flac")
            to_opus(clip, folder / "voices" / f"{new}.ogg")
            meta.update(id=new, file=f"{new}.ogg", author=meta.get("author") or args.author)
            write_json(folder / "voices" / f"{new}.voice.json", meta)

        image = ""
        if source.get("image") and (root / "images" / source["image"]).is_file():
            suffix = Path(source["image"]).suffix.lower()
            if suffix in IMAGE_TYPES:
                image = f"picture{suffix}"
                shutil.copyfile(root / "images" / source["image"], folder / image)

        character = {"format": FORMAT, "id": entry, "author": args.author, "version": args.version,
                     "updated": date.today().isoformat(), "image": image, "versions": versions}
        write_json(folder / "character.json", character)

    errors, warnings = check_entry(folder)
    for line in warnings:
        print(f"warning: {line}")
    if errors:
        for line in errors:
            print(f"error: {line}")
        print(f"\nentries/{entry} was written, but it does not pass the checks yet. Fix the errors above.")
        return 1
    print(f"Added entries/{entry}. Check it, then open a pull request with this folder.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
