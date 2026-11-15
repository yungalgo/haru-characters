# haru-characters

Shared characters for [haru-kit](https://github.com/yungalgo/haru-kit). In the haru-kit web app or Mac app, **Browse characters** shows the characters of this repository, and adds one to your library with one click.

```
characters/
  index.json          the list that the apps read (tools/build.py writes it)
  kai/                one folder for each character
    character.json    the character: a card and a voice for each language
    kai-en.ogg        a voice clip (Ogg Opus)
    kai-en.voice.json the voice's name and language
    …
tools/                checks and helpers (Python, ffmpeg)
```

When a pull request is merged, GitHub checks the characters and publishes the list. The apps show the new character a minute or two later.

## Add your character

1. **Make the character in haru-kit.** Write a version for each language that you want, and give each version a voice in that language. 10 to 30 seconds of voice is enough (up to 3 minutes is possible).
2. **Export it**: "Export the character (.haru)".
3. **Add it here** (needs Python 3.11 or newer and ffmpeg):
   ```bash
   git clone https://github.com/yungalgo/haru-characters && cd haru-characters
   python tools/add.py ~/Downloads/Coach.haru --author yourname
   ```
   This writes `characters/coach/`, converts the voices to Ogg Opus, checks everything, and updates `characters/index.json`.
4. **Open a pull request** with these changes. The checks run again on GitHub. The owner listens, reads, and merges.

To change your character later, change its folder, raise `"version"` in `character.json`, run `python tools/build.py`, and open a pull request. Apps that have the old version show **Update**.

## Rules

- **Only voices that you may share**: your own voice, a voice from a service that permits it, or a voice with the speaker's permission.
- The checks test the rest:
  - `character.json`: `"format": 1`, `"id"` equal to the folder name (lower-case letters, digits, `-`), and `"author"`, `"version"` and `"updated"` (a date such as `2026-11-15`).
  - Each language version: a title, the 7 card fields (persona, name, gender, backchannel, other_name, relationship, situation; the persona is not empty), and a voice.
  - Voice clips: **Ogg Opus, mono, at most 64 kbps** (48 kbps recommended), **3 seconds to 3 minutes**, at most 1.5 MB. Convert one by hand: `ffmpeg -i voice.wav -ac 1 -c:a libopus -b:a 48k voice.ogg`.
  - Optional picture: png, jpg or webp, at most 512 KB, named in `"image"`.
  - No other files in the folder, and `characters/index.json` is up to date.
- A voice in another language than its version gives a warning, not an error: the model speaks a language best with a voice in that language.

## For the owner

- `python tools/check.py`: check everything. `python tools/build.py`: update `characters/index.json`.
- Try changes in the apps before you merge: `python tools/build.py --site site && python tools/serve.py`, then `HARU_KIT_REGISTRY=http://localhost:8970/ haru-kit start --on mac --browser`.
- Publishing: the workflow `publish.yml` runs on each push to `main` and publishes `index.json` and one `.haru` file for each character on GitHub Pages (`https://yungalgo.github.io/haru-characters/`). The repository is public, so these runs are free.
