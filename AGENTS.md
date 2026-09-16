# AGENTS.md

Operating rules for AI coding agents working in this repository. Humans should read them too.
**AI-assisted contributions are welcome here** — that is exactly why these constraints exist.

If you follow one thing, follow this: **`make check` must pass before you commit, and you must
never weaken a check to make it pass.**

---

## 1. What this is

Kotoba Studio is a local-first Japanese study companion for Chinese speakers. One FastAPI
process owns the database, the media files and the built web app; a phone on the same network
reaches the same data through a PWA.

The data flow, which most tasks touch somewhere:

```
capture (OCR or text hook) → Line (台词 + screenshot)
   → Encounter (this word, in this line, with this sense)
      → Term (the word itself, across every work it appeared in)
      → Card (one review unit) → FSRS schedule → ReviewLog
```

## 2. Commands

```bash
make setup     # install both halves and enable the git hooks — run this first
make check     # everything CI runs; must pass before you commit
make fix       # auto-fix lint and formatting in both halves
make test      # tests only, faster than check
make dev       # API on 8720 + Vite on 5174, both reloading
make run       # build the frontend and serve everything on 8720
make migrate m="add x to y"   # create an Alembic revision
```

`make check` is the contract. If you cannot run it, say so instead of guessing.

Configuration is environment variables with a `KOTOBA_` prefix, all optional and all
documented in [`.env.example`](.env.example); a `.env` at the repository root or in
`backend/` is read, and real environment variables win over it. When you add a setting, add
it to `Settings` in `core/config.py` **and** to `.env.example` in the same commit.

## 3. Layout

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

Coding style, layering and testing patterns: [`docs/conventions.md`](docs/conventions.md).

## 4. Rules for commits

Committing without being asked each time is fine. Doing the following is not.

### Never, unless the human explicitly asks in this conversation

- **Never rewrite published history.** No `push --force`, no `filter-repo`, no amending a commit
  that is already on the remote, no `reset --hard` onto someone else's work.
- **Never use `--no-verify`.** The hooks exist to catch exactly the mistakes an agent makes at
  3am. If a hook blocks you, fix the cause.
- **Never weaken a check to make it pass.** Do not delete or `skip` a failing test, widen a type
  to `any`, add a blanket `eslint-disable`, add `# noqa` without a reason, or loosen a ruff or
  tsconfig setting. A failing check is information; report it.
- **Never commit credentials, runtime data, media or build output.** Keys belong in the OS
  keyring. `data/`, `*.db`, `frontend/dist/` and `.env` are not code.
- **Never touch the user's data directory.** No deleting, migrating or "cleaning" anything under
  `KOTOBA_DATA_DIR`. Tests use a temporary directory; use it.
- **Never change the licence, `NOTICE.md`, or the invariants in §5.**
- **Never upgrade or add dependencies as a side effect** of an unrelated change. A dependency
  change is its own commit with its own reason.
- **Never reformat files you did not otherwise need to change.** A formatting-only commit is
  fine; formatting noise mixed into a feature commit is not.
- **Never take an action visible outside this repository** — opening a PR, publishing a release,
  commenting on an issue, pushing to another remote — without being asked.

### Every commit must

1. Pass `make check` (or the half you touched, if the other half is untouched).
2. Contain **one logical change**. Found something unrelated while you were in there? Note it in
   your reply or open an issue; do not fold it in.
3. Carry a Conventional Commits subject under 72 characters, saying **why**, not just what:
   - good: `fix(jp): match contractions on token boundaries`
   - bad: `update contractions.py`

   Record the tool with an `Assisted-by: <tool> (<model>)` trailer rather than
   `Co-Authored-By:` — a tool assists, it does not author, and the human who sends the patch
   carries the responsibility. Never add `Signed-off-by:` on a human's behalf.
4. Come with a test when it changes behaviour — one that fails before the change and passes
   after. Bug fixes especially.
5. Include an Alembic revision when it changes a model.
6. Use Simplified Chinese for any new user-facing string, English for identifiers and comments.
7. Keep `backend/pyproject.toml` and `frontend/package.json` on the same version when you
   bump either — CI fails if they disagree. The Python package reads its own version from
   the manifest, so there is no third copy to update.

### Stop and ask instead of improvising when

- the change would grow well past what was asked;
- the only way to make a test pass is to change what the test asserts;
- you would have to delete data, rewrite history, or disable a safety check;
- the task rests on an assumption you cannot verify from the code.

Reporting "I got this far and here is what blocks me" is a good outcome. Quietly working around
a constraint is not.

