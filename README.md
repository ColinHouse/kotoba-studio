<h1 align="center">Kotobako · ことばこ</h1>
<p align="center">
  <b>好き、以外の言葉で。</b><br>
  会记住语境的日语伴读工具 · A context-keeping Japanese reading companion<br><br>
  <img alt="软件图标" src="assets/mascot.png" width="220">
</p>

---

<p align="center">
  <a href="https://github.com/ColinHouse/kotobako/stargazers"><img alt="GitHub Stars" src="https://img.shields.io/github/stars/ColinHouse/kotobako?style=flat-square"></a>
  <a href="https://github.com/ColinHouse/kotobako/network"><img alt="GitHub Forks" src="https://img.shields.io/github/forks/ColinHouse/kotobako?style=flat-square"></a>
  <a href="https://github.com/ColinHouse/kotobako/releases/latest"><img alt="GitHub Downloads" src="https://img.shields.io/github/downloads/ColinHouse/kotobako/total?style=flat-square"></a>
  <a href="https://github.com/ColinHouse/kotobako/issues"><img alt="GitHub Issues" src="https://img.shields.io/github/issues/ColinHouse/kotobako?style=flat-square"></a>
  <a href="https://github.com/ColinHouse/kotobako/graphs/contributors"><img alt="GitHub Contributors" src="https://img.shields.io/github/contributors/ColinHouse/kotobako?style=flat-square"></a>
  <a href="https://github.com/ColinHouse/kotobako/actions/workflows/ci.yml"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/ColinHouse/kotobako/ci.yml?branch=main&style=flat-square&label=CI"></a>
  <a href="LICENSE"><img alt="GitHub License" src="https://img.shields.io/github/license/ColinHouse/kotobako?style=flat-square"></a>
  <a href="https://deepwiki.com/ColinHouse/kotobako"><img alt="DeepWiki" src="https://deepwiki.com/badge.svg"></a>
</p>

> [!IMPORTANT]
> **当前版本 `v0.1.0-beta.1`。** 核心流程可以每天用，但只在 Windows 11 上打过包，
> 也只有作者一个人完整走过一遍。**请先用设置页的备份功能导出一份，再开始积累学习数据。**
> 完整的[已知限制](CHANGELOG.md)写在 CHANGELOG 里。
>
> **This is a beta.** Packaged and verified on Windows 11 only, by one person.
> Export a backup from the settings page before you start accumulating study data.

## 软件介绍 / Introduction

### 性质 / Nature

本软件是面向中文母语者的日语沉浸式学习工具。玩 Galgame、看动画、读漫画和轻小说时，
用很低的打断成本收藏台词——原句、截图、原声一起存下来，自动整理成词卡，用 FSRS 复习。
它拥有自己的数据库，Anki 只是可选出口。

- **看得懂汉字却读不出**：含汉字的词默认生成「看汉字写读音」卡，专治中文母语者最容易糊弄过去的那一类。
- **中日同形词误导**：勉強・大丈夫・手紙・怪我… 命中时卡片自动提醒，不让你把中文意思带进去。
- **口语缩约看不懂**：ちゃう ← てしまう、なきゃ ← なければ 等按词边界识别并标注，不是字符串替换。
- **收藏了却不复习**：会后三分钟短测 + FSRS 到期复习 + 手机扫码即用的 PWA。
- **数据不想被锁在别人的服务里**：SQLite 加一个媒体目录，一键备份/恢复，可导出 JSON、`.apkg` 或推给 AnkiConnect。

This software is an immersion-learning tool for Japanese, built for Chinese speakers. While you
play a visual novel, watch anime, or read manga and light novels, it captures a line at very low
interruption cost — the sentence, its screenshot and its audio together — turns the words you did
not know into flashcards, and schedules them with FSRS. It owns its own database; Anki export
exists, but nothing depends on it.

