# 参与贡献 · Contributing

这是一个个人项目，但欢迎任何人参与。下面这几条不是门槛，是为了让改动能被快速看懂和合并。

> **English:** this is a personal project but contributions are welcome. Everything below
> applies regardless of whether a human or an AI wrote the patch.

## 欢迎用 AI 写代码 · AI-assisted contributions are welcome

**明确欢迎使用 Claude Code、Codex、Cursor、Copilot 等工具编写的贡献。** 我自己就是这么开发的，
没有理由要求别人不用。仓库根目录的 [`AGENTS.md`](AGENTS.md) 就是给这类工具准备的：里面写清了
目录结构、必须跑通的命令，以及那些"看起来像 bug、其实是刻意为之"的规则。

只有三条要求：

1. **你自己读过、跑过。** 提交前在本机跑通下面的命令，并实际打开应用点一遍你改的地方。
   不接受没验证过就丢过来的补丁——无论作者是人还是模型。
2. **在 PR 里说明用了 AI。** 一句话就够（"用 Claude Code 写的，我核对并测试过"）。这不是
   减分项，只是让 review 时知道该重点看什么。
3. **一个 PR 只做一件事。** 不要批量提交自动生成的大范围改动（重命名、格式化、依赖升级
   全糊在一起）。这类 PR 会被关掉。

We explicitly welcome patches written with Claude Code, Codex, Cursor, Copilot and similar
tools — this project is built that way. Read [`AGENTS.md`](AGENTS.md) first, verify your change
locally, mention the tool in the PR, and keep one PR to one thing.

## 开发环境

```bash
cd backend  && uv sync --extra dev --extra macos   # Windows 用 --extra windows
cd frontend && npm ci
./scripts/dev.sh                                   # API 8720 + Vite 5174，均自动重载
```

## 提交前必须通过

```bash
cd backend  && uv run ruff check . && uv run ruff format --check . && uv run pytest -q
cd frontend && npm run typecheck && npx vitest run && npm run build
```

CI 会在 Ubuntu / macOS / Windows 上跑同样的命令。

## 特别欢迎的贡献

- **Windows 上的实机反馈。** 内置 OCR（需要日语语言包）这条路径从没在真机上跑过。
- **日语处理的细节。** 分词边界、口语缩约、表达式合并出错的具体例子，附上原句最有用。
- **中日同形词表。** `backend/kotoba/data/homograph_traps_zh.json`，纯数据，加词条不用改代码。
- **游戏兼容性。** 哪个 Galgame 的对话框 OCR 识别不好、Hook 工具接不上，欢迎开 issue 说明。

## 提 issue

说明你在做什么、期望什么、实际发生了什么。涉及识别问题时，附上原句文本（不用附截图，
截图里可能有剧透）、作品名和所在平台。

## 许可证

贡献的代码按 [AGPL-3.0-or-later](LICENSE) 授权。词典数据的授权见 [NOTICE.md](NOTICE.md)。
