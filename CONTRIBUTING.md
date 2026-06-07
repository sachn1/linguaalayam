# Contributing to LinguAalayam

## Before you start

For anything beyond a small bug fix, **open an issue first** to discuss the change. This avoids duplicating in-progress work or heading in a direction the project won't take.

---

## Development setup

```bash
git clone https://github.com/sachn1/linguaalayam
cd linguaalayam
make install-local          # auto-detects GPU; use 'poetry install' on CI / CPU-only
cp .env.example .env        # fill in DB credentials
poetry run alembic upgrade head
poetry run ingest corpus=debug   # 50-entry test ingest — no need for full corpora
```

See [docs/setup.md](docs/setup.md) for Docker Postgres setup and environment variables.

---

## Branch strategy

All feature and fix branches target `master` directly via PR — trunk-based flow.

```
feature/<short-description>  →  master
bugfix/<short-description>   →  master
```

The version bump CI runs automatically on every push to `master` via `cz bump`.

---

## Commit conventions

This project uses [Conventional Commits](https://www.conventionalcommits.org/). Commitizen enforces this and drives the version bump automatically:

| Commit type | Version bump |
|---|---|
| `fix: ...` | Patch (`0.0.x`) |
| `feat: ...` | Minor (`0.x.0`) |
| `feat!: ...` or `BREAKING CHANGE:` in footer | Major (`x.0.0`) |
| `docs:`, `chore:`, `test:`, `refactor:` | No bump |

Examples:

```
feat: add mlmorph morphological analysis to search results
fix: datuk definitions not romanised when A↔അ toggle is on
chore: remove unused langchain base dependency
```

---

## Tests

```bash
poetry run pytest                   # all tests (SQLite in-memory, no Postgres needed)
poetry run pytest tests/corpus      # corpus parsers only
poetry run pytest tests/database    # DB layer only
```

- All existing tests must pass before opening a PR.
- New behaviour must be covered by tests — bug fixes included (add a regression test).
- Tests live in `tests/` and mirror the module they cover.
- Do **not** mock the database for integration tests — use the SQLite `db_cfg` fixture.

---

## Lint and format

```bash
poetry run ruff check .
poetry run ruff format .
poetry run djlint linguaalayam/templates --profile=jinja
```

---

## Extending the project

### Adding a corpus

1. Create a parser in `linguaalayam/corpus/` exposing `parse(filepath: Path) -> list[Embeddable]`.
2. Add a source entry to `config/corpus/all.yaml` and `config/corpus/debug.yaml` with `parser._target_` pointing to your function.

No Python change is needed in `ingest.py`. See [CLAUDE.md](CLAUDE.md) for details.

### Adding an LLM provider

1. Subclass `LLMAdapter` in `linguaalayam/llm/adapters/`.
2. Add a YAML config in `config/llm/` with `_target_` pointing to your class.

---

## Pull request checklist

- Targets `master`
- Follows conventional commit format
- All tests pass (`poetry run pytest`)
- Linter clean (`poetry run ruff check .`)
- New behaviour has tests
- No secrets, API keys, or `.env` files committed