- **Kanji you can read but cannot pronounce**: words containing kanji default to a "write the reading" card — the failure mode Chinese speakers gloss over most easily.
- **False friends between Chinese and Japanese**: 勉強・大丈夫・手紙・怪我… when one is hit, the card flags it, so you do not carry the Chinese meaning across.
- **Spoken contractions**: ちゃう ← てしまう, なきゃ ← なければ and friends are recognised at word boundaries and annotated — not string-replaced.
- **Saved but never reviewed**: a three-minute quiz after each session, FSRS-scheduled reviews, and a PWA you open on your phone by scanning a code.
- **Data you do not want locked in someone else's service**: SQLite plus a media directory, one-click backup and restore, export to JSON, `.apkg`, or straight to AnkiConnect.

### 原理 / Working Principle

本软件通过以下流程把一句台词变成一张会到期的卡片：

1. **采集：** 对你框选的屏幕区域做 OCR，或者接收文本钩子（Textractor 等）送来的原始文本。
   两条路进来的句子后续流程完全一致。
2. **整理：** 对句子分词、归一化、查词典，与你已知的词比对，只留下真正的生词。
3. **建卡：** 生词连同它出现的那一句、那张截图与那段原声一起存成卡片——**语境跟着词走**。
4. **复习：** FSRS 安排到期时间，桌面或手机都能复习；一张卡只由一端安排正式复习，两端不会重复排期。

The software turns a line of dialogue into a scheduled card through the following workflow:

1. **Capture**: run OCR on the screen region you selected, or receive raw text from a text hooker
   (Textractor and friends). Lines from either path are handled identically afterwards.
2. **Sort**: tokenise and normalise the sentence, look the words up, compare against what you
   already know, and keep only the genuinely new ones.
3. **Build**: store each new word together with the sentence it appeared in, that screenshot and
   that audio clip — **the context travels with the word**.
4. **Review**: FSRS schedules the due dates, on desktop or phone. Each card is scheduled by one
   side only, so the two never queue the same card twice.

## 重要声明 / Important Notice

- **本软件不修改任何游戏或其文件。** 它读取屏幕像素，或读取你自行接入的文本钩子输出，
  不注入进程、不改内存、不碰存档。
- **使用责任自负。** 你需要自行确认，对你运行它的对象而言，截屏与文本读取符合其服务条款与当地法律。
- **开源许可：** 代码采用 [`AGPL-3.0-or-later`](LICENSE)。本应用自己提供网络界面（手机通过局域网访问桌面端），
  AGPL 第 13 条正对应这种形态；理由详见 [ADR 0002](docs/adr/0002-license.md)。
