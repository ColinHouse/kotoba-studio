# Contributing

> 中文：[CONTRIBUTING.zh-CN.md](CONTRIBUTING.zh-CN.md)

This is a personal project, but anyone is welcome to work on it. None of what follows is a
gate — it exists so a change can be understood and merged quickly.

## AI-assisted contributions are welcome

**Patches written with Claude Code, Codex, Cursor, Copilot and the like are explicitly
welcome.** That is how this project is built; there would be no sense in asking others not to.
[`AGENTS.md`](AGENTS.md) at the repository root is written for exactly those tools: the layout,
the commands that must pass, and the rules that look like bugs and are not.

Three requirements, and only three:

1. **You have read it and run it.** Run the commands below on your own machine before you send
   it, and actually open the app and click through what you changed. A patch nobody verified is
   not accepted — human or model.
2. **Say that a tool was involved.** Add a trailer to the commit message:

   ```
   Assisted-by: Claude Code (claude-opus-5)
   ```

   This counts against nothing. It tells review where to look harder. Use `Assisted-by:` rather
   than `Co-Authored-By:` — the latter makes GitHub record the tool as a co-author, and a tool
   is not an author. You are, and so is the responsibility. (Early commits here carry
   `Co-Authored-By:` because that was Claude Code's default; both are accepted, prefer
   `Assisted-by:` for new work.) The Linux kernel's 2026
   [coding-assistants policy](https://docs.kernel.org/process/coding-assistants.html) asks for
   the same thing, and adds one more: an AI must never add `Signed-off-by:` itself.
3. **One pull request does one thing.** Do not send bulk generated changes with renames,
   reformatting and dependency bumps mixed together. Those get closed.

## Development environment

```bash
make setup     # install both halves and enable the repository's git hooks
make dev       # API on 8720 + Vite on 5174, both reloading
make help      # every command
```

On Windows these run in Git Bash (`winget install ezwinports.make`). PowerShell and CMD make
`make` fall back to cmd.exe, where the Unix-style recipes fail. The repository checks out LF on
every platform via `.gitattributes`; if `format:check` is entirely red in an older clone, make
sure nothing is uncommitted and run `git read-tree --reset -u HEAD`.

## What must pass before you commit

```bash
make check
```

One command runs lint, formatting, types, tests and the build for both halves — the same thing
CI runs, except CI also runs the backend again on macOS and Windows. `make fix` repairs most
formatting and lint problems on its own.

Two git hooks ship with the repository (`make setup`, or `make hooks`):

- **pre-commit** blocks runtime data, build output, credentials and large files, and lints what
  you staged.
- **commit-msg** requires Conventional Commits, e.g. `fix(jp): match contractions on token
  boundaries`.

Do not reach for `--no-verify`. When a hook stops you, the thing to fix is the cause.

CI applies the same idea to two conventions, and both exits are labels on the pull request —
visible and auditable, never a magic word in a commit message:

- a PR that touches `LICENSE`, `NOTICE.md`, `SECURITY.md`, `docs/adr/*` or `AGENTS.md` needs a
  human to add the `protected-docs-reviewed` label;
- a PR whose `feat(...)`/`fix(...)` commits do not update `CHANGELOG.md` needs the
  `no-changelog` label (pure refactors, tests and CI changes are what it is for).

## Code conventions

Read [docs/conventions.md](docs/conventions.md) before writing code: how the layers are split,
where the transaction boundaries are, and which parts of the Japanese handling are
counter-intuitive. If you are using an AI tool, point it at [AGENTS.md](AGENTS.md) first.

## Especially welcome

- **Real-hardware reports on Windows.** Built-in OCR (with the Japanese language pack) and the
  global shortcut are verified on Windows 11. Still unverified on real hardware: system audio
  loopback (#14), and how well individual visual novels' dialogue boxes actually recognise.
- **Japanese handling details.** Concrete cases where tokenisation, contractions or expression
  merging get it wrong. The original sentence is the most useful thing you can attach.
- **The Chinese–Japanese homograph table.** `backend/kotoba/data/homograph_traps_zh.json` is
  plain data; adding entries needs no code.
- **Game compatibility.** Which visual novel's dialogue box OCR reads badly, which text hooker
  will not connect.

## Claiming an issue

Comment on it. The maintainer will assign it as soon as they see it, and **once it is assigned
it is yours** — nobody else should pick it up.

This rule was paid for. On #114 someone asked politely to be assigned while somebody else had
already opened the pull request, which merged. The person who put their hand up first got
nothing. There was no convention, so neither of them did anything wrong — hence this one.

Practical notes:

- **GitHub only lets us assign someone who has commented on that specific issue.** So comment
  on the one you want; saying it anywhere else cannot be acted on.
- **You do not have to wait for the assignment to start reading**, but comment before you start
  writing, so two people do not collide.
- **Once assigned, this repository's automated agent will not touch it either**
  ([`AGENTS.md`](AGENTS.md) §7.3). There is an AI agent working through the queue unattended and
  it is much faster than you are, so "assigned means off the queue" is an enforced rule rather
  than an understanding.
- If you get stuck or lose interest, just say so. **There is no obligation.** Silence is the
  only thing that leaves others waiting.
- A claim with no activity for a week or two may be released so someone else can take it.

## Filing an issue

Say what you were doing, what you expected, and what happened instead. For recognition
problems, attach the sentence text (not a screenshot — screenshots spoil the story), the title
of the work, and the platform.

### How to read the labels

You do not need to apply labels yourself; the maintainer will. Understanding them helps you
find work that fits:

- **Type** (exactly one per issue): `bug`, `enhancement`, `documentation`, `refactor`, `test`.
  Domain labels sit on top: `japanese` (tokenisation, readings, contractions, expression
  merging) and `accessibility`.
- **`agent-ready`** — specified completely enough to hand to an unattended coding agent: the
  problem is established, the subsystem is named, the scope is bounded, the acceptance criteria
  are explicit, verification is described, and no product decision is still open. It is a
  **readiness state, not a byline** — an issue is not ready because an AI found or wrote it.
- **`needs-hardware`** — cannot be verified without real hardware or an OS permission. **Agents
  must not take these**; a person has to do them on a real machine.
- **`good first issue`** — genuinely suitable for a first contribution here: small blast radius,
  no cross-file coordination, no repository lore required. **Not a synonym for "small".**
- **`help wanted`** — the maintainer actively wants someone outside to take it.
- **`no-japanese-needed`** — pure engineering; you do not need to read Japanese. Note that
  user-facing strings are Simplified Chinese, so an issue that adds UI copy is not language-free
  even when it needs no Japanese.

**Bringing your own coding agent?** Take something labelled `agent-ready` + `no-japanese-needed`
and give it [`AGENTS.md`](AGENTS.md) — the rules are all in there, including how to label an
issue it opens (§8). Tests, CI and migrations are the issues with no user-visible strings at
all, which makes them the easiest place to start if you read neither Chinese nor Japanese.

## Licence

Contributions are licensed under [AGPL-3.0-or-later](LICENSE). Dictionary data licensing is in
[NOTICE.md](NOTICE.md).
