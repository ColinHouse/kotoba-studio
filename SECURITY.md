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

**Screenshots capture whatever is on screen.** The capture feature stores the region you
framed, as an image, in your data directory. If something sensitive is on screen when you
press the shortcut, it is now in the database and in any backup you make.

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

Only the JMdict dictionary, over HTTPS from the
[jmdict-simplified](https://github.com/scriptin/jmdict-simplified) releases, when you ask for
it in Settings. Nothing is executed from it; it is parsed as JSON.

## Supported versions

Pre-1.0: only the latest commit on `main` gets fixes.
