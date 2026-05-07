"""Seed script for CI eval — inserts a minimal fixture corpus into the database.

Covers all expected_headwords in data/eval/queries.jsonl with stub Malayalam
definitions. Purpose: verify pipeline mechanics (exact, fuzzy, semantic routing)
without the full 58k-entry corpus. Accuracy metrics from this seed are NOT
representative — run against the real ingested corpus for meaningful numbers.
"""

import logging
from pathlib import Path

from dotenv import load_dotenv

from linguaalayam.corpus.enml import EnMlEntry
from linguaalayam.database import batch_insert, build_engine, build_session_factory, get_session
from linguaalayam.embeddings import EmbeddingService
from linguaalayam.eval.dataset import load_dataset
from linguaalayam.scripts.vector_checkpoint import VectorCheckpoint

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

log = logging.getLogger(__name__)

# Curated definitions for the eval set headwords.
# Format: headword -> [(pos, malayalam_definition), ...]
_DEFINITIONS: dict[str, list[tuple[str, str]]] = {
    "run": [("v", "ഓടുക; ദ്രുതഗതിയിൽ ചലിക്കുക")],
    "walk": [("v", "നടക്കുക; കാൽനടയായി ചലിക്കുക")],
    "water": [("n", "വെള്ളം; ജലം; ഒരു അടിസ്ഥാന ദ്രാവകം")],
    "peace": [("n", "ശാന്തി; സമാധാനം; സംഘർഷമില്ലാത്ത അവസ്ഥ")],
    "love": [("n", "സ്നേഹം; പ്രണയം; ആഴമായ വൈകാരിക ബന്ധം"), ("v", "സ്നേഹിക്കുക")],
    "truth": [("n", "സത്യം; വസ്തുത; ആ‌ർജ്ജവം")],
    "beauty": [("n", "സൗന്ദര്യം; ഭംഗി; ആകർഷണീയത")],
    "beautiful": [("adj", "സുന്ദരമായ; ഭംഗിയുള്ള; ആകർഷകമായ")],
    "river": [("n", "നദി; ആറ്; ഒഴുകുന്ന ജലപ്രവാഹം")],
    "mountain": [("n", "മലഞ്ചെരിവ്; പർ‌വ്വതം; ഉയർ‌ന്ന ഭൂ‌പ്രദേശം")],
    "flower": [("n", "പൂ; പുഷ്പം; സസ്യത്തിന്റെ ഭംഗിയുള്ള ഭാഗം")],
    "light": [("n", "വെളിച്ചം; പ്രകാശം; ദ്യുതി"), ("adj", "ഭാരം കുറഞ്ഞ; ലഘുവായ")],
    "hope": [("n", "പ്രത്യാശ; ആശ; ഭാവിയെക്കുറിച്ചുള്ള പ്രതീക്ഷ"), ("v", "പ്രത്യാശിക്കുക")],
    "heart": [("n", "ഹൃദയം; ചേതന; ഉൾ‌ക്കണ്ഠ; വൈകാരിക കേന്ദ്രം")],
    "soul": [("n", "ആത്മാവ്; ജീ‌വൻ; ഒരു ജീ‌വിയുടെ ആന്തരിക സ്വഭാവം")],
    "silence": [("n", "നിശ്ശബ്ദത; ശബ്ദമില്ലായ്മ; മൌനം")],
    "urn": [("n", "ഭരണി; ചരക്ക്; ഭസ്മം സൂക്ഷിക്കുന്ന പാത്രം")],
    "ephemeral": [("adj", "ക്ഷണഭംഗുരമായ; ക്ഷണിക‌മായ; അൽ‌പകാ‌ലം മാ‌ത്രം നി‌ലനി‌ൽ‌ക്കുന്ന")],
    "pastoral": [("adj", "ഗ്രാ‌മീ‌ണ‌മായ; ആ‌ടുമേ‌യ്‌ക്കൽ‌ സം‌ബ‌ന്ധി‌ച്ച; ഗ്രാ‌മ‌ജ്‌നൈ‌ശ‌ക‌ര‌ഭ‌ദ്ര‌ത")],
    "nostalgia": [("n", "ഗൃ‌ഹാ‌തുര‌ത; ഭൂ‌ത‌കാ‌ലം‌ ആ‌ഗ്ര‌ഹി‌ക്കൽ‌; വ്യ‌സ‌ന‌ം")],
    "melancholy": [("n", "വി‌ഷ‌ദ‌ം; ദുഃ‌ഖ‌ം; ഉ‌ൾ‌പ്പൊ‌ള്ളൽ‌"), ("adj", "ദുഃ‌ഖ‌ക‌ര‌മായ; നി‌ര‌ദ്ര‌നായ")],
}


def _build_entries() -> list[EnMlEntry]:
    dataset = load_dataset(
        Path(__file__).resolve().parent.parent.parent / "data/eval/queries.jsonl"
    )
    needed = {q.expected_headword.lower() for q in dataset}

    entries = []
    for headword in needed:
        defs = _DEFINITIONS.get(headword)
        if defs is None:
            # Fallback: minimal stub so exact/fuzzy lookups still hit
            defs = [("n", f"{headword}: (stub definition for eval)")]
            log.warning("No curated definition for %r — using stub", headword)
        entries.append(EnMlEntry(headword=headword, definitions=defs))

    return entries


def main() -> None:  # pragma: no cover
    from hydra import compose, initialize_config_dir
    from hydra.core.global_hydra import GlobalHydra

    GlobalHydra.instance().clear()
    config_dir = str(Path(__file__).resolve().parent.parent.parent / "config")
    with initialize_config_dir(config_dir=config_dir, version_base=None):
        cfg = compose(config_name="config")

    engine = build_engine(cfg.database)
    session_factory = build_session_factory(engine)
    service = EmbeddingService(cfg.embedding)

    entries = _build_entries()
    log.info("Seeding %d eval entries", len(entries))

    checkpoint = VectorCheckpoint(Path(".checkpoints/eval_seed.jsonl"))
    checkpoint_dir = Path(".checkpoints")
    checkpoint_dir.mkdir(exist_ok=True)

    cached = checkpoint.load()
    to_embed = [e for e in entries if e.headword not in cached]

    if to_embed:
        vectors = service.encode(to_embed)
        checkpoint.append_batch([e.headword for e in to_embed], vectors)

    all_vectors = checkpoint.load()
    entry_vectors = [all_vectors[e.headword] for e in entries]

    with get_session(session_factory) as session:
        batch_insert(session, entries, entry_vectors)

    log.info("Seed complete — %d entries inserted", len(entries))


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    main()
