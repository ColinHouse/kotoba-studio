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
2. **说明用了 AI。** 在提交信息末尾加一行 trailer：

   ```
   Assisted-by: Claude Code (claude-opus-5)
   ```

   这不是减分项，只是让 review 知道该重点看什么。用 `Assisted-by:` 而不是
   `Co-Authored-By:`：后者在 GitHub 上会被算作共同作者，而工具不是作者——你才是，
   责任也在你。（本仓库早期提交带的是 `Co-Authored-By:`，那是 Claude Code 的默认行为；
   两种都接受，新提交请优先用 `Assisted-by:`。）Linux 内核 2026 年的
   [coding-assistants 政策](https://docs.kernel.org/process/coding-assistants.html)
   同样要求：AI 绝不能自己添加 `Signed-off-by:`。
3. **一个 PR 只做一件事。** 不要批量提交自动生成的大范围改动（重命名、格式化、依赖升级
   全糊在一起）。这类 PR 会被关掉。

We explicitly welcome patches written with Claude Code, Codex, Cursor, Copilot and similar
tools — this project is built that way. Read [`AGENTS.md`](AGENTS.md) first, verify your change
locally, mention the tool in the PR, and keep one PR to one thing.

## 开发环境

```bash
make setup     # 安装两端依赖，并启用仓库自带的 git hooks
make dev       # API 8720 + Vite 5174，都自动重载
make help      # 看全部命令
```

Windows 上 make 需要在 Git Bash 里运行（`winget install ezwinports.make` 安装）；
PowerShell / CMD 会让 make 回退到 cmd.exe，Unix 风格的 recipe 会失败。仓库用
`.gitattributes` 在所有平台检出 LF；如果旧检出的 `format:check` 全红，在确认没有未提交
改动后运行 `git read-tree --reset -u HEAD` 重新检出。

## 提交前必须通过

```bash
make check
```

一条命令跑完两端的 lint、格式、类型、测试和构建，和 CI 一模一样（CI 还会在 macOS 与 Windows 上
再跑一遍后端）。`make fix` 能自动修掉大部分格式和 lint 问题。

仓库自带两个 git hook（`make setup` 或 `make hooks` 启用）：

- **pre-commit**：拦截运行时数据、构建产物、密钥和大文件，并对暂存的文件跑 lint。
- **commit-msg**：要求 Conventional Commits 格式，例如 `fix(jp): match contractions on token boundaries`。

不要用 `--no-verify` 绕过它们。hook 拦住你的时候，要修的是原因。

## 代码约定

写代码前请看 [docs/conventions.md](docs/conventions.md)：分层怎么分、事务边界在哪、
日语处理有哪些反直觉的坑。如果你用 AI 工具，让它先读 [AGENTS.md](AGENTS.md)。

## 特别欢迎的贡献

- **Windows 上的实机反馈。** 内置 OCR（日语语言包）与全局快捷键已在 Windows 11 上验证；仍然需要真机的是
  系统音频回环（#14），以及各个 Galgame 对话框的识别效果。
- **日语处理的细节。** 分词边界、口语缩约、表达式合并出错的具体例子，附上原句最有用。
- **中日同形词表。** `backend/kotoba/data/homograph_traps_zh.json`，纯数据，加词条不用改代码。
- **游戏兼容性。** 哪个 Galgame 的对话框 OCR 识别不好、Hook 工具接不上，欢迎开 issue 说明。

## 认领一个 issue

在下面评论一句就行，维护者会尽快 assign 给你。**assign 之后那个 issue 就是你的**，别人不该再动它。

这条是有代价换来的：#114 上有人礼貌地问「能分配给我吗」，而另一个人已经直接交了 PR 并合并了。先举手的人什么也没拿到。当时没有任何约定，两个人的做法都不算错——所以现在有了。

几点实际的：

- **GitHub 只能 assign 在该 issue 下评论过的人。** 所以必须在你想做的那个 issue 下留言，在别处说不算。
- **不用等 assign 才开始看代码**，但动手之前最好先留言，省得撞车。
- 认领后如果做不下去了，说一声就行，**没有任何负担**。放着不说才会让别人一直等。
- 超过一两周没动静的认领，维护者可能会释放掉，让别人接手。

带自己的 coding agent 来的话，挑 `agent-ready` + `no-japanese-needed`，把 [`AGENTS.md`](AGENTS.md) 交给它。注意**界面文案是简体中文**，所以不懂中文的话优先挑测试、CI、迁移这类不含用户可见字符串的。

## 提 issue

说明你在做什么、期望什么、实际发生了什么。涉及识别问题时，附上原句文本（不用附截图，
截图里可能有剧透）、作品名和所在平台。

### 标签怎么看

不用自己贴标签，维护者会补；但看懂它们能帮你挑到合适的活：

- **类型**（每个 issue 恰好一个）：`bug`、`enhancement`、`documentation`、`refactor`、`test`。
  另有领域标签 `japanese`（分词、读音、缩约、表达合并）与 `accessibility`。
- **`agent-ready`** —— 规格完整到**可以交给自动运行的 coding agent 直接实现**：问题确凿、
  子系统明确、范围有边界、验收标准写死、验证方式说清楚、没有悬而未决的产品决策。
  它是**就绪状态，不是署名**——由 AI 发现或撰写的 issue 不会因此自动就绪。
- **`needs-hardware`** —— 要真机或系统授权才能验证，**agent 不要接**，必须有人在真机上做。
- **`good first issue`** —— 真的适合第一次来的人：影响面小、不需要跨文件协调、不需要背景知识。
  **不等于"改动小"。**
- **`help wanted`** —— 明确希望有外部的人来接。
- **`no-japanese-needed`** —— 纯工程改动，不懂日语也能做。注意用户可见的文案是简体中文，
  所以"要写界面文案"的 issue 即使不需要日语，也不是零语言门槛。

带上自己的 coding agent 来的话：挑 `agent-ready` + `no-japanese-needed`，把
[`AGENTS.md`](AGENTS.md) 交给它，规矩都在里面（开 issue 时该怎么贴标签见 §8）。

## 许可证

贡献的代码按 [AGPL-3.0-or-later](LICENSE) 授权。词典数据的授权见 [NOTICE.md](NOTICE.md)。
