"""Prepare a stratified corpus sample for offline model comparison.

Pulls entries from the live DB (headword + embed_text + source), samples
evenly across sources, then guarantees every expected headword from the
eval query files is present (so no query can be a guaranteed miss).

Usage:
    poetry run eval-prepare-corpus
    poetry run eval-prepare-corpus --output data/eval/corpus_sample.jsonl
    poetry run eval-prepare-corpus --sample-size 3000
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

_SOURCES = ["olam_enml", "datuk", "ekkurup"]
_QUERY_FILES = [
    "data/eval/queries_en.jsonl",
    "data/eval/queries_ml.jsonl",
    # Legacy filenames kept as fallback so existing pinned samples still work
    "data/eval/queries.jsonl",
]


def _build_url() -> str:
    user = os.environ.get("DB_USER", "postgres")
    password = os.environ.get("DB_PASSWORD", "")
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    name = os.environ.get("DB_NAME", "linguaalayam")
    return f"postgresql+psycopg2://{user}:{quote_plus(password)}@{host}:{port}/{name}"


def _load_expected_headwords() -> set[str]:
    """Collect all expected_headword values from the eval query files."""
    headwords: set[str] = set()
    for path in _QUERY_FILES:
        p = Path(path)
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                headwords.add(json.loads(line)["expected_headword"].lower())
    return headwords


def prepare_sample(output: Path, sample_size: int) -> None:
    load_dotenv()

    expected_headwords = _load_expected_headwords()
    per_source = sample_size // len(_SOURCES)
    engine = create_engine(_build_url(), pool_pre_ping=True)

    rows: list[dict] = []
    seen_keys: set[tuple[str, str]] = set()  # (source, headword.lower())

    with engine.connect() as conn:
        # Guaranteed inclusion: fetch all entries whose headword is in any query file
        if expected_headwords:
            placeholders = ", ".join(f":hw{i}" for i in range(len(expected_headwords)))
            params = {f"hw{i}": hw for i, hw in enumerate(expected_headwords)}
            result = conn.execute(
                text(
                    f"SELECT headword, embed_text, source FROM dictionary_entries "
                    f"WHERE lower(headword) IN ({placeholders})"
                ),
                params,
            )
            pinned = [{"headword": r[0], "embed_text": r[1], "source": r[2]} for r in result]
            for row in pinned:
                key = (row["source"], row["headword"].lower())
                if key not in seen_keys:
                    seen_keys.add(key)
                    rows.append(row)
            print(f"  Pinned {len(rows)} entries matching eval headwords")

        # Random sample per source (fill remainder after pinned entries)
        for source in _SOURCES:
            already = sum(1 for r in rows if r["source"] == source)
            need = max(0, per_source - already)
            if need == 0:
                continue
            result = conn.execute(
                text(
                    "SELECT headword, embed_text, source FROM dictionary_entries "
                    "WHERE source = :source ORDER BY random() LIMIT :n"
                ),
                {"source": source, "n": need * 2},  # fetch extra to cover dedup
            )
            added = 0
            for r in result:
                key = (r[2], r[0].lower())
                if key not in seen_keys and added < need:
                    seen_keys.add(key)
                    rows.append({"headword": r[0], "embed_text": r[1], "source": r[2]})
                    added += 1
            print(f"  {source}: {already} pinned + {added} random = {already + added}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    source_counts = {s: sum(1 for r in rows if r["source"] == s) for s in _SOURCES}
    print(f"\nSaved {len(rows)} entries to {output}  {source_counts}")
    print("Re-run this command whenever query files change.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare a stratified corpus sample for offline eval (embed + retrieval)."
    )
    parser.add_argument(
        "--output",
        default="data/eval/corpus_sample.jsonl",
        help="Output JSONL path (default: data/eval/corpus_sample.jsonl)",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=5000,
        help="Total entries to sample across all sources (default: 5000)",
    )
    args = parser.parse_args()
    prepare_sample(Path(args.output), args.sample_size)