- **词典数据不属于本项目。** JMdict/EDICT、KANJIDIC2 与 Kanjium 依 CC BY-SA 4.0 授权，
  再分发时**不得剥离其署名与协议**，详见下方[鸣谢](#鸣谢--acknowledgements)与 [NOTICE.md](NOTICE.md)。
- **免责：** 本软件按「原样」提供。因使用本软件造成的任何直接或间接损失，作者不承担责任。

<br>

- **This software does not modify any game or its files.** It reads screen pixels, or the output of
  a text hooker you connected yourself. It does not inject into processes, patch memory, or touch saves.
- **Use is at your own risk.** It is your responsibility to confirm that screen capture and text
  reading comply with the terms of service of whatever you run it against, and with your local law.
- **Licence**: the code is [`AGPL-3.0-or-later`](LICENSE). This application serves its own web
  interface (the phone reaches the desktop over the LAN), which is exactly the shape AGPL §13
  addresses; the reasoning is in [ADR 0002](docs/adr/0002-license.md).
- **Dictionary data is not part of this project.** JMdict/EDICT, KANJIDIC2 and Kanjium are licensed
  CC BY-SA 4.0; redistribution **must not strip their attribution or licence**.
- **Disclaimer**: provided "as is". The author accepts no liability for any direct or indirect loss
  arising from its use.

## 使用方法 / How to Use

**Windows**：到 [Releases](https://github.com/ColinHouse/kotobako/releases) 下载安装包，
双击即可，不需要装 Python 或 Node。**macOS / Linux**：暂无安装包，[从源码运行](docs/install.md#从源码运行)。

访问文档站获取完整使用指南：

- [Kotobako 文档站](https://colinhouse.github.io/kotobako/)

| | |
| --- | --- |
| [安装](docs/install.md) | 安装包、从源码跑、环境变量 |
| [头三件事](docs/guide.md) | 上手流程，截图与 Hook 怎么选 |
| [手机复习](docs/mobile.md) | 扫码连接与局域网注意事项 |
| [平台说明](docs/platforms.md) | macOS 授权、Windows 语言包、游戏内覆盖层 |
| [Hook 与导入导出](docs/integrations.md) | 对外契约：Hook 协议、字幕/EPUB/mokuro 导入、Anki 导出 |
| [架构](docs/architecture.md) | 目录结构、数据模型、怎么改代码、怎么打包 |

**Windows**: download the installer from [Releases](https://github.com/ColinHouse/kotobako/releases) —
no Python or Node required. **macOS / Linux**: no installer yet, [run from source](docs/install.md#从源码运行).

Visit the documentation site for the full guide:

- [Kotobako Documentation](https://colinhouse.github.io/kotobako/)

## 参与贡献 / Contributing

欢迎参与，也**明确欢迎用 AI 工具写的贡献**——这个项目本身就是这么开发的。前提是有约束：
[AGENTS.md](AGENTS.md) 写明了 AI 工具的操作规则（必须跑通 `make check`、不得绕过 hook、
不得为了让检查通过而削弱检查、一次提交只做一件事）。

- [CONTRIBUTING.md](CONTRIBUTING.md)：环境、必须通过的那一条命令、怎么认领 issue
- [docs/conventions.md](docs/conventions.md)：代码约定

最需要帮助的是 **Windows 实机验证**、日语分词的错例，以及中日同形词表的扩充。

**Contributing does not require Chinese or Japanese.** Issue titles are English, and
[`AGENTS.md`](AGENTS.md) — the file that tells a coding agent how this repository works — is written
in English throughout. **The interface itself is Simplified Chinese**; an English UI is not
scheduled, and if that changes it will appear in the issue tracker first.

- [`good first issue`](https://github.com/ColinHouse/kotobako/labels/good%20first%20issue) — small blast radius, no repository lore required
- [`help wanted`](https://github.com/ColinHouse/kotobako/labels/help%20wanted) — the maintainer actively wants outside help here
- [`no-japanese-needed`](https://github.com/ColinHouse/kotobako/labels/no-japanese-needed) — pure engineering; tests, CI and migrations touch no user-visible strings at all

**AI-assisted patches are explicitly welcome**, with two conditions: you ran it yourself, and the
commit says which tool helped. Point your agent at `AGENTS.md` and it has everything.

## 代码签名策略 / Code Signing Policy

**本项目目前没有代码签名。** Windows 安装包未签名，首次运行会弹出 SmartScreen 警告，
需要点「更多信息 → 仍要运行」。签名的成本、可选方案与后续打算写在
[docs/CODE_SIGNING.md](docs/CODE_SIGNING.md)。

**This project is not code-signed yet.** The Windows installer is unsigned and SmartScreen will warn
on first run — choose "More info → Run anyway". The cost, the options and the plan are written up in
[docs/CODE_SIGNING.md](docs/CODE_SIGNING.md).

## 隐私政策 / Privacy Policy

**本软件不收集任何信息。** 没有遥测、没有使用统计、没有崩溃上报——仓库里不存在这类代码。

- **学习数据全在本机**：一个 SQLite 文件加一个媒体目录。
- **OCR 与分词都在本地跑**，不经过任何服务器。
- **出站请求只有两种情况**：你安装词典（EDRDG / GitHub），或者你填了 AI 密钥并使用 AI 解释——
  那时候这一句台词会发给你选的服务商（DeepSeek / OpenAI / Moonshot / 阿里云百炼）。不填密钥，应用完整可用。
- **AI 密钥存系统钥匙串**，不是磁盘上的明文文件。
- ⚠️ **手机复习需要开放局域网端口，该端口没有认证。** 同一网络里的任何人都能读写你的学习数据、
  并触发截屏。只在信得过的网络上开，用完就关，详见 [SECURITY.md](SECURITY.md)。

**This software collects nothing.** No telemetry, no usage statistics, no crash reporting — no such
code exists in the repository.

- **All study data stays on your machine**: one SQLite file plus a media directory.
- **OCR and tokenisation run locally**, never through a server.
- **Outbound requests happen in exactly two cases**: you install a dictionary (EDRDG / GitHub), or
  you supplied an AI key and used the AI explanation — then that one line goes to the provider you
  chose. Without a key the application is fully usable.
- **The AI key lives in the system keychain**, not in a plaintext file on disk.
- ⚠️ **Phone review opens a LAN port, and that port has no authentication.** Anyone on the same
  network can read and write your study data and trigger screenshots. Open it only on networks you
  trust, and close it when you are done — see [SECURITY.md](SECURITY.md).

---

# 关于 / About

## 鸣谢 / Acknowledgements

### 数据来源 / Data Sources

- [JMdict/EDICT](https://www.edrdg.org/wiki/index.php/JMdict-EDICT_Dictionary_Project) 与
  [KANJIDIC2](https://www.edrdg.org/wiki/index.php/KANJIDIC_Project)
  © 电子辞書研究開発グループ（EDRDG），[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)
- [Kanjium](https://github.com/mifunetoshiro/kanjium) © Uros O.，
  [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)，仅在用户主动安装时下载

### 开源库 / Open Source Libraries

- [FastAPI](https://github.com/fastapi/fastapi) · [SQLAlchemy](https://github.com/sqlalchemy/sqlalchemy) · [Alembic](https://github.com/sqlalchemy/alembic)
- [py-fsrs](https://github.com/open-spaced-repetition/py-fsrs)　自由间隔重复调度器
- [fugashi](https://github.com/polm/fugashi) + [unidic-lite](https://github.com/polm/unidic-lite)　日语分词
- [mss](https://github.com/BoboTiG/python-mss) · [RapidOCR](https://github.com/RapidAI/RapidOCR)　截屏与离线 OCR
- [Vue](https://github.com/vuejs/core) · [Vite](https://github.com/vitejs/vite) · [Tailwind CSS](https://github.com/tailwindlabs/tailwindcss) · [vite-plugin-pwa](https://github.com/vite-pwa/vite-plugin-pwa)

其余第三方组件的授权见 [NOTICE.md](NOTICE.md)。
The licences of all other third-party components are listed in [NOTICE.md](NOTICE.md).

### 思路灵感 / Inspiration

- [Anki](https://github.com/ankitects/anki)　间隔重复的事实标准。本项目保留独立的 FSRS 状态，Anki 只作为可选出口。
- [Yomitan](https://github.com/yomidevs/yomitan)　**本项目支持其词典包格式**，使已有的社区词典可以直接导入。
- [mokuro](https://github.com/kha-white/mokuro)　**本项目读取其 `.mokuro` 输出**以支持漫画，保留每块文字在页面上的位置。
- [Kamite](https://github.com/fauu/Kamite) · [jimaku](https://github.com/Ajatt-Tools/jimaku)　同类工具，也都采用 AGPL；本项目参考了它们的形态取舍，但未使用其源代码。
- 作者早先的两个实验仓库 `vocab_test`（PySide6 词汇测试）与 `anki_mpv`（Electron 字幕学习 + AnkiConnect）——
  AnkiConnect 逻辑、口语缩约规则、答案 diff 高亮与错误加权抽题的思想被保留下来。

## 贡献者 / Contributors

感谢以下贡献者对本项目做出的贡献。<br>
We thank the following contributors for their work on this project.

<a href="https://github.com/ColinHouse/kotobako/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=ColinHouse/kotobako" />
</a>

## Star History

<a href="https://www.star-history.com/#ColinHouse/kotobako&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=ColinHouse/kotobako&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=ColinHouse/kotobako&type=Date" />
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=ColinHouse/kotobako&type=Date" />
  </picture>
</a>

## 社区 / Community

目前没有 QQ 群或 Discord。提问、报 bug、提想法都走 GitHub：

- [Discussions](https://github.com/ColinHouse/kotobako/discussions)　提问与想法
- [Issues](https://github.com/ColinHouse/kotobako/issues)　bug 与功能请求

There is no QQ group or Discord yet. Questions, bug reports and ideas all go through GitHub:

- [Discussions](https://github.com/ColinHouse/kotobako/discussions) for questions and ideas
- [Issues](https://github.com/ColinHouse/kotobako/issues) for bugs and feature requests
