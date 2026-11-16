#!/usr/bin/env python3
"""Turn a .haru file (exported from the haru-kit web app or Mac app) into a character of this registry.

    python tools/add.py Coach.haru [--author NAME] [--check-only]
    python tools/add.py --submissions [--author NAME]   # every file in submissions/ (the publish workflow)

It writes characters/<name>/ (the character file, the voices as Ogg Opus mono 48 kbps, the picture), checks it,
and updates characters/index.json. <name> comes from the character's English (else first) title. A character
with the same name is replaced, and its version goes up. Needs ffmpeg.
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
from common import CHARACTERS, FORMAT, IMAGE_TYPES, INDEX, ROOT, read_json, to_opus, write_json

SUBMISSIONS = ROOT / "submissions"


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def next_version(old: str) -> str:
    """1.0 -> 1.1; anything else -> old + '.1'."""
    parts = old.split(".")
    if parts and parts[-1].isdigit():
        parts[-1] = str(int(parts[-1]) + 1)
        return ".".join(parts)
    return f"{old}.1" if old else "1.0"


def add(file: Path, author: str | None, target_root: Path) -> tuple[str, list[str], list[str]]:
    """Write the character of `file` under target_root/<name>/. Returns (name, errors, warnings)."""
    with tempfile.TemporaryDirectory() as tmp:
        try:
            with zipfile.ZipFile(file) as archive:
                archive.extractall(tmp)  # zipfile drops absolute paths and '..'
            root = Path(tmp)
            index = read_json(root / "haru.json")
            source = read_json(root / "characters" / f"{index['characters'][0]}.character.json")
            versions = source["versions"]
            assert index.get("kind") == "haru-kit" and len(index["characters"]) == 1 and versions
        except Exception:  # noqa: BLE001 - any broken file gets the same answer
            return file.stem, ["this is not a .haru file with one character (in the app: Export the character)"], []
        first = versions.get("en") or next(iter(versions.values()))
        name = slug(str(first.get("title") or "")) or slug(file.stem) or "character"
        author = str(source.get("author") or author or "").strip()
        if not author:
            return name, ["no author: fill in the Author field of the character in the app, then export again"], []
        folder = target_root / name
        old = CHARACTERS / name / "character.json"
        version = str(source.get("version") or "")
        if old.is_file():
            previous = read_json(old).get("version", "")
            if not version or version == previous:
                version = next_version(previous)
        shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True)

        renamed: dict[str, str] = {}
        for lang, version_data in versions.items():
            voice_id = version_data.get("voice")
            if voice_id not in renamed:
                try:
                    meta = read_json(root / "voices" / f"{voice_id}.voice.json")
                    clip = root / "voices" / str(meta.get("file") or f"{voice_id}.flac")
                    new = f"{name}-{meta.get('language') or lang}"
                    while new in renamed.values():
                        new += "-2"
                    to_opus(clip, folder / f"{new}.ogg")
                except Exception:  # noqa: BLE001
                    return name, [f"the {lang!r} version's voice is missing or cannot be read"], []
                meta.update(id=new, file=f"{new}.ogg")
                renamed[voice_id] = new
                write_json(folder / f"{new}.voice.json", meta)
            version_data["voice"] = renamed[voice_id]

        image = ""
        picture = root / "images" / str(source.get("image") or "")
        if source.get("image") and picture.is_file() and picture.suffix.lower() in IMAGE_TYPES:
            image = f"picture{picture.suffix.lower()}"
            shutil.copyfile(picture, folder / image)

        write_json(folder / "character.json", {
            "format": FORMAT, "id": name, "author": author, "version": version or "1.0",
            "updated": date.today().isoformat(), "image": image, "versions": versions})
    errors, warnings = check_character(folder)
    return name, errors, warnings


def report(file: Path, name: str, errors: list[str], warnings: list[str], languages: list[str]) -> str:
    if errors:
        return f"✗ **{file.name}** ({name})\n" + "".join(f"- {line}\n" for line in errors + warnings)
    lines = f"✓ **{file.name}** → `characters/{name}` ({', '.join(languages)})\n"
    return lines + "".join(f"- warning: {line}\n" for line in warnings)


def main() -> int:
    parser = argparse.ArgumentParser(description="Add characters from .haru files.")
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument("--submissions", action="store_true", help="add every .haru file in submissions/, then delete it")
    parser.add_argument("--author", help="author when the file has none (the workflow passes the GitHub user)")
    parser.add_argument("--check-only", action="store_true", help="check the files; change nothing")
    args = parser.parse_args()
    files = sorted(SUBMISSIONS.glob("*.haru")) if args.submissions else args.files
    failed = 0
    with tempfile.TemporaryDirectory() as scratch:
        for file in files:
            # Written in a scratch folder first, so that a bad file never touches a published character.
            name, errors, warnings = add(file, args.author, Path(scratch))
            languages = [] if errors else list(read_json(Path(scratch) / name / "character.json")["versions"])
            print(report(file, name, errors, warnings, languages))
            if errors:
                failed += 1
            elif not args.check_only:
                shutil.rmtree(CHARACTERS / name, ignore_errors=True)
                shutil.move(str(Path(scratch) / name), CHARACTERS / name)
                if args.submissions:
                    file.unlink()
    if not args.check_only:
        INDEX.write_text(index_text(), encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
