#!/usr/bin/env python3
"""Write characters/index.json (the list that the apps read), and with --site, the folder that GitHub Pages
publishes: index.json and packs/<name>.haru.

    python tools/build.py              # update characters/index.json (commit it with your character)
    python tools/build.py --site site  # also build the published folder (the publish workflow does this)

A pack is the character as a .haru file (a ZIP: haru.json, characters/, images/, voices/), the same file as an
export from the haru-kit apps. Only characters that pass tools/check.py are listed.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import zipfile
from io import BytesIO
from pathlib import Path

from check import check_character
from common import FORMAT, INDEX, LANGUAGES, character_folders, dump_json, read_json

FIXED_TIME = (2020, 1, 1, 0, 0, 0)  # the same bytes for the same character, so the checksum changes only with it


def pack(folder: Path) -> bytes:
    character = read_json(folder / "character.json")
    voice_ids = sorted({v["voice"] for v in character["versions"].values()})
    files = [("haru.json", dump_json({"format": FORMAT, "kind": "haru-kit", "characters": [character["id"]],
                                      "voices": voice_ids}).encode()),
             (f"characters/{character['id']}.character.json", (folder / "character.json").read_bytes())]
    if character.get("image"):
        files.append((f"images/{character['image']}", (folder / character["image"]).read_bytes()))
    for voice_id in voice_ids:
        files.append((f"voices/{voice_id}.voice.json", (folder / f"{voice_id}.voice.json").read_bytes()))
        files.append((f"voices/{voice_id}.ogg", (folder / f"{voice_id}.ogg").read_bytes()))
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as archive:
        for name, data in files:
            archive.writestr(zipfile.ZipInfo(name, FIXED_TIME), data)
    return buffer.getvalue()


def entries() -> list[tuple[Path, dict, bytes]]:
    """The characters that pass the checks, with their index entry and pack."""
    out = []
    for folder in character_folders():
        if check_character(folder)[0]:
            continue
        character = read_json(folder / "character.json")
        data = pack(folder)
        versions = character["versions"]
        languages = [lang for lang in LANGUAGES if lang in versions]
        out.append((folder, {
            "id": character["id"], "author": character["author"], "version": character["version"],
            "updated": character["updated"], "languages": languages,
            "titles": {lang: versions[lang]["title"] for lang in languages},
            "summaries": {lang: versions[lang].get("summary", "") for lang in languages},
            "image": f"{folder.name}/{character['image']}" if character.get("image") else "",
            "haru": f"packs/{folder.name}.haru", "size": len(data), "sha256": hashlib.sha256(data).hexdigest(),
        }, data))
    return out


def index_text() -> str:
    return dump_json({"format": FORMAT, "entries": [entry for _, entry, _ in entries()]})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", help="also build the published folder here")
    args = parser.parse_args()
    built = entries()
    text = dump_json({"format": FORMAT, "entries": [entry for _, entry, _ in built]})
    INDEX.write_text(text, encoding="utf-8")
    print(f"characters/index.json: {len(built)} characters")
    if args.site:
        site = Path(args.site)
        shutil.rmtree(site, ignore_errors=True)
        (site / "packs").mkdir(parents=True)
        (site / "index.json").write_text(text, encoding="utf-8")
        for folder, entry, data in built:
            (site / entry["haru"]).write_bytes(data)
            if entry["image"]:
                (site / folder.name).mkdir()
                shutil.copyfile(folder / Path(entry["image"]).name, site / entry["image"])
        (site / ".nojekyll").write_text("")
        print(f"built {site}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
