# AGENTS.md

Conventions for AI coding agents (and humans) working in this repository.
**AI-assisted contributions are welcome here** — see `CONTRIBUTING.md` for what we ask in return.

## What this is

Kotoba Studio is a local-first Japanese study companion for Chinese speakers. One FastAPI
process owns the database, the media files and the built web app; a phone on the same
network reaches the same data through a PWA. Capture (OCR / text hook) produces *lines*;
confirming a word in a line produces an *encounter*; encounters produce *cards*; cards are
scheduled with FSRS.

## Setup

```bash
cd backend  && uv sync --extra dev --extra macos   # Windows: --extra windows; any OS: --extra ocr-onnx
cd frontend && npm ci
```

## Commands you must be able to run before proposing a change

```bash
cd backend  && uv run ruff check . && uv run ruff format --check . && uv run pytest -q
cd frontend && npm run typecheck && npx vitest run && npm run build
```

Run the app (serves the built frontend on one port):

```bash
cd backend && uv run python -m kotoba serve --open        # add --host 0.0.0.0 to reach it from a phone
```

Both dev servers with reload: `./scripts/dev.sh` (API on 8720, Vite on 5174).

## Layout

| Path | Holds |
| --- | --- |
| `backend/kotoba/core/` | settings, database, error envelope, in-process events, bundled resource paths |
| `backend/kotoba/models/` | ORM split by domain: `capture`, `vocabulary`, `review`, `reference`, `system` |
| `backend/kotoba/schemas/` | Pydantic DTOs |
| `backend/kotoba/api/` | `capture/`, `study/`, `system/` route groups, assembled by `build_api_router()` |
| `backend/kotoba/services/` | `jp`, `text`, `dictionary/jmdict`, `ocr/providers`, `capture`, `learning`, `review`, `ai`, `export`, `backup` |
| `backend/kotoba/data/` | bundled JSON: contractions, homograph traps, JMdict test fixture |
| `frontend/src/composables/` | data flow for the heavier views |
| `frontend/src/components/` | `common`, `capture`, `inbox`, `review`, `settings` |

## Rules that are deliberate — do not "fix" them

1. **A session quiz never touches the FSRS schedule.** `services/review/scheduler.review()`
   only calls `review_card` when `mode == "scheduled"`; quiz answers are logged and nothing else.
2. **A card front never leaks its answer.** No screenshot and no un-clozed sentence on the
   front. Anything revealing goes behind the reveal.
3. **One card has one review owner.** `Card.review_owner` is `desktop`, `mobile` or `any`,
   and the queue filters on it so the same card is not scheduled on two devices.
4. **AI is optional everywhere.** Capture, lookup and review must work with no API key, and
   an AI failure must never lose a capture.
5. **The AI prompt never sees later lines.** Only the target word, the current line and up to
   three preceding lines, so explanations cannot spoil the story.
6. **Errors use one envelope:** `{"error": {"code": ..., "message": ...}}`, raised as
   `ApiError(code, message, status)`.
7. **Platform-only imports are lazy.** Never import `Vision`, `winocr` or `mss` at module
   import time; the registry imports them inside the provider.

## Conventions

- Python ≥ 3.12, line length 100, `ruff` for lint and format. UI copy is Simplified Chinese;
  identifiers, comments and commit messages are English.
- Keep files focused; if one passes ~300 lines it probably wants splitting.
- Database changes need an Alembic revision: `cd backend && uv run alembic revision --autogenerate -m "..."`.
  Replace any generated `kotoba.models.UTCDateTime()` with `sa.DateTime()` in the migration.
- Tests use a temporary data directory via the `KOTOBA_DATA_DIR` env var; the `client`,
  `db` and `jmdict_fixture` fixtures live in `backend/tests/conftest.py`.
- Japanese text handling belongs in `services/jp/`. Note that contraction matching is done on
  token boundaries on purpose — `って` inside `奢って` is a te-form, not the quotative particle.

## Things that cannot be verified in CI

- Real screen OCR needs the OS screen-recording permission, so it is tested against rendered
  images instead. The Apple Vision test is skipped off macOS.
- The Windows OCR path has never been exercised on real hardware. If you have a Windows
  machine, reports are especially welcome.
