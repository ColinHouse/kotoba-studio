# Changelog

All notable changes to this project are documented here, newest first.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- 采集：框选屏幕区域，OCR 识别台词，连同截图收进收件箱；支持 Apple Vision、Windows OCR、
  RapidOCR 与手动粘贴，Hook 工具可通过 `ws://<host>:8720/ws/hook` 送入文本。
- 收件箱：分词后逐词确认，词典候选来自 JMdict，可填写"这里的意思"并选择要建的卡片类型。
- 复习：内置 FSRS 调度，卡片按设备归属分配，读音／释义／填空三种卡型。
- 会后短测与会话复盘；短测结果只记录，不影响 FSRS 的正式安排。
- 词库与词条详情：同一个词跨作品的"相遇史"时间线。
- 中日同形词提醒（78 条种子表）与口语缩约还原，按词边界匹配。
- 可选的 AI 语境解释，兼容 OpenAI 接口，默认 DeepSeek；密钥存系统钥匙串。
- 导出到 Anki（AnkiConnect 或 .apkg）、JSON 导出、备份与恢复。
- 手机端 PWA：扫码连接，浏览与复习。
- Classical 设计语言：纸墨金三层、墨色编码学习状态、中日双字体、明暗两套主题。

### Notes

- 未在 Windows 真机上验证内置 OCR 路径。
- 手机端复习需要桌面端在线（同一局域网）；离线复习计划在 M3。

[Unreleased]: https://github.com/ColinHouse/kotoba-studio/commits/main
