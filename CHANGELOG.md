# Changelog

All notable changes to this project are documented here, newest first.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- 采集：框选屏幕区域，OCR 识别台词，连同截图收进收件箱；支持 Apple Vision、Windows OCR、
  RapidOCR 与手动粘贴，Hook 工具可通过 `ws://<host>:8720/ws/hook` 送入文本。
- 采集：可绑定游戏窗口（列出运行中的真实窗口，按进程与标题选择，不做名字猜测），对话框区域相对窗口
  客户区保存，窗口移动或换分辨率后自动跟随；快捷键与区域监视器共用同一套解析。
- 采集：绑定窗口后优先读窗口自身像素（`PrintWindow`），游戏被别的窗口或覆盖层挡住也能识别；
  引擎不配合时自动回退屏幕截图。
- 收件箱：分词后逐词确认，词典候选来自 JMdict，可填写"这里的意思"并选择要建的卡片类型。
- 复习：内置 FSRS 调度，卡片按设备归属分配，读音／释义／填空三种卡型。
- 会后短测与会话复盘；短测结果只记录，不影响 FSRS 的正式安排。
- 词库与词条详情：同一个词跨作品的"相遇史"时间线。
- 中日同形词提醒（78 条种子表）与口语缩约还原，按词边界匹配。
- 可选的 AI 语境解释，兼容 OpenAI 接口，默认 DeepSeek；密钥存系统钥匙串。
- 导出到 Anki（AnkiConnect 或 .apkg）、JSON 导出、备份与恢复。
- 手机端 PWA：扫码连接，浏览与复习。
- 全局快捷键：默认 `Ctrl+Shift+S`，在游戏里直接收藏当前句（设置页可改键并查看监听状态）；
  未设置对话区域、macOS 缺少「辅助功能」授权等失败都会说明原因，不会静默失效。
- 采集：导入 mokuro 生成的 `.mokuro` 文件，把漫画按页收进一部作品；首版只收文字，
  卡片暂时没有漫画页截图。
- Windows 分发：`make package-windows` 构建 PyInstaller onedir 与 Inno Setup 安装包（含前端与分词词典），
  构建后自动冒烟（内置 OCR 实拍识别、分词、SPA）；签名脚本与证书说明见 `docs/CODE_SIGNING.md`（仓库暂无证书，签名未实测）。
- 采集：导入 EPUB 轻小说，按 spine 顺序切成句子收进作品；振假名单独保留不混进正文，
  10 万字级长篇按批入库（实测 3441 句 / 3.8 秒，峰值内存 2.2 MiB 不随书增长）。
- 采集：媒体缓冲（默认最近 60 秒、按内存上限 200MB，纯内存不落盘）。事后可用
  `POST /api/lines/{id}/backfill` 给已经过去的台词补上截图；对不上的时间点报 `buffer_miss`，
  容差由设置 `backfill_tolerance_s`（默认 5 秒）控制，音频接口预留、声源尚未接入。
- 学习：汉字进度网格。导入 KANJIDIC2（EDRDG，CC BY-SA 4.0，运行时从 EDRDG 下载、不随仓库分发）
  后，常用汉字按掌握度用墨色深浅排布，点字列出含它的词；作品页可看超出常用汉字表的字及出现次数。
- Classical 设计语言：纸墨金三层、墨色编码学习状态、中日双字体、明暗两套主题。

### Notes

- Windows 11 实机已验证：内置 OCR（需日语语言包）、屏幕抓取与剪贴板读取；
  完整采集流程与 Windows 安装步骤尚未逐一走查。
- 手机端复习需要桌面端在线（同一局域网）；离线复习计划在 M3。

[Unreleased]: https://github.com/ColinHouse/kotoba-studio/commits/main
