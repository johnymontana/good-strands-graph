"""Fetch author data for the Goodreads 10k loader.

Downloads:
  1. S3 10k-books-authors.json and writes data/10k-book-authors.json (JSONL)
     with one line per book: {"book_id": "<id>", "author_ids": ["<id1>", ...]}
  2. Gist 10k-books-filtered_authors.json to data/10k-authors-demo.json (JSONL)

Run from repo root or backend: python backend/scripts/fetch_author_data.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from urllib.request import urlopen
except ImportError:
    urlopen = None  # type: ignore

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
BOOKS_WITH_AUTHORS_URL = "https://devrel-goodreads-graph.s3.us-west-2.amazonaws.com/10k-books-authors.json"
AUTHORS_URL = (
    "https://gist.githubusercontent.com/jpadams/5e3322fce95671f61db447f896f90a6d/"
    "raw/15408f58c4e7348f88a375d15dfab16be0eec0f3/10k-books-filtered_authors.json"
)
BOOK_AUTHORS_FILE = DATA_DIR / "10k-book-authors.json"
AUTHORS_FILE = DATA_DIR / "10k-authors-demo.json"


def fetch_url(url: str) -> str:
    with urlopen(url, timeout=60) as resp:  # type: ignore
        return resp.read().decode("utf-8")


def main() -> None:
    if urlopen is None:
        print("Error: urllib.request.urlopen not available")
        sys.exit(1)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("Fetching books with authors from S3...")
    text = fetch_url(BOOKS_WITH_AUTHORS_URL)
    with open(BOOK_AUTHORS_FILE, "w", encoding="utf-8") as f:
        f.write(text)
    num_lines = len([l for l in text.strip().split("\n") if l.strip()])
    print(f"  Wrote {BOOK_AUTHORS_FILE} ({num_lines:,} books)")

    print("Fetching author details from Gist...")
    text = fetch_url(AUTHORS_URL)
    with open(AUTHORS_FILE, "w", encoding="utf-8") as f:
        f.write(text)
    num_lines = len([l for l in text.strip().split("\n") if l.strip()])
    print(f"  Wrote {AUTHORS_FILE} ({num_lines:,} authors)")

    print("Done. Run make load-data to load Author nodes and AUTHORED.")


if __name__ == "__main__":
    main()
