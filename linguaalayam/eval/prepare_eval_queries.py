"""Generate eval query files from the actual corpus data in the DB.

All queries are derived from real entries — nothing is hand-crafted.
Writes two JSONL files:

  data/eval/queries_en.jsonl   — queries whose input is English or Manglish
  data/eval/queries_ml.jsonl   — queries whose input is Malayalam

Intent taxonomy:

  Same-corpus (single source):
    en_from_en_exact     Olam/Ekkurup EN headword → same EN headword
    en_from_en_semantic  Ekkurup EN synonyms → EN headword
    ml_from_ml_exact     Datuk ML headword → same ML headword
    ml_from_ml_semantic  Datuk ML definition → ML headword

  Cross-corpus (Ekkurup EN↔ML bridge + Datuk verification):
    en_from_ml_exact     ML word (from Ekkurup translation) → EN headword
    ml_from_en_exact     EN headword → ML headword (Datuk)
    ml_from_en_semantic  EN synonyms (Ekkurup) → ML headword (Datuk)
    en_from_ml_semantic  ML definition (Datuk) → EN headword (Ekkurup)

  Manglish (Latin-script romanised Malayalam):
    ml_from_manglish     ISO-romanised ML headword → ML headword
    en_from_manglish     ISO-romanised ML headword → EN headword

Usage:
    poetry run eval-prepare-queries
    poetry run eval-prepare-queries --per-intent 15 --seed 42
    poetry run eval-prepare-queries --out-en data/eval/queries_en.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from linguaalayam.transliteration import malayalam_to_roman

_DEFAULT_PER_INTENT = 10
_MALAYALAM_RE = re.compile(r"[ഀ-ൿ]")


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _build_url() -> str:
    user = os.environ.get("DB_USER", "postgres")
    password = os.environ.get("DB_PASSWORD", "")
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    name = os.environ.get("DB_NAME", "linguaalayam")
    return f"postgresql+psycopg2://{user}:{quote_plus(password)}@{host}:{port}/{name}"


def _sample_entries(conn, source: str, n: int, seed: int) -> list[dict]:
    """Sample n random entries from a given source."""
    rows = conn.execute(
        text(
            "SELECT headword, embed_text FROM dictionary_entries "
            "WHERE source = :source ORDER BY random() LIMIT :n"
        ),
        {"source": source, "n": n * 3},  # over-fetch to allow post-filtering
    ).fetchall()
    rng = random.Random(seed)
    rng.shuffle(rows)
    return [{"headword": r[0], "embed_text": r[1]} for r in rows]


# ---------------------------------------------------------------------------
# embed_text parsers
# ---------------------------------------------------------------------------


def _parse_definitions(embed_text: str) -> list[str]:
    """Extract definition strings from a Datuk/Olam embed_text block.

    Format::

        word: headword
          [pos] defn1; defn2; ...
          [pos] defn3; ...

    Returns individual definition phrases split on ``; ``.
    """
    definitions: list[str] = []
    for line in embed_text.splitlines():
        line = line.strip()
        m = re.match(r"^\[.+?\]\s*(.+)$", line)
        if not m:
            continue
        text = m.group(1)
        # Strip language prefix used by Ekkurup ("en: ...", "ml: ...")
        text = re.sub(r"^(en|ml):\s*", "", text)
        for part in re.split(r";\s*", text):
            part = part.strip().strip(";").strip()
            if part and len(part) > 2:
                definitions.append(part)
    return definitions


def _parse_ekkurup_en_synonyms(embed_text: str) -> list[str]:
    """Extract English synonym strings from an Ekkurup embed_text block."""
    syns: list[str] = []
    for line in embed_text.splitlines():
        line = line.strip()
        m = re.match(r"^\[.+?\]\s*en:\s*(.+)$", line)
        if not m:
            continue
        for part in re.split(r";\s*|,\s*", m.group(1)):
            part = part.strip()
            if part and len(part) > 2:
                syns.append(part)
    return syns


def _parse_ekkurup_ml_translations(embed_text: str) -> list[str]:
    """Extract Malayalam translation words from an Ekkurup embed_text block."""
    translations: list[str] = []
    for line in embed_text.splitlines():
        line = line.strip()
        m = re.match(r"^\[.+?\]\s*ml:\s*(.+)$", line)
        if not m:
            continue
        for part in re.split(r";\s*|,\s*", m.group(1)):
            part = part.strip()
            if _MALAYALAM_RE.search(part) and len(part) > 1:
                translations.append(part)
    return translations


# ---------------------------------------------------------------------------
# Intent generators
# ---------------------------------------------------------------------------


def _make_record(query: str, expected: str, intent: str) -> dict:
    return {"query": query, "expected_headword": expected, "intent": intent, "source": None}


def gen_en_from_en_exact(entries: list[dict], n: int) -> list[dict]:
    """EN headword → EN headword (trivially correct, tests exact tool)."""
    return [_make_record(e["headword"], e["headword"], "en_from_en_exact") for e in entries[:n]]


def gen_en_from_en_semantic(entries: list[dict], n: int) -> list[dict]:
    """Ekkurup EN synonym → EN headword."""
    records: list[dict] = []
    for e in entries:
        if len(records) >= n:
            break
        syns = _parse_ekkurup_en_synonyms(e["embed_text"])
        # Use a synonym that is NOT the headword itself
        candidates = [s for s in syns if s.lower() != e["headword"].lower()]
        if not candidates:
            continue
        records.append(_make_record(candidates[0], e["headword"], "en_from_en_semantic"))
    return records


def gen_ml_from_ml_exact(entries: list[dict], n: int) -> list[dict]:
    """ML headword → ML headword."""
    return [_make_record(e["headword"], e["headword"], "ml_from_ml_exact") for e in entries[:n]]


def gen_ml_from_ml_semantic(entries: list[dict], n: int) -> list[dict]:
    """Datuk ML definition → ML headword."""
    records: list[dict] = []
    for e in entries:
        if len(records) >= n:
            break
        defns = [d for d in _parse_definitions(e["embed_text"]) if _MALAYALAM_RE.search(d)]
        if not defns:
            continue
        records.append(_make_record(defns[0], e["headword"], "ml_from_ml_semantic"))
    return records


def gen_cross_intents(
    ekkurup_entries: list[dict],
    datuk_hw_set: set[str],
    n: int,
) -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict], list[dict]]:
    """Generate all cross-corpus intents using Ekkurup as the EN↔ML bridge.

    Returns six lists:
        en_from_ml_exact, ml_from_en_exact,
        ml_from_en_semantic, en_from_ml_semantic,
        ml_from_manglish, en_from_manglish
    """
    en_from_ml_exact: list[dict] = []
    ml_from_en_exact: list[dict] = []
    ml_from_en_semantic: list[dict] = []
    en_from_ml_semantic: list[dict] = []
    ml_from_manglish: list[dict] = []
    en_from_manglish: list[dict] = []

    datuk_hw_lower = {hw.lower(): hw for hw in datuk_hw_set}

    for e in ekkurup_entries:
        if all(
            len(lst) >= n
            for lst in [
                en_from_ml_exact,
                ml_from_en_exact,
                ml_from_en_semantic,
                en_from_ml_semantic,
                ml_from_manglish,
                en_from_manglish,
            ]
        ):
            break

        en_hw = e["headword"]
        ml_translations = _parse_ekkurup_ml_translations(e["embed_text"])
        en_synonyms = _parse_ekkurup_en_synonyms(e["embed_text"])

        # Find ML translations that exist as Datuk headwords
        ml_headwords = [
            datuk_hw_lower[t.lower()] for t in ml_translations if t.lower() in datuk_hw_lower
        ]
        if not ml_headwords:
            continue

        ml_hw = ml_headwords[0]
        romanised = malayalam_to_roman(ml_hw)

        if len(en_from_ml_exact) < n:
            en_from_ml_exact.append(_make_record(ml_hw, en_hw, "en_from_ml_exact"))
        if len(ml_from_en_exact) < n:
            ml_from_en_exact.append(_make_record(en_hw, ml_hw, "ml_from_en_exact"))
        if len(ml_from_en_semantic) < n and en_synonyms:
            syn = next((s for s in en_synonyms if s.lower() != en_hw.lower()), en_synonyms[0])
            ml_from_en_semantic.append(_make_record(syn, ml_hw, "ml_from_en_semantic"))
        if len(ml_from_manglish) < n:
            ml_from_manglish.append(_make_record(romanised, ml_hw, "ml_from_manglish"))
        if len(en_from_manglish) < n:
            en_from_manglish.append(_make_record(romanised, en_hw, "en_from_manglish"))

    # en_from_ml_semantic: Datuk ML definition → Ekkurup EN headword
    # Derived separately below (needs Datuk entries joined to the EN headword)
    return (
        en_from_ml_exact,
        ml_from_en_exact,
        ml_from_en_semantic,
        en_from_ml_semantic,
        ml_from_manglish,
        en_from_manglish,
    )


def gen_en_from_ml_semantic(
    ekkurup_entries: list[dict],
    datuk_entries_by_hw: dict[str, dict],
    n: int,
) -> list[dict]:
    """Datuk ML definition → EN headword.

    Uses the Ekkurup bridge to get (ML headword → EN headword) mapping,
    then pulls the ML definition from Datuk.
    """
    records: list[dict] = []
    datuk_hw_lower = {hw.lower(): hw for hw in datuk_entries_by_hw}

    for e in ekkurup_entries:
        if len(records) >= n:
            break
        ml_translations = _parse_ekkurup_ml_translations(e["embed_text"])
        for ml_t in ml_translations:
            if ml_t.lower() not in datuk_hw_lower:
                continue
            ml_hw = datuk_hw_lower[ml_t.lower()]
            datuk_entry = datuk_entries_by_hw.get(ml_hw)
            if not datuk_entry:
                continue
            defns = [
                d for d in _parse_definitions(datuk_entry["embed_text"]) if _MALAYALAM_RE.search(d)
            ]
            if not defns:
                continue
            records.append(_make_record(defns[0], e["headword"], "en_from_ml_semantic"))
            break
    return records


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def prepare_queries(
    out_en: Path,
    out_ml: Path,
    per_intent: int,
    seed: int,
) -> None:
    load_dotenv()
    engine = create_engine(_build_url(), pool_pre_ping=True)

    print("Sampling entries from DB...")
    with engine.connect() as conn:
        olam_entries = _sample_entries(conn, "olam_enml", per_intent * 3, seed)
        ekkurup_entries = _sample_entries(conn, "ekkurup", per_intent * 5, seed)
        datuk_entries = _sample_entries(conn, "datuk", per_intent * 5, seed)

        # Full Datuk headword set for cross-corpus verification
        rows = conn.execute(
            text("SELECT headword FROM dictionary_entries WHERE source = 'datuk'")
        ).fetchall()
        datuk_hw_set = {r[0] for r in rows}

    datuk_entries_by_hw = {e["headword"]: e for e in datuk_entries}

    print("Generating intents...")

    # EN-input intents
    en_from_en_exact = gen_en_from_en_exact(olam_entries, per_intent)
    en_from_en_semantic = gen_en_from_en_semantic(ekkurup_entries, per_intent)

    (
        en_from_ml_exact,
        ml_from_en_exact,
        ml_from_en_semantic,
        _unused_en_from_ml_sem,
        ml_from_manglish,
        en_from_manglish,
    ) = gen_cross_intents(ekkurup_entries, datuk_hw_set, per_intent)

    en_from_ml_semantic = gen_en_from_ml_semantic(ekkurup_entries, datuk_entries_by_hw, per_intent)

    # ML-input intents
    ml_from_ml_exact = gen_ml_from_ml_exact(datuk_entries, per_intent)
    ml_from_ml_semantic = gen_ml_from_ml_semantic(datuk_entries, per_intent)

    # EN queries file: queries where input is Latin/English/Manglish
    en_records = (
        en_from_en_exact
        + en_from_en_semantic
        + ml_from_en_exact  # input is EN, expected is ML
        + ml_from_en_semantic  # input is EN, expected is ML
        + en_from_manglish  # input is Manglish, expected is EN
    )

    # ML queries file: queries where input is Malayalam or Manglish (expected ML)
    ml_records = (
        ml_from_ml_exact
        + ml_from_ml_semantic
        + en_from_ml_exact  # input is ML, expected is EN
        + en_from_ml_semantic  # input is ML, expected is EN
        + ml_from_manglish  # input is Manglish, expected is ML
    )

    for path, records, label in [(out_en, en_records, "EN"), (out_ml, ml_records, "ML")]:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        intent_counts = {}
        for r in records:
            intent_counts[r["intent"]] = intent_counts.get(r["intent"], 0) + 1
        print(f"\n{label} queries → {path}  ({len(records)} total)")
        for intent, count in sorted(intent_counts.items()):
            print(f"  {intent:<30} {count}")

    print("\nDone. Re-run eval-prepare-corpus to pin headwords in corpus sample.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate eval query files from the live DB corpus."
    )
    parser.add_argument("--out-en", default="data/eval/queries_en.jsonl")
    parser.add_argument("--out-ml", default="data/eval/queries_ml.jsonl")
    parser.add_argument("--per-intent", type=int, default=_DEFAULT_PER_INTENT)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    prepare_queries(
        Path(args.out_en),
        Path(args.out_ml),
        args.per_intent,
        args.seed,
    )
