# Tools (for the owner)

Needs Python 3.11 or newer and ffmpeg.

| Command | What it does |
| --- | --- |
| `python tools/add.py FILE.haru [--author NAME]` | Turn a `.haru` file into `characters/<name>/` (voices to Ogg Opus, 48 kbps mono) and update `characters/index.json`. A character with the same name is replaced and its version goes up. |
| `python tools/add.py --check-only FILE.haru` | Check a file; change nothing. |
| `python tools/check.py` | Check all characters, and that `characters/index.json` is up to date. |
| `python tools/build.py [--site site]` | Update `characters/index.json`; with `--site`, also build the published folder (`index.json`, `packs/<name>.haru`). |
| `python tools/serve.py` | Serve `site/` on `http://localhost:8970/`. Try it with `HARU_KIT_REGISTRY=http://localhost:8970/ haru-kit start --on mac --browser`. |

## How it runs on GitHub

- **Pull request** (`check.yml`): the `.haru` files that the pull request adds to `submissions/` are checked with `add.py --check-only`, and the result is a comment on the pull request. It runs this repository's tools, not code from the pull request.
- **Merge** (`publish.yml`): `add.py --submissions` turns the uploaded files into character folders and commits them, then `check.py` runs, and `build.py --site` publishes on GitHub Pages: `https://yungalgo.github.io/haru-characters/`. The apps read `index.json` there.

## Rules that the checks use

- `character.json`: format 1; `id` = folder name (lower-case letters, digits, `-`); `author`, `version`, `updated`; at least one language version with a title, the 7 card fields (persona not empty) and a voice.
- Voices: `<voice id>.voice.json` and `<voice id>.ogg`: Ogg Opus, mono, at most 64 kbps, 3 s to 3 min, at most 1.5 MB. A voice in another language than its version is a warning.
- Optional picture: png, jpg or webp, at most 512 KB. No other files in a character's folder.
