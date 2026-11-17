#!/usr/bin/env python3
"""Turn a .haru file (exported from the haru-kit web app or Mac app) into a character of this registry.

    python tools/add.py Coach.haru --github USER [--check-only]
    python tools/add.py --submissions --github USER   # every file in submissions/ (the publish workflow)

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
from common import CHARACTERS, FORMAT, ID, IMAGE_TYPES, INDEX, ROOT, read_json, to_opus, write_json

SUBMISSIONS = ROOT / "submissions"
MAX_ARCHIVE_BYTES = 25 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 60 * 1024 * 1024
MAX_ENTRIES = 64


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


def safe_filename(name: str) -> bool:
    return bool(name) and name not in (".", "..") and "/" not in name and "\\" not in name and "\0" not in name


def safe_extract(file: Path, target: Path) -> None:
    """Extract a .haru ZIP archive after checking size, entry count, symlinks, and path bounds."""
    if file.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("archive too large")
    with zipfile.ZipFile(file) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_ENTRIES:
            raise ValueError("too many entries")
        total = 0
        for info in infos:
            unix_type = (info.external_attr >> 16) & 0o170000
            if unix_type == 0o120000:
                raise ValueError("symbolic links are not allowed")
            name = info.filename
            if not name or name.startswith("/") or "\\" in name or "\0" in name or ".." in name.split("/"):
                raise ValueError(f"unsafe path: {name}")
            total += info.file_size
            if total > MAX_UNCOMPRESSED_BYTES:
                raise ValueError("uncompressed size exceeds limit")
        for info in infos:
            if info.is_dir():
                continue
            dest = (target / info.filename).resolve()
            if not dest.is_relative_to(target.resolve()):
                raise ValueError("escaped target directory")
            dest.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as src, open(dest, "wb") as dst:
                copied = 0
                while chunk := src.read(65536):
                    copied += len(chunk)
                    if copied > MAX_UNCOMPRESSED_BYTES:
                        raise ValueError("stream exceeds uncompressed limit")
                    dst.write(chunk)


def add(file: Path, github: str, target_root: Path) -> tuple[str, list[str], list[str], str]:
    """Write the character of `file`, merged with the published one, under target_root/<name>/.

    Rules: a name belongs to the GitHub user who first uploaded it (the "owner"). Each language version
    records who wrote it ("by"). An upload may add a language that the character does not have, or replace a
    language version that the same user wrote; it never replaces another person's version or voice. Only the
    owner changes the picture and the author name. Returns (name, errors, warnings, what the merge does)."""
    with tempfile.TemporaryDirectory() as tmp:
        try:
            root = Path(tmp).resolve()
            safe_extract(file, root)
            index = read_json(root / "haru.json")
            assert index.get("kind") == "haru-kit" and isinstance(index.get("characters"), list)
            assert len(index["characters"]) == 1
            char_id = str(index["characters"][0])
            assert safe_filename(char_id)
            source = read_json(root / "characters" / f"{char_id}.character.json")
            versions = source["versions"]
            assert isinstance(versions, dict) and versions
        except Exception:  # noqa: BLE001 - any broken file gets the same answer
            return file.stem, ["this is not a .haru file with one character (in the app: Export the character)"], [], ""
        # The published character that this file updates: its id (a character added from Browse keeps it),
        # else the English (or first) title.
        first = versions.get("en") or next(iter(versions.values()))
        raw_name = str(source.get("id") or "")
        name = raw_name if ID.match(raw_name) and (CHARACTERS / raw_name / "character.json").is_file() else ""
        if not name:
            name = slug(str(first.get("title") or "")) or slug(file.stem) or "character"
        old_folder = CHARACTERS / name
        existing = read_json(old_folder / "character.json") if (old_folder / "character.json").is_file() else None
        owner = (existing or {}).get("owner") or (existing or {}).get("author") if existing else github
        is_owner = github == owner

        # A version with the same text as the published one is "unchanged" (a character added from Browse and
        # exported again carries all its languages); it keeps the published version and voice.
        published = (existing or {}).get("versions") or {}
        same = lambda a, b: all(a.get(k, "") == b.get(k, "") for k in ("title", "summary", "card"))  # noqa: E731
        unchanged = {lang for lang, v in versions.items() if lang in published and same(v, published[lang])}
        versions = {lang: v for lang, v in versions.items() if lang not in unchanged}
        if not versions:
            return name, [f"nothing new: every language version is the same as the published {name!r}"], [], ""
        errors = []
        for lang in versions:
            old = published.get(lang)
            if old is not None and github != (old.get("by") or owner):
                errors.append(f"the {lang!r} version of {name!r} was written by {old.get('by') or owner}; "
                              "you can add languages that it does not have, but not change this one")
        if errors:
            return name, errors, [], ""

        folder = target_root / name
        shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True)
        merged: dict[str, dict] = {}
        used_ids: set[str] = set()
        for lang, kept in ((existing or {}).get("versions") or {}).items():
            if lang in versions:
                continue
            merged[lang] = kept  # another language: stays as published, with its voice
            for suffix in (".voice.json", ".ogg"):
                shutil.copyfile(old_folder / f"{kept['voice']}{suffix}", folder / f"{kept['voice']}{suffix}")
            used_ids.add(kept["voice"])

        voices_dir = (root / "voices").resolve()
        renamed: dict[str, str] = {}
        for lang, version_data in versions.items():
            voice_id = str(version_data.get("voice") or "")
            if voice_id not in renamed:
                try:
                    assert safe_filename(voice_id)
                    meta = read_json(voices_dir / f"{voice_id}.voice.json")
                    clip_name = str(meta.get("file") or f"{voice_id}.flac")
                    assert safe_filename(clip_name)
                    clip = (voices_dir / clip_name).resolve()
                    assert clip.is_relative_to(voices_dir) and clip.is_file()
                    new = f"{name}-{meta.get('language') or lang}"
                    while new in used_ids:
                        new += "-2"
                    to_opus(clip, folder / f"{new}.ogg")
                except Exception:  # noqa: BLE001
                    return name, [f"the {lang!r} version's voice is missing or cannot be read"], [], ""
                meta.update(id=new, file=f"{new}.ogg")
                meta.setdefault("author", github)
                renamed[voice_id] = new
                used_ids.add(new)
                write_json(folder / f"{new}.voice.json", meta)
            merged[lang] = {**version_data, "voice": renamed[voice_id], "by": github}

        image = (existing or {}).get("image", "")
        images_dir = (root / "images").resolve()
        raw_image = str(source.get("image") or "")
        picture = (images_dir / raw_image).resolve() if safe_filename(raw_image) else None
        if (is_owner and picture is not None and picture.is_relative_to(images_dir)
                and picture.is_file() and picture.suffix.lower() in IMAGE_TYPES):
            image = f"picture{picture.suffix.lower()}"
            shutil.copyfile(picture, folder / image)
        elif image:
            shutil.copyfile(old_folder / image, folder / image)
        else:
            return name, ["the character has no picture: add one in the app (png, jpg or webp, at most 512 KB), "
                          "then export it again"], [], ""

        author = str(source.get("author") or github) if is_owner else existing["author"]
        version = "1.0"
        if existing:
            version = next_version(existing.get("version", ""))
        write_json(folder / "character.json", {
            "format": FORMAT, "id": name, "owner": owner, "author": author, "version": version,
            "updated": date.today().isoformat(), "image": image,
            "versions": {lang: merged[lang] for lang in sorted(merged)}})
        old_langs = set(((existing or {}).get("versions") or {}))
        added = ", ".join(sorted(set(versions) - old_langs))
        changed = ", ".join(sorted(set(versions) & old_langs))
        parts = [f"adds {added}"] if added else []
        parts += [f"updates {changed} (written by you)"] if changed else []
        if not existing:
            what = f"new character, owner {github} ({', '.join(sorted(versions))})"
        else:
            whose = "yours" if is_owner else f"owner {owner}"
            what = f"{' and '.join(parts)} in {name} ({whose}); version {version}"
    errors, warnings = check_character(folder)
    return name, errors, warnings, what


def report(file: Path, name: str, errors: list[str], warnings: list[str], what: str) -> str:
    if errors:
        return f"✗ **{file.name}** ({name})\n" + "".join(f"- {line}\n" for line in errors + warnings)
    lines = f"✓ **{file.name}** → `characters/{name}`: {what}\n"
    return lines + "".join(f"- warning: {line}\n" for line in warnings)


def main() -> int:
    parser = argparse.ArgumentParser(description="Add characters from .haru files.")
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument("--submissions", action="store_true", help="add every .haru file in submissions/, then delete it")
    parser.add_argument("--github", required=True, help="GitHub user of the upload (owner of a new name)")
    parser.add_argument("--check-only", action="store_true", help="check the files; change nothing")
    args = parser.parse_args()
    files = sorted(SUBMISSIONS.glob("*.haru")) if args.submissions else args.files
    failed = 0
    with tempfile.TemporaryDirectory() as scratch:
        for file in files:
            # Written in a scratch folder first, so that a bad file never touches a published character.
            name, errors, warnings, what = add(file, args.github, Path(scratch))
            print(report(file, name, errors, warnings, what))
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
