# haru-characters

Shared characters for [haru-kit](https://github.com/yungalgo/haru-kit): people who talk with Haru-4B in the haru-kit web app or Mac app can add these characters with **Browse characters**.

Each character is one folder in `entries/`. When the owner merges a pull request, a GitHub Action checks every entry, builds the list (`index.json`) and the `.haru` files, and publishes them on GitHub Pages. The apps read the list from there, so a merged character shows in the apps a minute or two later.

## Add your character

1. **Make the character in haru-kit.** Write a version for each language that you want, and give each version a voice in that language. A voice clip of 10 to 30 seconds is enough (up to 3 minutes is possible).
2. **Export it** with "Export the character (.haru)".
3. **Make the entry** (needs Python 3.11 or newer and ffmpeg):
   ```bash
   git clone https://github.com/yungalgo/haru-characters && cd haru-characters
   python tools/add.py ~/Downloads/Coach.haru --author yourname --name coach
   ```
   This writes `entries/yourname-coach/`, converts the voices to Ogg Opus, and runs the checks.
4. **Open a pull request** with the new folder. The checks run again on GitHub. The owner listens, reads, and merges.

To change your character later, change its folder, raise `"version"` in `character.json`, and open a pull request. Apps that have the old version show **Update**.

## Rules

- **Only voices that you may share**: your own voice, a voice that you made with a voice service that permits this, or a voice with the speaker's permission.
- **Format** (the checks test all of this):
  - `entries/<id>/character.json`: `"format": 1`, `"id"` equal to the folder name (lower-case letters, digits, `-`), and `"author"`, `"version"` and `"updated"` (a date such as `2026-11-15`).
  - Each language version: a title, the 7 card fields (persona, name, gender, backchannel, other_name, relationship, situation; the persona is not empty), and a voice.
  - Voices: `voices/<voice id>.voice.json` and `voices/<voice id>.ogg`. The clip must be **Ogg Opus, mono, at most 64 kbps** (48 kbps recommended), **3 seconds to 3 minutes**, at most 1.5 MB.
  - Optional picture: png, jpg or webp, at most 512 KB, named in `"image"`.
  - No other files.
- A voice in another language than its version gives a warning, not an error. The model speaks a language best with a voice in that language.

Convert any audio file by hand: `ffmpeg -i voice.wav -ac 1 -c:a libopus -b:a 48k voice.ogg`

## For the owner

- `python tools/check.py` checks all entries; `python tools/build.py` builds `site/`; `python tools/serve.py` serves it on `http://localhost:8970/` so that you can try it in the apps: `HARU_KIT_REGISTRY=http://localhost:8970/ haru-kit start --on mac --browser`.
- Publishing: in the repo settings, set **Pages → Source: GitHub Actions**. The workflow `publish.yml` runs on each push to `main`.
- GitHub Pages needs a public repository on a free plan (private repositories need a paid plan for Pages).
