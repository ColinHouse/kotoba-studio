# Kotoba Studio 设计规格（v1 / M0 骨架）

日期：2026-09-15
状态：已按"自主执行"模式定稿；未经用户逐节确认的决策在 §11 列出，可随时推翻。

## 1. 一句话定位

Kotoba Studio 是一个"会记住语境的日语伴读工具"：在玩 Galgame / 看动画时，用很低的打断成本收藏台词（原句 + 截图 + 原声），自动整理成可复习的词卡，用 FSRS 在电脑或手机上复习。它是独立可用的学习应用，Anki 只是可选出口。首个目标用户是中文母语的日语学习者。

## 2. 目标与非目标

### 2.1 v1 目标（按优先级）

1. 首次使用 10 分钟内：框选 → 识别 → 收藏 → 完成一次复习，无需 Anki。
2. 玩游戏时每次收藏 ≤ 2 次按键，离开游戏 ≤ 3 秒；整理放在会后。
3. 卡片内容可靠：OCR 抖动去重、半句合并、截图与文本对齐、可回看修正。
4. 面向中文学习者的解释：语境义、读音、缩约还原、中日同形词提醒、能否日常使用。
5. 收藏后确实会复习：会后短测 + FSRS 到期复习 + 手机 PWA 复习。

### 2.2 非目标（v1 不做）

- 游戏引擎 Hook 的自研；只接收 Textractor / Agent / LunaTranslator 等已有工具的文本。
- 云同步、账号系统；v1 只在局域网内由桌面端提供服务。
- 手机离线复习（需要客户端 FSRS + 同步冲突处理，列入 M3）。
- 语音识别（无字幕音频），列入 M3。
- 自研复习算法；直接用 py-fsrs。

## 3. 用户流程

### 3.1 随手取词（Quick Pick）

快捷键 → 拖框 → OCR → 浮层显示分词结果（已知词灰色、未知词高亮）→ 点词收藏（创建 Line + Term + Encounter）或"收藏整句"（只创建 Line 进收件箱）。

### 3.2 持续伴读（Companion）

1. 选择作品（Source），首次为该作品选定对话框区域（Region 随 Source 保存）。
2. 后台监视器（watcher）定时截取区域，图像哈希无变化则跳过；变化后等待文本稳定（打字机效果结束）再 OCR。
3. 连续两次 OCR 文本相似度 ≥ 0.9 视为同一句；同句不重复入库。
4. 用户按"收藏这句"快捷键：保存最近一句的文本 + 当时的截图 +（M1）最近 N 秒音频。
5. 结束会话 → 会后整理页。

若使用 Hook 工具：文本从 WebSocket / 剪贴板进入，走同一条管线；截图在文本到达后延迟 300 ms 抓取（避开打字机动画）。

### 3.3 会后整理（Inbox）

收件箱列出本次会话收藏的句子。每句：分词高亮 → 选目标词 → 选义项（词典）→ 可选"解释这句"（AI）→ 确认，生成卡片；或丢弃。支持批量确认。

### 3.4 会后短测（Session Quiz）

对本次确认的卡片做 3 分钟短测：读音回忆 / 语境填空 /（M1）听音理解。结果记入 review_logs（mode = session_quiz），**不改变 FSRS 状态**。

### 3.5 正式复习（Scheduled Review）

到期卡片按设备归属分发：一张卡只由一个"归属端"（desktop / mobile）安排正式复习。卡片正面不显示截图和字幕（防泄题），作答后展示。评分 Again / Hard / Good / Easy → py-fsrs 更新。

### 3.6 词库与语境时间线（Library）

词条列表（认识状态、遇见次数、跨作品）。词条详情：所有 Encounter 按时间线展示（作品、位置、截图、原句）。"再见词"（遇见 ≥ 2 次仍未掌握）单独标出。

### 3.7 导出与备份

- Anki：AnkiConnect 直接加卡，或生成 .apkg。
- 备份：一键打包 SQLite（VACUUM INTO）+ 媒体目录为 zip；可恢复；可导出 JSON。

## 4. 领域模型

