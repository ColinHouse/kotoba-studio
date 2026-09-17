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
- **打包与签名。** 见 M4；届时补一份 `CODE_SIGNING.md`（参考 localsend）。

## M2 · 知道该学什么（进行中，[milestone 2](https://github.com/ColinHouse/kotoba-studio/milestone/2)）

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

## M3 · 什么都读得进来（[milestone 3](https://github.com/ColinHouse/kotoba-studio/milestone/3)）

M3 是**内容源扩展**。应用此前只吃 galgame 与带字幕动画，漫画与轻小说这两个日语学习者最大的内容类型完全没覆盖；而且字幕在 M1 里只做了文本那一半，配视频切原声的那一半（[#67](https://github.com/ColinHouse/kotoba-studio/issues/67)）在 `#7` 里被划出范围后一直没人捡回来。M3 补齐多媒介阅读与视听体验。

本轮架构评估结论：**不拆服务**——分层零违规、services 依赖无环、114 个文件平均 66 行、6 万词条导入 2.3 秒且内存只涨 12MB；唯一要动的是内容定位模型（[#51](https://github.com/ColinHouse/kotoba-studio/issues/51)）与离线同步模型（[#59](https://github.com/ColinHouse/kotoba-studio/issues/59)），两者都各自有 ADR。

- **通用内容定位模型**（[#51](https://github.com/ColinHouse/kotoba-studio/issues/51)）：从单篇时间轴扩展到支持页、行、分卷的统一坐标模型。
- **Mokuro 漫画 OCR 导入**（[#52](https://github.com/ColinHouse/kotoba-studio/issues/52)）与**漫画阅读视图**（[#53](https://github.com/ColinHouse/kotoba-studio/issues/53)）：画面即语境，点击框选文本查词建卡。
- **EPUB 轻小说解析与导入**（[#54](https://github.com/ColinHouse/kotoba-studio/issues/54)）：按 spine 拆句并保留振假名入库。
- **回溯媒体缓冲**（[#55](https://github.com/ColinHouse/kotoba-studio/issues/55)）：内存循环缓冲，事后为已过去的台词补齐截图与音频。
- **汉字掌握度进度网格**（[#56](https://github.com/ColinHouse/kotoba-studio/issues/56)）：基于 KANJIDIC2 的常用汉字学习进度透视。
- **学习统计页**（[#57](https://github.com/ColinHouse/kotoba-studio/issues/57)）：纯 SQL 聚合与诚实留存率轨迹。
- **字幕配视频**（[#67](https://github.com/ColinHouse/kotoba-studio/issues/67)）：ffmpeg 切原声与截图，为台词卡片补齐视听语境。
- **凝缩音频**（[#68](https://github.com/ColinHouse/kotoba-studio/issues/68)）：抽取纯台词音频流，通勤反复盲听。

## M4 · 装得上、带得走（[milestone 4](https://github.com/ColinHouse/kotoba-studio/milestone/4)）

M4 是**交付**。从开发者使用的命令行启动，走向真正给终端用户开箱即用的产品形态：双击可用、手机离线复习、游戏时不用切窗口。

- **手机离线复习与可合并同步**（[#59](https://github.com/ColinHouse/kotoba-studio/issues/59)）：客户端 ts-fsrs 调度与基于只追加日志的确定性重放合并。
- **pywebview 桌面壳与托盘**（[#60](https://github.com/ColinHouse/kotoba-studio/issues/60)）：双击启动本地服务、常驻托盘菜单与优雅退出。
- **打包与签名**（[#61](https://github.com/ColinHouse/kotoba-studio/issues/61)）：macOS .app 与 Windows 安装包自动化分发。
- **游戏内透明覆盖层**（[#62](https://github.com/ColinHouse/kotoba-studio/issues/62)）：游戏窗口上方悬浮即时分词与一键收藏，无需频繁切屏。

## M5 · 测得住（[milestone 5](https://github.com/ColinHouse/kotoba-studio/milestone/5)）

M5 是**质量**。工程化债项的系统性清偿：34 个前端组件目前零测试、没有 E2E、没有性能基线、CHANGELOG 缺少强制护栏。

- **前端组件测试基建**（[#69](https://github.com/ColinHouse/kotoba-studio/issues/69)）：为高频交互组件补齐 vitest 测试。
- **Playwright 主路径 E2E 冒烟测试**（[#70](https://github.com/ColinHouse/kotoba-studio/issues/70)）：走通采集、整理、复习全链路。
- **Hypothesis 日语性质测试**（[#71](https://github.com/ColinHouse/kotoba-studio/issues/71)）：针对分词、振假名与音高算子做基于性质的随机边界轰炸。
- **导入与查词性能基线**（[#72](https://github.com/ColinHouse/kotoba-studio/issues/72)）：建立万级词条与长文本导入的性能回归防护。
- **文档债项补齐**（[#73](https://github.com/ColinHouse/kotoba-studio/issues/73)）与**CHANGELOG 联动强制检查**（[#77](https://github.com/ColinHouse/kotoba-studio/issues/77)）：杜绝版本更新文档脱节。
- **协议性文档变更防护**（[#74](https://github.com/ColinHouse/kotoba-studio/issues/74)）：受保护文件必须由人工审核通过后合入。
- **Alembic 迁移往返与数据升级测试**（[#75](https://github.com/ColinHouse/kotoba-studio/issues/75)）：保障数据库升降级安全。
- **可访问性与对比度基线**（[#76](https://github.com/ColinHouse/kotoba-studio/issues/76)）：评估墨色编码系统的对比度与键盘可达性。
