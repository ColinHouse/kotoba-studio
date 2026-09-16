# Kotoba Studio 产品分析：竞品、定位与优势

调研日期：2026-09-15 / 16。星标数与最后提交日期来自 GitHub API 当日快照；功能描述来自各项目 README、文档与社区讨论。

## 0. 结论先行

1. **"截图 → OCR/Hook → 建卡 → 复习"的一体化工具并不新**：GameSentenceMiner（GSM）几乎就是你描述的产品，LunaTranslator 在中文圈也早已支持 Hook/OCR + AnkiConnect。所以"有截图取词"本身不是优势。
2. **但没有任何开源项目自己负责"学习闭环"**：GSM、LunaTranslator、asbplayer、mpvacious、jidoujisho 全部把复习交给 Anki；不依赖 Anki 的（YomiNinja、Kamite）又没有卡片和复习。唯一自带复习的是闭源订阅制的 Migaku（$10/月），而且不支持游戏。**"独立可学 + Anki 可选导出"在开源里是空位。**
3. **没有人专门服务中文母语者**：所有采集工具的释义/翻译流向是 日→英；LunaTranslator 面向中文用户，但它是"翻译器"，目标是读懂剧情而不是学会日语。
4. **macOS 是二等公民**：GSM 靠 OBS + Windows 引擎，LunaTranslator 仅 Windows，Kamite 没有 macOS 版；YomiNinja 支持 macOS 但已停更 13 个月。Apple Vision 本机验证可用（约 1 秒、带坐标）。
5. **领域整体在变冷**：YomiNinja、Kamite、Game2Text、Textractor、Agent 都 1–3 年没有新版本。一个持续维护的新项目有机会。

因此 Kotoba Studio 的定位不是"又一个截图取词器"，而是：**面向中文母语者的、会记住语境的日语学习闭环**——采集只是入口，资产是"遇到这个词的经历"，出口是 FSRS 复习（电脑或手机），Anki 只是可选导出。

## 1. 两个旧仓库：保留了什么

| 仓库 | 现状 | 保留到 Kotoba Studio 的部分 |
|---|---|---|
| `vocab_test`（PySide6，607 行） | 中英短语背诵桌面小程序：txt 词库、按错误率加权抽题、答案 diff 高亮 | 错误加权抽题的思想（会后短测）；答案 diff 高亮（`web/src/utils/diff.ts` 用 CJK/假名/拉丁分段重写） |
| `anki_mpv`（Electron + Vue，约 7k 行） | 视频 + 字幕学习 + AnkiConnect 建卡；kuromoji 分词；本地 LLM 解释 | AnkiConnect 服务（牌组/模板自愈、媒体上传）→ `server/kotoba/services/export/anki_connect.py`；口语缩约表（ちゃう→てしまう 等）→ `data/jp_contractions.json`；SRT 智能合并思路 → 列入 M1 字幕导入；LLM 解释提示词 → 升级为结构化中文解释 |

两个仓库都没有词库/复习记录/备份，这次全部补齐。原仓库保留为归档（可逆），新仓库 README 注明来源。

## 2. 做得好的项目

### 2.1 游戏/视觉小说采集类

| 项目 | ⭐ / 最后提交 | 平台 | 文本来源 | 每张卡保存 | 复习 | AI | 手机 | 主要短板 |
|---|---|---|---|---|---|---|---|---|
| **GameSentenceMiner** | 832 / 2026-09-15 | Win 为主，mac/Linux 可用 | Agent/Textractor/LunaTranslator Hook；自带 OwOCR 分支 | 句子、截图/GIF、VAD 裁剪的语音、可选 AI 翻译 | 只写 Anki | LLM 翻译（自带 key） | 无 | 必须先装 OBS 回放缓冲；Anki 是唯一数据库；配置项极多；OCR 是备选 |
| **LunaTranslator** | 13,210 / 2026-09-14 | 仅 Windows | Hook（主）、OCR、剪贴板 | 无自有数据，推到 AnkiConnect | 只写 Anki | 各家 LLM 翻译 | 无 | 翻译优先，学习是附属；引擎/插件面很大，新手配置重 |
| **YomiNinja** | 751 / 2025-08-04 | Win/Linux/mac | OCR（Paddle、Google Lens、manga-ocr、Apple Vision） | 无卡片功能 | 无 | 无 | 无 | 只有识别 + 弹词典，没有学习管线；13 个月无更新 |
| **Kamite** | 144 / 2025-04-03 | Win/Linux | OCR、mpv 字幕、Textractor/Agent、剪贴板 | 只写文本日志 | 无 | 无 | 无 | 无卡片/复习；停更 17 个月；manga-ocr 需 2.5 GB |
| **Textractor / Agent** | 2,690 / 2024-03；354 / 2024-04 | Windows | 引擎 Hook | — | — | — | — | 均处于社区维护状态；Agent（FRIDA 脚本）对新引擎更稳，被 GSM 预设为默认 |
| **OwOCR** | 298 / 2026-06-03 | 库，跨平台 | 包装 oneOCR、Apple Vision/Live Text、manga-ocr、Google Lens 等 | 输出到剪贴板/WebSocket/文件 | — | — | — | 只是引擎聚合，没有产品层 |
| Game2Text | 295 / 2023-09 | — | — | — | — | — | — | 已停止维护 |