| 表 | 作用 | 关键字段 |
|---|---|---|
| sources | 作品 | id, kind(game/anime/video/manga/other), title, title_ja, region_json, created_at |
| sessions | 一次采集会话 | id, source_id, mode(quick/companion/import), started_at, ended_at, text_source(ocr/hook/subtitle/manual), stats_json |
| lines | 收藏的句子（语境载体） | id, session_id, source_id, text, raw_text, text_hash, screenshot_path, audio_path, position_json, speaker, translation_zh, tokens_json, status(inbox/kept/discarded), captured_at |
| terms | 词条（词典形） | id, headword, reading, pos, jmdict_id, known_status(unknown/learning/known/ignored), note, created_at；唯一 (headword, reading) |
| senses | 义项 | id, term_id, gloss_zh, gloss_en, origin(jmdict/yomitan/ai/user), ord |
| encounters | "遇到这个词的经历" | id, line_id, term_id, sense_id, surface, span_start, span_end, contraction_of, ai_explanation_json, created_at |
| cards | 可复习单位 | id, term_id, card_type(reading/meaning/cloze/listening), primary_encounter_id, review_owner(desktop/mobile/any), suspended, fsrs_state, fsrs_step, stability, difficulty, due, last_review, created_at；唯一 (term_id, card_type) |
| review_logs | 复习记录 | id, card_id, rating(1-4), mode(scheduled/session_quiz), reviewed_at, duration_ms, device_id, session_id |
| devices | 设备 | id, name, kind(desktop/mobile), last_seen |
| dict_entries / dict_forms | 词典（JMdict + 导入的 Yomitan 词典） | entry: id, dict_id, senses_json, pos_json, common；form: entry_id, text, kind(kanji/kana) 建索引 |
| dictionaries | 已安装词典 | id, title, revision, kind(jmdict/yomitan), entry_count, imported_at |
| llm_calls | AI 调用记录 | id, purpose, model, prompt_tokens, completion_tokens, cost_estimate, ok, created_at |
| settings | 键值设置 | key, value_json |

规则：
- 同词同义再次出现 → 新 Encounter 挂到同一 Term，不新建 Card。
- 同词不同义 → 新 Sense，允许单独建卡（card 的 primary_encounter 不同）。
- 同一句被 OCR 重复识别 → 同一 session 内 text_hash 相同则跳过；相邻句相似度 ≥ 0.9 视为同句。
- 已学过的词 → 收件箱显示"已掌握 / 学习中"状态，不默认建卡。

## 5. 架构

```
┌───────────────────────── 桌面端（Windows / macOS） ─────────────────────────┐
│ backend/ (Python 3.12, FastAPI, SQLite)                                      │
│  ├ api/         REST + WebSocket                                            │
│  ├ services/    capture(mss) · ocr(Vision/WinOCR/RapidOCR) · jp(fugashi)    │
│  │              dictionary(JMdict/Yomitan) · scheduling(py-fsrs) · ai(LLM)  │
│  │              media(ffmpeg) · export(AnkiConnect/apkg) · backup           │
│  └ 静态托管 frontend/dist（单端口，局域网可达）                                    │
│ frontend/ (Vue 3 + TS + Vite + Tailwind 4 + PWA)  ← 桌面浏览器 / pywebview 壳    │
└──────────────────────────────────────────────────────────────────────────────┘
                 ▲ 局域网 http://<ip>:8720（扫码打开，安装为 PWA）
┌────────────────┴─────────┐
│ 手机（浏览 / 正式复习）    │
└──────────────────────────┘
```

- 单一后端进程是唯一数据源；手机只是另一个客户端。
- 桌面专属能力（截屏、OCR、快捷键、Hook 接收）只在 `platform` 允许时注册；手机端 UI 隐藏这些入口。
- 数据目录：macOS `~/Library/Application Support/KotobaStudio`，Windows `%APPDATA%\KotobaStudio`（platformdirs）。内含 `kotoba.db`、`media/screens`、`media/audio`、`dicts`、`backups`。

## 6. 技术栈决策

保留用户提议的 Vue 3 (TS) + FastAPI + SQLite。理由与替代方案见 `docs/adr/0001-tech-stack.md`。要点：

- Python 是 OCR / 分词 / VAD / FSRS / Anki 生态的交汇点（pyobjc Vision、winocr、RapidOCR、fugashi、silero-vad、py-fsrs、genanki）；Node / Java / Ruby 后端最终都得带一个 Python sidecar。
- 调度只在服务端做（py-fsrs），不引入 ts-fsrs；手机离线复习（M3）时再引入。
- SQLAlchemy 2 + Alembic 从第一天开始，满足"备份与数据迁移"要求。
- 前端 Tailwind 4 做响应式（桌面侧栏 / 手机底部 Tab），vite-plugin-pwa 提供安装与壳缓存。
- 桌面壳：M2 用 pywebview（单工具链）；Tauri 仅在需要更精细托盘 / 覆盖层时考虑。
- 依赖管理：uv（Python）、npm（前端）。

OCR 提供者优先级：
| 平台 | 默认 | 后备 |
|---|---|---|
| macOS 13+ | Apple Vision（pyobjc，本机已验证：0.9 s，含框） | RapidOCR（onnxruntime） |
| Windows 10/11 | Windows.Media.Ocr（winocr，需日语语言包） | RapidOCR；高级用户可接 OwOCR/oneOCR |
| 任意 | 手动粘贴 / Hook 文本 | — |

## 7. API（M0 范围）

前缀 `/api`。所有响应 JSON；错误统一 `{error: {code, message}}`。

