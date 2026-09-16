# Kotoba Studio · ことば Studio

**会记住语境的日语伴读工具。** 玩 Galgame / 看动画时，用很低的打断成本收藏台词（原句 + 截图 + 原声），自动整理成词卡，用 FSRS 在电脑或手机上复习。独立可用，Anki 只是可选出口。第一版面向中文母语的日语学习者。

> A local-first companion for learning Japanese from visual novels and anime: capture a line with its screenshot, confirm the words you met, and review them with FSRS on desktop or phone. Chinese-first UI; Anki export optional.

## 它解决什么

- **看得懂汉字却读不出**：含汉字的词默认生成"看汉字写读音"卡。
- **中日同形词误导**：勉強・大丈夫・手紙・怪我… 命中时卡片自动提醒。
- **口语缩约看不懂**：ちゃう ← てしまう、なきゃ ← なければ 等按词边界识别并标注。
- **收藏了却不复习**：会后三分钟短测 + FSRS 到期复习 + 手机扫码即用的 PWA。
- **数据不想被锁在别人的服务里**：SQLite + 媒体目录，一键备份/恢复，JSON / .apkg / AnkiConnect 导出。

## 快速开始

```bash
make setup     # 安装两端依赖（Python 3.12 + uv，Node 22 + npm），启用 git hooks
make run       # 构建前端并在 8720 端口同时提供 API 与网页
make help      # 全部命令
```

手机访问：`cd backend && uv run python -m kotoba serve --host 0.0.0.0`，然后在设置页扫码。
开发用 `make dev`（API 自动重载 + Vite 5174），提交前跑 `make check`。

开发时：`scripts/dev.sh` 同时启动后端（自动重载）与 Vite（端口 5174，代理 `/api` `/media` `/ws`）。

首次使用：设置页安装 JMdict（约 25 MB）→ 作品页添加作品 → 开始会话 → 采集页截取预览、框选对话框 → ⌘/Ctrl+Enter 收藏 → 收件箱确认建卡 → 复习。

## 架构

```
backend/kotoba/
  core/        配置、数据库、错误、事件、内置资源
  models/      ORM，按域拆分：capture / vocabulary / review / reference / system
  schemas/     请求与响应 DTO
  api/         capture（作品·会话·句子·截屏·Hook）· study（词条·语境·卡片·复习·短测）
               · system（词典·设置·AI·导出·备份）
  services/    jp（假名·归一化·分词·缩约·表达式）· text（去重·分析·入库）
               · dictionary/jmdict · ocr/providers · capture · learning · review
               · ai · export · backup
frontend/src/
  api/         客户端与按域拆分的类型
  composables/ useScreenCapture · useSessionLines · useInboxLines · useSettings
  components/  common · capture · inbox · review · settings
  views/       首页·作品·采集·收件箱·复习·短测·词库·词条·设置
docs/          产品分析、设计规格、ADR、路线图
```

技术：FastAPI · SQLAlchemy 2 + Alembic · py-fsrs · fugashi/unidic · mss ·
Apple Vision / Windows OCR / RapidOCR · Vue 3 + Vite + Tailwind 4 + PWA。

核心数据模型：作品 → 会话 → 句子（截图/音频）→ 语境（某句里的某个词）→ 词条/义项 → 卡片（FSRS 状态 + 设备归属）→ 复习记录（正式 / 短测分开）。详见 [设计规格](docs/superpowers/specs/2026-09-15-kotoba-studio-design.md)。

## 参与

欢迎参与，也**明确欢迎用 AI 工具写的贡献**——这个项目本身就是这么开发的。前提是有约束：
[AGENTS.md](AGENTS.md) 写明了 AI 工具的操作规则（必须跑通 `make check`、不得绕过 hook、
不得为了让检查通过而削弱检查、一次提交只做一件事），[docs/conventions.md](docs/conventions.md)
是代码约定，[CONTRIBUTING.md](CONTRIBUTING.md) 是给人看的入口。

最需要帮助的是 Windows 实机验证、日语分词的错例，以及中日同形词表的扩充。

## 文档

- [UI 设计说明](docs/ui-design-brief.md) · [开发约定](docs/conventions.md)
- [设计规格](docs/superpowers/specs/2026-09-15-kotoba-studio-design.md) · [M0 实施计划](docs/superpowers/plans/2026-09-15-m0-skeleton.md)
- [ADR 0001 技术栈](docs/adr/0001-tech-stack.md) · [路线图](docs/roadmap.md)

## 平台说明

- macOS：截屏需要在「系统设置 → 隐私与安全性 → 屏幕录制」中授权启动服务器的终端或应用；未授权时只会截到壁纸。
- Windows：内置 OCR 需要日语语言包（`Add-WindowsCapability -Online -Name Language.OCR~~~ja-JP~0.0.1.0`），或安装 `--extra ocr-onnx` 使用 RapidOCR。Windows 路径尚未在真机验证。
- Hook 工具（Textractor / Agent / LunaTranslator）可把文本发送到 `ws://<host>:8720/ws/hook`（纯文本或 `{"text": "..."}`）。

## 来源

本项目合并并重写了作者早先的两个实验仓库：`vocab_test`（PySide6 词汇测试）与 `anki_mpv`（Electron 字幕学习 + AnkiConnect）。它们的 AnkiConnect 逻辑、口语缩约规则、答案 diff 高亮与错误加权抽题思想被保留下来。

## 许可证与致谢

代码采用 **AGPL-3.0-or-later**（见 [LICENSE](LICENSE)）。选择理由见
[ADR 0002](docs/adr/0002-license.md)：本应用自己提供网络界面（手机通过局域网访问桌面端），
AGPL 第 13 条正对应这种形态；最接近的同类 Anki、Kamite、jimaku 也都用 AGPL。

词典数据来自 **JMdict/EDICT 项目**，© 电子辞書研究開発グループ（EDRDG），依
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) 授权使用：

- <https://www.edrdg.org/wiki/index.php/JMdict-EDICT_Dictionary_Project>

其余第三方组件的授权见 [NOTICE.md](NOTICE.md)。
