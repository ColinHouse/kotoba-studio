# 路线图

## M0 · 可运行骨架（已完成，2026-09-16）

- FastAPI + SQLite + Alembic；作品 / 会话 / 句子 / 词条 / 义项 / 语境 / 卡片 / 复习记录 / 设备 / 词典 / AI 调用日志。
- JMdict 一键安装（218k 条），按写法查词，表达式合并（校验读音）。
- OCR 提供者：Apple Vision（已实测）、Windows OCR（未在 Windows 实测）、RapidOCR（可选）、手动粘贴；`/ws/hook` 接收 Hook 文本。
- 收件箱确认建卡；FSRS 复习（设备归属）；会后短测（读音/填空/释义）与复盘。
- AI 结构化解释（DeepSeek 默认，OpenAI 兼容），Key 存钥匙串，费用估算。
- AnkiConnect / .apkg / JSON 导出；备份与恢复。
- Vue 3 PWA：桌面侧栏 / 手机底部 Tab；扫码连接。
- 测试：52 个 pytest（含 Vision 集成测试）、8 个 vitest；CI 覆盖 ubuntu/macos/windows。

## M1 · 持续伴读与音频

- 区域监视器：图像哈希变化检测 + 文本稳定后 OCR + 自动去重，"收藏这句"全局快捷键（pynput）。
- 主动连接 Textractor（6677）/ Agent（9001）/ LunaTranslator（2333）WebSocket，剪贴板监听。
- Hook 文本到达后延迟抓图；系统音频回环（Windows PyAudioWPatch，macOS ScreenCaptureKit）+ silero-vad 裁剪原声；听音卡与听音短测。
- 字幕导入（.srt/.ass + 视频路径 → ffmpeg 切片），沿用 anki_mpv 的媒体逻辑。
- 引擎对比面板（同一区域多引擎结果并排）。

## 工程化待办（不绑定里程碑）

- **前端类型从 OpenAPI 生成。** `frontend/src/api/types/` 目前是手写的，改后端字段时容易忘记
  同步——本轮就漏过一次（`streak_days`、`known_term_count`），靠 `vue-tsc` 才发现。
  用 `openapi-typescript` 或 `@hey-api/openapi-ts` 从 FastAPI 的 schema 生成，并在 CI 里
  校验生成结果是最新的，可以整类消除这种漂移。现在没做是因为手写类型按域组织得更好读，
  而且类型检查已经能抓住漏字段；等接口稳定、字段变动变频繁时再换。
- **打包与签名。** 见 M2；届时补一份 `CODE_SIGNING.md`（参考 localsend）。

## M2 · 桌面壳、词典与作品统计

- pywebview 窗口 + 托盘 + PyInstaller 打包（签名的 macOS .app、Windows 安装包）。
- 导入 Yomitan 格式词典（含社区日中词典）与 Tomoshi 开放数据（简繁中文释义）。
- 作品覆盖率与开玩前预习；已知词批量导入（jpdb/Anki）。
- KANJIDIC2 拼音扩展同形词提醒。

## M3 · 手机离线与语音识别

- 客户端 ts-fsrs + 冲突可控的同步（仍保持"一张卡一个归属端"）。
- 无字幕音频的转写（anime-whisper / Qwen3-ASR 日语动画微调模型）。