- 健康与设备：`GET /health`，`POST /devices/register`，`GET /connect-info`（局域网地址 + QR SVG）
- 作品：`GET/POST /sources`，`GET/PATCH/DELETE /sources/{id}`
- 会话：`POST /sessions`，`POST /sessions/{id}/end`，`GET /sessions/{id}/summary`，`GET /sessions`
- 句子：`GET /lines?session_id&status`，`POST /lines`（手动 / Hook 文本入库，含去重），`PATCH /lines/{id}`，`DELETE /lines/{id}`，`POST /lines/{id}/analyze`（分词 + 词典候选 + 认识状态）
- 采集（仅桌面）：`GET /capture/displays`，`POST /capture/screenshot`，`POST /capture/ocr`，`POST /capture/collect`（截图 + OCR + 建句一步完成），`WS /ws/hook`（接收 Hook 文本），`WS /ws/events`（推送新句到 UI）
- 词典：`GET /dict/lookup?q=`，`GET /dict/status`，`POST /dict/jmdict/install`
- 词条：`GET /terms?q&status&source_id`，`GET /terms/{id}`（含 Encounter 时间线），`PATCH /terms/{id}`，`POST /terms/bulk-known`
- 语境：`POST /encounters`，`PATCH /encounters/{id}`，`DELETE /encounters/{id}`，`POST /encounters/{id}/explain`（AI）
- 卡片：`POST /cards`（确认 → 建卡），`GET /cards?due&device_kind`，`PATCH /cards/{id}`，`GET /cards/stats`
- 复习：`GET /reviews/queue?device_id&limit`，`POST /reviews`（rating, mode）
- 短测：`POST /quiz/sessions/{session_id}`（生成题目），`POST /quiz/answers`
- AI：`POST /ai/explain`，`GET /ai/usage`，`PUT /settings/ai-key`（存系统凭据）
- 导出：`POST /export/anki-connect`，`POST /export/apkg`，`GET /export/json`
- 备份：`POST /backups`，`GET /backups`，`POST /backups/restore`
- 设置：`GET/PUT /settings`
- 媒体：`GET /media/{path}`

## 8. 关键算法与规则

- **归属过滤**：`queue` 只返回 `review_owner == device.kind or review_owner == 'any'` 的到期卡；`settings.review_owner_default` 决定新卡归属（有已注册手机时默认 mobile，否则 desktop）。
- **FSRS**：py-fsrs `Scheduler(desired_retention=0.9)`；`POST /reviews` 在 mode = scheduled 时调用 `review_card`，mode = session_quiz 时只写日志。
- **去重**：`text_hash = sha1(normalize(text))`；同 session 内命中即跳过；与上一句 `difflib.SequenceMatcher.ratio() >= 0.9` 视为同句并保留较长者。
- **OCR 归一化**：`・・・`/`...` → `…`；全角空格与 CJK 之间空格删除；半角片假名转全角；常见误识别表可配置。
- **表达式合并**：分词后对 2–6 个 token 的表面/词元拼接做 JMdict 最长匹配，把 しょう+が+ない 合并为 しょうがない（exp 条目优先）。
- **缩约还原**：`jp_contractions.json`（ちゃう→てしまう、なきゃ→なければ、とく→ておく、てる→ている…）用于展示"缩约形 ← 原形"与检索。
- **中日同形词**：`homograph_traps_zh.json` 种子表；命中时卡片与解释加"同形异义"提示。
- **AI 解释**：仅发送目标词、当前句、同 session 中之前的 ≤ 3 句；不发送之后的句子；返回结构化 JSON `{meaning_here, form, tone, needs_context, daily_usable, trap_for_zh}`；词典义与 AI 解释分开显示、可编辑；调用失败不阻塞收藏。

## 9. 错误处理

- OCR 提供者不可用（缺权限 / 缺语言包）→ 返回 `ocr_unavailable` 与修复指引；UI 提供"手动粘贴"通道。
- AnkiConnect 不可达 → 明确提示"打开 Anki 并启用插件"，可重试；模型 / 牌组缺失时自动创建（沿用 anki_mpv 的自愈逻辑）。
- AI 出错 → Encounter 照常保存，`ai_explanation_json = null`，UI 显示"稍后补充"。
- 备份恢复前先把当前库另存为 `pre-restore-*.zip`。

## 10. 测试

- pytest（backend/tests）：调度（短测不改 FSRS；归属过滤）、去重、归一化、表达式合并、缩约表、备份恢复往返、API 契约（TestClient + 临时 SQLite）。
- vitest（frontend）：kana 工具、答案 diff（源自 vocab_test 的高亮逻辑）。
- `vue-tsc --noEmit` 与 `ruff` 进 CI。
- OCR 集成测试仅在 macOS 上本地运行（渲染日文图片 → Vision），CI 跳过。

## 11. 未经确认的决策（可推翻）

1. 端口 8720（避开 AnkiConnect 8765）。
2. 手机端 v1 在线复习（依赖桌面端运行），离线复习延后到 M3。
3. 桌面壳延后到 M2，M0/M1 直接用浏览器。
4. 不把两个旧仓库的 git 历史合并进来；旧仓库改为归档（可逆）而非删除，删除命令交给用户执行。
5. ~~许可证 MIT~~ → 2026-09-16 改为 AGPL-3.0-or-later，见 ADR 0002。
6. Windows OCR 默认 winocr，未在本机验证（本机为 macOS）。