### 2.2 动画/视频类

| 项目 | ⭐ / 最后提交 | 说明 | 短板 |
|---|---|---|---|
| **asbplayer** | 1,437 / 2026-09-14 | 浏览器播放器 + 扩展；Netflix/YouTube 字幕挖句到 Anki；已知词状态可从 Anki 同步 | 首张卡前要配 Anki + AnkiConnect + 模板 + CORS；无词典、无复习、iOS 不可用 |
| **mpvacious** | 889 / 2026-09-04 | mpv 快捷键建 Anki 卡（Opus 音频、AVIF 截图）；Ajatt-Tools 生态 | Lua 配置文件式工作流；README 自称在找维护者；无游戏输入 |
| **jidoujisho** | 1,759 / 2025-10-20 | Android 沉浸式套件（视频/EPUB/漫画/texthooker）| 仅 Android、需侧载、约一年一版 |
| Language Reactor / Migaku | 商业 | LR：Netflix/YouTube 双语字幕，Pro $5.95/月；Migaku：$10/月，自带复习 "Migaku Memory"、已知词覆盖率、一键卡片 | 闭源；LR 无游戏无本地文件；Migaku 没有官方 Anki 导出，复习记录被订阅锁住 |
| Immersion Kit / Nadeshiko | 语料库 | 动画例句 + 音频 + 截图搜索；Nadeshiko 有文档化 API（150 次/分，5000 次/月） | 无中文翻译；Immersion Kit API 不稳定 |
| Jimaku / Kitsunekko | 字幕源 | Jimaku 有 API（25 次/分）；Kitsunekko 域名 2026-10-02 到期，频繁宕机 | 需要客户端自带回退 |

### 2.3 复习与词典类

| 项目 | 说明 | 对我们的启示 |
|---|---|---|
| **jpdb.io** | 免费；已知词状态全局同步；21,434 个"媒体牌组"覆盖 1,399 部动画/VN，显示每部作品的词汇覆盖率；自研 SRS | "作品词汇覆盖率"和"跨作品已知词"是被验证过的需求；但 jpdb 没有采集，语料是别人预制的 |
| **Yomitan** | 2,825 ⭐；弹出词典事实标准；词典 zip 格式（`term_bank_N.json` 八元组）；社区有 小学館中日辞典、中日大辞典 等日中词典 | 支持导入 Yomitan 词典即可获得中文释义生态（M2） |
| **jmdict-simplified** | JMdict JSON，**不含中文释义**（仅 eng/ger/rus 等） | M0 用 JMdict 英文释义 + 用户手填中文；Tomoshi 开放数据集（CC BY-SA，JMdict 衍生，含简繁中文释义）是 M2 候选 |
| **py-fsrs 6.3.2 / ts-fsrs 5.4.2** | FSRS-6，官方实现 | 直接复用；短测不调用 `review_card` 即可与正式复习隔离（已实现并有测试） |
| Anki 移动端 | AnkiDroid 免费；AnkiMobile $24.99；AnkiWeb 限 100 MB | 带截图/音频的沉浸卡组很快撞上 AnkiWeb 上限；这是"自带手机复习"的现实理由 |

### 2.4 中文市场

MOJi辞書（词典 + 例句 + MOJi Test，PRO 会员制）、沪江开心词场（游戏化背词）、每日日语听力等都是"教材式"产品：词表来自 JLPT/教材，而不是用户自己的游戏和动画。中文 Galgame 圈的主流路线是 LunaTranslator（或 Yomitan + ShareX）→ Anki，配置门槛高、卡片要手工组装、复习必须回到 Anki。

