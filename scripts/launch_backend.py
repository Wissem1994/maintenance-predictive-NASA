"""Backend used by the Windows launcher, with a graceful file-based stop request."""
from __future__ import annotations

import argparse
from pathlib import Path
from threading import Event, Thread

import uvicorn

from scripts.init_db import main as initialize_database


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stop-file", required=True, type=Path)
    args = parser.parse_args()
    initialize_database()
    server = uvicorn.Server(uvicorn.Config("backend.app.main:app", host="127.0.0.1", port=8000))
    finished = Event()

    def watch_stop_request() -> None:
        while not finished.wait(0.25):
            if args.stop_file.exists():
                server.should_exit = True
                return

    watcher = Thread(target=watch_stop_request, daemon=True)
    watcher.start()
    try:
        server.run()
    finally:
        finished.set()
        watcher.join(timeout=1)


if __name__ == "__main__":
    main()
