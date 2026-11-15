#!/usr/bin/env python3
"""Check the characters in entries/ before they are published.

    python tools/check.py              # every entry
    python tools/check.py ID [ID ...]  # some entries

An entry is a folder entries/<id>/ with:
    character.json                 the character file (format 1), with "author", "version", "updated"
    voices/<voice id>.voice.json   one voice file for each voice that the character's versions use
    voices/<voice id>.ogg          the clip: Ogg Opus, mono, at most 64 kbps, 3 s to 3 min
    <picture>                      optional: the file named by "image" (png, jpg, webp; at most 512 KB)
Errors stop the publication; warnings do not.
"""

from __future__ import annotations

import sys
from pathlib import Path

from common import (CARD_FIELDS, DATE, ENTRIES, FORMAT, ID, IMAGE_TYPES, LANGUAGES, MAX_BITRATE, MAX_CLIP_BYTES,
                    MAX_IMAGE_BYTES, MAX_SECONDS, MIN_SECONDS, probe, read_json)


def check_entry(folder: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    entry = folder.name
    if not ID.match(entry) or len(entry) > 64:
        errors.append(f"folder name {entry!r}: use lower-case letters, digits and '-' (e.g. 'yourname-coach')")
    path = folder / "character.json"
    try:
        character = read_json(path)
    except (OSError, ValueError) as error:
        return [f"character.json: {error}"], warnings

    if character.get("format") != FORMAT:
        errors.append(f"character.json: \"format\" must be {FORMAT}")
    if character.get("id") != entry:
        errors.append(f"character.json: \"id\" must be the folder name {entry!r}")
    for key in ("author", "version", "updated"):
        if not isinstance(character.get(key), str) or not character[key].strip():
            errors.append(f"character.json: \"{key}\" is required")
    if isinstance(character.get("updated"), str) and not DATE.match(character["updated"]):
        errors.append("character.json: \"updated\" must be a date like 2026-11-15")

    image = character.get("image") or ""
    used_files = {"character.json"}
    if image:
        picture = folder / image
        used_files.add(image)
        if "/" in image or Path(image).suffix.lower() not in IMAGE_TYPES or not picture.is_file():
            errors.append(f"image {image!r}: a png, jpg or webp file in the entry folder")
        elif picture.stat().st_size > MAX_IMAGE_BYTES:
            errors.append(f"image {image!r}: at most {MAX_IMAGE_BYTES // 1000} KB")

    versions = character.get("versions")
    if not isinstance(versions, dict) or not versions:
        errors.append("character.json: \"versions\" needs at least one language")
        versions = {}
    voices_needed: dict[str, str] = {}
    for lang, version in versions.items():
        where = f"version {lang!r}"
        if lang not in LANGUAGES:
            errors.append(f"{where}: language must be one of {', '.join(LANGUAGES)}")
        if not isinstance(version, dict):
            errors.append(f"{where}: not an object")
            continue
        if not str(version.get("title") or "").strip():
            errors.append(f"{where}: \"title\" is empty")
        card = version.get("card")
        if not isinstance(card, dict) or set(card) != set(CARD_FIELDS):
            errors.append(f"{where}: \"card\" must have exactly the 7 fields: {', '.join(CARD_FIELDS)}")
        elif not all(isinstance(card[k], str) for k in CARD_FIELDS):
            errors.append(f"{where}: card fields must be text")
        elif not card["persona"].strip():
            errors.append(f"{where}: \"persona\" is empty")
        voice = version.get("voice")
        if not isinstance(voice, str) or not voice:
            errors.append(f"{where}: \"voice\" is missing")
        else:
            voices_needed[voice] = lang

    for voice_id, lang in voices_needed.items():
        meta_path = folder / "voices" / f"{voice_id}.voice.json"
        used_files.add(f"voices/{voice_id}.voice.json")
        try:
            voice = read_json(meta_path)
        except (OSError, ValueError):
            errors.append(f"voice {voice_id!r}: voices/{voice_id}.voice.json is missing or broken")
            continue
        if voice.get("format") != FORMAT or voice.get("id") != voice_id:
            errors.append(f"voice {voice_id!r}: needs \"format\": {FORMAT} and \"id\": {voice_id!r}")
        if not str(voice.get("name") or "").strip():
            errors.append(f"voice {voice_id!r}: \"name\" is empty")
        if voice.get("language") not in LANGUAGES:
            errors.append(f"voice {voice_id!r}: \"language\" must be one of {', '.join(LANGUAGES)}")
        elif voice["language"] != lang:
            warnings.append(f"voice {voice_id!r} speaks {voice['language']!r} but is used by the {lang!r} version")
        file = str(voice.get("file") or f"{voice_id}.ogg")
        clip = folder / "voices" / file
        used_files.add(f"voices/{file}")
        if not file.endswith(".ogg") or not clip.is_file():
            errors.append(f"voice {voice_id!r}: the clip must be voices/{voice_id}.ogg (Ogg Opus); "
                          "convert it with: python tools/add.py, or ffmpeg -i IN -ac 1 -c:a libopus -b:a 48k OUT.ogg")
            continue
        info = probe(clip)
        if info.get("codec") != "opus":
            errors.append(f"voice {voice_id!r}: the clip is {info.get('codec') or 'unreadable'}, not Opus")
        if info.get("channels") != 1:
            errors.append(f"voice {voice_id!r}: the clip must be mono (1 channel)")
        if not MIN_SECONDS <= info.get("seconds", 0) <= MAX_SECONDS + 0.5:
            errors.append(f"voice {voice_id!r}: the clip is {info.get('seconds', 0):.1f} s; "
                          f"use {MIN_SECONDS:g} s to {MAX_SECONDS / 60:g} min")
        if info.get("bitrate", 0) > MAX_BITRATE:
            errors.append(f"voice {voice_id!r}: {info['bitrate'] // 1000} kbps; at most {MAX_BITRATE // 1000} kbps")
        if clip.stat().st_size > MAX_CLIP_BYTES:
            errors.append(f"voice {voice_id!r}: at most {MAX_CLIP_BYTES // 1000} KB")

    extra = sorted(str(p.relative_to(folder)) for p in folder.rglob("*") if p.is_file()
                   and str(p.relative_to(folder)) not in used_files and p.name != ".DS_Store")
    if extra:
        errors.append(f"files that the character does not use: {', '.join(extra)}")
    return errors, warnings


def main(argv: list[str]) -> int:
    folders = [ENTRIES / name for name in argv] if argv else sorted(p for p in ENTRIES.iterdir() if p.is_dir())
    failed = 0
    for folder in folders:
        if not folder.is_dir():
            print(f"✗ {folder.name}: no such entry")
            failed += 1
            continue
        errors, warnings = check_entry(folder)
        print(f"{'✗' if errors else '✓'} {folder.name}")
        for line in errors:
            print(f"    error: {line}")
        for line in warnings:
            print(f"    warning: {line}")
        failed += bool(errors)
    print(f"\n{len(folders) - failed} of {len(folders)} entries pass.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
