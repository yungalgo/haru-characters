#!/usr/bin/env python3
"""Build the published site from entries/: site/index.json, site/packs/<id>.haru, site/images/<id>.<ext>.

    python tools/build.py [--out site]

Only entries that pass tools/check.py are built. The apps of haru-kit read <site URL>/index.json and add a
character by downloading its .haru pack (a ZIP: haru.json, characters/, images/, voices/), the same file as
an export from the apps.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from check import check_entry
from common import ENTRIES, FORMAT, LANGUAGES, read_json

FIXED_TIME = (2020, 1, 1, 0, 0, 0)  # same bytes for the same entry, so the checksum only changes with content


def pack(folder: Path, character: dict) -> bytes:
    """The entry as a .haru file (STORE ZIP)."""
    voice_ids = sorted({v["voice"] for v in character["versions"].values()})
    files: list[tuple[str, bytes]] = [
        ("haru.json", json.dumps({"format": FORMAT, "kind": "haru-kit", "characters": [character["id"]],
                                  "voices": voice_ids}, indent=2).encode() + b"\n"),
        (f"characters/{character['id']}.character.json", (folder / "character.json").read_bytes()),
    ]
    if character.get("image"):
        files.append((f"images/{character['image']}", (folder / character["image"]).read_bytes()))
    for voice_id in voice_ids:
        meta = read_json(folder / "voices" / f"{voice_id}.voice.json")
        file = meta.get("file") or f"{voice_id}.ogg"
        files.append((f"voices/{voice_id}.voice.json", (folder / "voices" / f"{voice_id}.voice.json").read_bytes()))
        files.append((f"voices/{file}", (folder / "voices" / file).read_bytes()))
    out = Path(folder / ".pack.tmp")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as archive:
        for name, data in files:
            archive.writestr(zipfile.ZipInfo(name, FIXED_TIME), data)
    data = out.read_bytes()
    out.unlink()
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ENTRIES.parent / "site"))
    out = Path(parser.parse_args().out)
    shutil.rmtree(out, ignore_errors=True)
    (out / "packs").mkdir(parents=True)
    (out / "images").mkdir()
    entries = []
    for folder in sorted(p for p in ENTRIES.iterdir() if p.is_dir()):
        errors, _ = check_entry(folder)
        if errors:
            print(f"skipped {folder.name}: {errors[0]}", file=sys.stderr)
            continue
        character = read_json(folder / "character.json")
        data = pack(folder, character)
        (out / "packs" / f"{folder.name}.haru").write_bytes(data)
        image = ""
        if character.get("image"):
            image = f"images/{folder.name}{Path(character['image']).suffix.lower()}"
            shutil.copyfile(folder / character["image"], out / image)
        versions = character["versions"]
        languages = [lang for lang in LANGUAGES if lang in versions]
        entries.append({
            "id": character["id"], "author": character["author"], "version": character["version"],
            "updated": character["updated"], "languages": languages,
            "titles": {lang: versions[lang]["title"] for lang in languages},
            "summaries": {lang: versions[lang].get("summary", "") for lang in languages},
            "image": image, "haru": f"packs/{folder.name}.haru", "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    index = {"format": FORMAT, "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "entries": entries}
    (out / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / ".nojekyll").write_text("")
    print(f"built {len(entries)} entries into {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
