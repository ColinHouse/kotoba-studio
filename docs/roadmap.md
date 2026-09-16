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

## M1 · 持续伴读与音频（已完成，2026-09-17）

区域监视器、三种 Hook 主动连接、剪贴板、字幕导入、引擎对比已合并（#6–#12）。
仍开着的是两条 `needs-hardware`：全局快捷键（#13）与系统音频回环 + VAD（#14）——
它们要系统授权与真机，CI 和 agent 都验证不了，必须有人在真机上做。

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

## M2 · 知道该学什么（[issue 队列](https://github.com/ColinHouse/kotoba-studio/milestone/2)）

M1 把采集做强了：一晚上能收五百句。瓶颈因此往后挪了——**这五百句里该学哪二十个词？**
别的开源方案都停在「Anki 前端」，没人回答这个问题；jpdb 真正的护城河也不是它的 SRS，
而是「开玩之前就知道这部作品对我有多难」。M2 补的就是这一层。

- **词典与词频数据层**：读 Yomitan 词典包（社区日中词典、频率表、音高表都是这个格式）。
  只支持格式、不打包任何第三方词典——用户自带数据，版权不落在仓库里。
- **作品覆盖率与开玩前预习**：按 token 算覆盖率（认识 100 个高频词 ≠ 认识 100 个生僻词），
  列出最值得先学的生词，一键建成预习牌组。
- **已知词批量导入**（列表 / Anki / jpdb）：没有它，前面几项对老用户全是噪音——
  词库空的时候，「生词」里全是他早就会的词。
- **音高重音**（Kanjium，CC-BY-SA 4.0，与 JMdict 同一许可）：卡面音高线 + 音高小测。
  这一条专冲中文母语者——有声调的母语者要么逐字套声调、要么干脆无视，
  结果是词都认识、一开口不像日语。这是第一版最该有的差异化。
- **FSRS 参数个人化**：`py-fsrs` 自带 `Optimizer`，喂用户自己的复习记录算出专属参数与最优保留率。
  Anki 要装插件、导出、跑脚本；我们拥有完整记录，可以做成一个按钮。
  这是「独立应用而不是 Anki 前端」最有说服力的一处。
- **i+1 例句优选**：整句只有一个生词的句子最有效。整句、分词、`known_status` 我们都有了，
  只差把它用起来。

## M3 · 装得上、带得走

打包与签名从 M2 挪到这里，原因是它**验证不了**：证书、真机、各平台安装器都需要人，
CI 与 agent 都证明不了它能用。M2 整条线相反，全部可以在 CI 里验证。

- pywebview 窗口 + 托盘 + PyInstaller 打包（签名的 macOS .app、Windows 安装包）；补 `CODE_SIGNING.md`。
- 客户端 ts-fsrs + 冲突可控的同步（仍保持「一张卡一个归属端」）。
- 无字幕音频的转写（anime-whisper / Qwen3-ASR 日语动画微调模型）。
- KANJIDIC2 拼音扩展同形词提醒。