## 3. "有同款吗？"——有，以及我们和它的差别

你的想法（框选区域 → OCR/读内存 → 截图建卡 → 测试 → 接 DeepSeek）与 **GameSentenceMiner** 高度重合。逐项对比：

| 维度 | GSM | Kotoba Studio（本次实现的 M0 + 规划） |
|---|---|---|
| 文本来源 | Hook 为主，OCR 备选 | OCR（Apple Vision / Windows OCR / RapidOCR）与 Hook（WebSocket + 剪贴板）并列，同一条管线 |
| 截图与音频 | OBS 回放缓冲（必须安装 OBS） | 直接截屏（mss）；音频 M1 用系统回环，不依赖 OBS |
| 卡片存放 | Anki（唯一） | 本地 SQLite：作品 / 会话 / 句子 / 词条 / 义项 / 语境 / 卡片 / 复习记录 |
| 复习 | Anki | 内置 FSRS；会后短测与正式复习分开记录 |
| 手机 | 无 | 同一服务的 PWA，卡片按设备归属分配 |
| 语言 | 英文 | 中文界面；中日同形词提醒；口语缩约还原；中文语境解释 |
| 平台 | Windows 优先 | macOS 与 Windows 并列（macOS 已实测） |
| AI | 翻译 | 结构化解释（这句什么意思 / 词形 / 语气 / 需要上下文 / 能否日常用 / 中文母语者提醒），只发送之前的台词 |

GSM 依旧在两点上更强：成熟的 Hook 生态整合（Agent/Textractor 端口预设）和 VAD 语音裁剪。这两点我们在 M1 直接借鉴（监听 6677/9001/2333 端口 + silero-vad），不重新发明。

## 4. 我们应该形成的优势（验证目标）

| 优势目标 | 落地 | 怎样证明 |
|---|---|---|
| 首次使用更容易 | 安装后：添加作品 → 框选 → 收藏 → 收件箱确认 → 复习，全程不需要 Anki；JMdict 一键安装 | 新用户 10 分钟内独立完成第一张可复习卡片 |
| 更少打断剧情 | 区域随作品保存；收藏一键（⌘/Ctrl+Enter，M1 全局快捷键）；整理放在会后 | 每次收藏 ≤ 2 次按键，离开游戏 ≤ 3 秒 |
| 卡片内容更可靠 | OCR 归一化、前缀增长与相似度去重、表达式合并（しょう+が+ない→しょうがない，且校验读音避免 今日は→こんにちは）、缩约按词边界识别、可回看修正 | 无需修正的卡片比例、平均修正时间 |
| 更适合中文学习者 | 卡片按原文用字选择词头（假名/汉字）；中日同形词种子表 78 条并在卡片上提醒；中文"这里的意思"字段；AI 解释区分词典与推断 | 用户能解释原句并在新句子里认出该词 |
| 收藏后更容易复习 | 会后短测（读音/填空/释义）+ FSRS 到期复习 + 手机 PWA；"再见词"标记 | 收藏后 24h 内实际复习比例、延迟测试表现 |
| 数据是自己的 | 本地 SQLite + 媒体目录；一键备份/恢复；JSON 导出；Anki 导出（AnkiConnect 或 .apkg） | 备份恢复往返测试通过（已有） |

## 5. 新想法（在 GPT 建议之外）

