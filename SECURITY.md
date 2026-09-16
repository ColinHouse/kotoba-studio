# Security

## Reporting a vulnerability

Use GitHub's private vulnerability reporting on this repository
(**Security → Report a vulnerability**). Please do not open a public issue for something
exploitable. I am one person working on this in my spare time; expect a first reply within a
week.

## What this application is

Kotoba Studio runs on your own machine. There is no account, no server owned by anyone else,
and your study data never leaves your computer unless you export it or enable the optional AI
explanations. That shapes the threat model below.

## Things you should know before you run it

**Serving to your phone has no authentication.** The server binds `127.0.0.1` by default. When
you start it with `--host 0.0.0.0` so a phone can reach it, *anyone on that network* can read
and modify your study data and trigger screen captures through the API. Only do this on a
network you trust, and stop the server when you are done. Treat the URL in Settings the way
you would treat an unlocked laptop.

**Screen capture stores whatever is in the framed region.** The image goes into your data
directory and into any backup you make. This is not only the moment you press the shortcut:
the region watcher, once started, captures that region continuously until you stop it. If
something sensitive passes through the frame while it is running, it is now on disk.

**The global shortcut installs an OS-level keyboard hook.** Turning it on asks `pynput` for a
system-wide key hook — on macOS that needs Accessibility permission, on Windows it is a
low-level hook. The hook receives key events from *every* window, not just this application;
Kotoba Studio only acts on the combination you configured and does not record, store or send
anything else. But the hook itself is global, so if you would rather not have one running,
leave the feature off — it is off by default.

**The clipboard watcher reads your clipboard.** While it is running it polls the clipboard
roughly three times a second. Text with no kana or kanji, text longer than 200 characters and
text identical to the previous read are discarded without being stored — but they are still
read. Anything Japanese and short enough is ingested as a line, whether or not it came from a
game. Do not leave it running while you copy passwords or private messages. It is off by
default and has to be started explicitly.

**Optional AI explanations send text to a third party.** If you configure a key, the target
word, the current line and up to three preceding lines are sent to the provider you chose
(DeepSeek by default). Nothing is sent when no key is configured, and later lines are never
sent. Review your provider's data-retention policy before enabling it.

## Where secrets are kept

API keys go in the operating system's credential store (macOS Keychain, Windows Credential
Manager, Linux Secret Service) via `keyring`, which is the default when you enter a key in
Settings. They are never written to the database.

For headless setups, `KOTOBA_AI_KEY` may be set in the environment or in a `.env` file — see
[`.env.example`](.env.example). A `.env` is plaintext on disk; prefer the credential store
wherever you have one. `.env` is git-ignored, and the pre-commit hook and CI both reject it
along with anything that looks like a key.

## What is downloaded at runtime

Nothing is fetched unless you ask for it in Settings. When you do:

- **JMdict**, over HTTPS from the
  [jmdict-simplified](https://github.com/scriptin/jmdict-simplified) releases, parsed as JSON.
- **Pitch accent data**, over HTTPS from the
  [Kanjium](https://github.com/mifunetoshiro/kanjium) repository, parsed as text.

Nothing downloaded is ever executed.

## Files you import are untrusted input

Yomitan dictionary packs, Anki `.apkg` decks, subtitle files and backup archives are parsed by
this application, and they usually come from the internet. They are treated as data — no
archive entry is written outside the data directory and nothing in them is executed — but
parsing untrusted input is still the most likely place for a bug in a program like this one.
Prefer files from a source you trust, and report anything that crashes the importer.

## Outbound connections while capturing

When you connect a hook target, the application dials `ws://127.0.0.1` on the port you chose
(6677 Textractor, 9001 Agent, 2333 LunaTranslator by default). These are loopback connections
to a tool already running on your own machine. It never dials anything else on its own.

## Supported versions

Pre-1.0: only the latest commit on `main` gets fixes.
