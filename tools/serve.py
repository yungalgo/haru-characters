#!/usr/bin/env python3
"""Serve the built site/ on this computer, like GitHub Pages does (with CORS), to try a change in the apps.

    python tools/build.py && python tools/serve.py [--port 8970]
    HARU_KIT_REGISTRY=http://localhost:8970/ haru-kit start --on mac --browser
"""

from __future__ import annotations

import argparse
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8970)
    parser.add_argument("--site", default=str(Path(__file__).resolve().parent.parent / "site"))
    args = parser.parse_args()
    handler = functools.partial(Handler, directory=args.site)
    print(f"serving {args.site} on http://localhost:{args.port}/")
    ThreadingHTTPServer(("127.0.0.1", args.port), handler).serve_forever()


if __name__ == "__main__":
    main()