1. **开玩前预习（作品覆盖率）**：导入作品脚本/字幕或用会话累积的文本，算出"这部作品你认识 xx%"，列出高频未知词供预习——jpdb 的媒体牌组做法，但基于用户自己的文本，任何游戏都适用。（M2）
2. **语境时间线与"再见词"**：每个词跨作品的遇见记录（已实现）；遇见 ≥ 2 次仍未掌握的词在词库高亮——这是自然间隔的重复，价值最高。（M0 已做基础）
3. **读音优先**：中文母语者认得汉字读不出音，含汉字的词默认生成"看汉字写读音"卡，假名输入按平/片假名等价判定。（M0 已做）
4. **中日同形词提醒**：78 条种子表（勉強、大丈夫、手紙、怪我、迷惑…），命中时卡片与解释自动加提示；后续用 KANJIDIC2 的拼音字段扩展。（M0 已做）
5. **口语缩约还原按词边界识别**：避免把 奢って 里的 って 当成引用助词（M0 已修）；卡片显示"缩约形 ← 原形"。
6. **听力优先卡**：Galgame 有配音，M1 用系统音频回环 + silero-vad 裁出这句的原声，正面只放音频，三段揭示（听懂→读音→意思）。
7. **Hook 文本与截图/音频对齐**：文本到达后延迟 300 ms 抓图避开打字机动画，并从环形缓冲取前 N 秒音频。（M1）
8. **剧透保护**：卡片正面不出现截图/整句答案（已做）；AI 只收到之前 ≤ 3 句，不收之后的（已做并有测试）。
9. **零账号局域网同步**：设置页显示二维码，手机扫码即用（已做）；"同一张卡只由一端安排复习"用归属字段实现（已做）。
10. **AI 费用可见**：每次调用记录 token 与估算费用，设置页可见；deepseek-flash 缓存命中价 $0.006/M，一条解释不到 0.001 美元。（已做）
11. **字幕文件导入**：动画有 .srt/.ass 时（Jimaku 可取），按时间轴批量生成句子并用 ffmpeg 切片，沿用 anki_mpv 的媒体服务。（M1）
12. **一键会后复盘**：收藏/确认/新词/再见词/短测正确率/时长（已做），后续加连续天数。
13. **可替换的模型服务**：预设 DeepSeek / OpenAI / DashScope / Moonshot / 本地 Ollama，Key 存系统钥匙串。（已做）

## 6. 改进后的产品流程

```
选择作品 → 首次框选对话框（随作品保存）
   ↓ 玩游戏时：⌘/Ctrl+Enter 收藏（截图 + OCR），或 Hook/剪贴板自动进入
   ↓ 会话结束：收件箱逐句确认（点词 → 候选释义 → 中文"这里的意思" → 卡片类型）
   ↓ 三分钟短测（读音/填空/释义，只记录，不影响 FSRS）
   ↓ 复盘：新词 / 再见词 / 正确率
   ↓ 之后：手机或电脑做 FSRS 到期复习；Anki 可选导出
```

与 GPT 建议的差异：
- "读内存"落地为**接收 Hook 工具的 WebSocket/剪贴板文本**（已实现 `/ws/hook`），不自研引擎适配。
- 词典义与 AI 解释在数据上分开存（`senses` vs `encounters.ai_explanation_json`），UI 分区显示。
- 测试三类中"听音理解"依赖音频，放到 M1；读音回忆与语境填空已可用。

## 7. 技术栈结论

保留 **Vue 3 (TS) + FastAPI + SQLite**。理由：OCR（pyobjc Vision、winocr、RapidOCR）、分词（fugashi）、VAD（silero-vad）、FSRS（py-fsrs）、Anki 导出（genanki）全部是 Python 生态；Node/Java/Ruby 后端最终都要带一个 Python sidecar。细节见 `docs/adr/0001-tech-stack.md`。

## 8. 风险与验证清单

- **屏幕录制权限**：macOS 上未授权的进程截屏只得到壁纸（本次浏览器验证遇到）；正式分发需打包成 .app 并引导授权。Windows 需要日语 OCR 语言包（设置页给出安装命令）。
- **OCR 抖动**：已处理省略号、半角片假名、前缀增长；游戏字体风格化时需要 RapidOCR/manga-ocr 备选（M1 增加"引擎对比"面板）。
- **中文释义来源**：M0 依赖用户手填 + AI；M2 导入 Yomitan 日中词典或 Tomoshi 数据集。
- **DeepSeek 模型命名变动**：2026-09 官方模型为 deepseek-flash / deepseek-v4-pro，已按此配置；设置页允许改模型名。
- **手机离线**：v1 需要桌面端在线（局域网）；离线复习需要客户端 FSRS 与同步（M3）。

## 数据来源

GitHub API（stargazers_count / pushed_at，2026-09-15）；各项目 README；docs.gamesentenceminer.com；lunatranslator.org；docs.asbplayer.dev；jpdb.io；yomitan.wiki；huggingface.co/datasets/yuany1z/tomoshi-dict-data；api-docs.deepseek.com/quick_start/pricing（2026-09-16 核对）；pypi.org（rapidocr 3.9.2、oneocr 1.0.12、winocr、mss 10.2、pywebview 6.2.1、PyAudioWPatch 0.2.12.8）。