## 5. Product invariants — these look like bugs and are not

1. **A session quiz never touches the FSRS schedule.** `services/review/scheduler.review()` only
   calls `review_card` when `mode == "scheduled"`; quiz answers are logged and nothing else.
   Short-term recall is not evidence of long-term retention.
2. **A card front never leaks its answer.** No screenshot, no un-clozed sentence on the front.
3. **One card has one review owner.** `Card.review_owner` is `desktop`, `mobile` or `any`, and
   the queue filters on it so a card is never scheduled twice on two devices.
4. **AI is optional everywhere.** Capture, lookup and review must work with no API key, and an
   AI failure must never lose a capture.
5. **The AI prompt never sees later lines.** Only the target word, the current line and up to
   three preceding lines — otherwise explanations spoil the story.
6. **Errors use one envelope:** `{"error": {"code": ..., "message": ...}}` via
   `ApiError(code, message, status)`.
7. **Platform-only imports are lazy.** Never import `Vision`, `winocr` or `mss` at module import
   time; the OCR registry imports them inside the provider so the app still boots without them.
8. **Contractions match on token boundaries.** `って` inside `奢って` is a te-form, not the
   quotative particle. `find_in_tokens`, not substring search.

## 6. What cannot be verified here

- Real screen OCR needs the OS screen-recording permission, so it is tested against rendered
  images instead. The Apple Vision test is skipped off macOS.
- The Windows OCR path has never run on real hardware. Do not claim it works; say it is untested.
- Anything involving a real game window. Say what you verified and what you did not.

## 7. Working the issue queue unattended

This section applies when a human has told you to work the queue, and **only then**. It is the
one standing exception to §4's "never take an action visible outside this repository": inside
the loop below, branching, pushing and opening a pull request are pre-authorised. Nothing else
in §4 is relaxed.

### The loop

```bash
git switch main && git pull --ff-only

# Is a queue PR still open? If this prints anything, stop — see below.
gh pr list --state open --json headRefName --jq '.[].headRefName | select(startswith("agent/"))'

# Otherwise take the lowest-numbered ready issue.
gh issue list --state open --label agent-ready --json number,title --jq 'sort_by(.number)[0]'

git switch -c agent/<type>-<slug>   # agent/feat-subtitle-parser, agent/fix-dedup-growth
#   ... implement only what the issue's acceptance criteria ask for ...
make check
git commit                          # Conventional Commits, Assisted-by: trailer
git push -u origin agent/<type>-<slug>
gh pr create --fill --body "...Closes #<n>..."
```

Then **stop and report**. Do not start the next issue.

**Branches from this loop are always prefixed `agent/`.** That prefix is not decoration: it is
how you tell your own unreviewed work from everyone else's, and how a human reviewing the branch
list can see at a glance what came from an unattended run. Do not use `--author` to find your
PRs — you and the human share one GitHub account, so that matches their work too.

### Rules that hold throughout

1. **One open `agent/` pull request at a time.** If one is still unmerged, the queue is blocked
   on a human, not on you. Do not open a second one, and do not branch off an unreviewed branch —
   always branch from `main`.
2. **Never merge anything** — not your PR, not anyone's. Never approve, never enable auto-merge,
   never push to `main`. A human merges; that review is the whole point of the loop.
3. **Only issues labelled `agent-ready`.** That label means a human decided the description is
   complete enough to implement without asking. An issue without it is not yours to take, no
   matter how easy it looks. Lowest open number first, so dependencies land in order.
4. **One issue, one branch, one PR.** If you discover a second problem, open an issue for it
   (that much is allowed) and leave it alone.
5. **The issue's "Out of scope" list is binding.** It is there because the work was deliberately
   split to keep each PR reviewable.
6. **Never edit or close an issue you did not finish**, and never remove a label a human set.
   `Closes #<n>` in the PR body is how an issue gets closed — by the merge, not by you.

### The pull request body must say

- what changed and why, in one short paragraph;
- how you verified it — the actual command and its result, not "tests pass";
- **what you could not verify** (§6 lists the usual suspects: real screen OCR, Windows, a real
  game window). An honest "untested on Windows" is worth more than a confident guess;
- `Closes #<n>`.

### Stop, report, and leave the branch for a human when

- the acceptance criteria cannot be met without breaking an invariant in §5;
- `make check` fails for a reason your change did not introduce;
- the task needs hardware, an OS permission or a credential you do not have;
- you have tried the same failing check three times. Three is enough to know you are guessing.

Stopping with "here is the branch, here is what blocks me" is a success. A green PR that quietly
skipped half the acceptance criteria is not.
