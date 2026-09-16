@AGENTS.md

# Notes specific to Claude Code

The rules for this repository live in [`AGENTS.md`](AGENTS.md); the line above imports them,
because Claude Code reads `CLAUDE.md` and does not read `AGENTS.md` on its own. Everything in
that file applies here — most of all: run `make check` before committing, and never weaken a
check to make it pass.

Do not duplicate rules into this file. If something belongs to every agent, it belongs in
`AGENTS.md`. Use this file only for Claude-Code-specific mechanics.

- The desktop preview tool reads `.claude/launch.json`, which is deliberately untracked
  (personal tooling). Start the server yourself instead: `make run`, or
  `cd backend && uv run python -m kotoba serve --data-dir ../data`.
- Real screen OCR cannot be verified from a sandboxed shell — a capture returns the wallpaper
  because the process has no Screen Recording permission. Say so rather than claiming the OCR
  path works.
