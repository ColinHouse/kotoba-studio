---
layout: home
hero:
  name: Kotobako
  text: 好き、以外の言葉で。
  tagline: 会记住语境的日语伴读工具。玩 Galgame、看动画、读漫画和轻小说时，用很低的打断成本收藏台词——原句、截图、原声一起存下来，自动整理成词卡，用 FSRS 复习。数据在你自己的机器上。
  image:
    src: /mascot.png
    alt: Kotobako
  actions:
    - theme: brand
      text: 下载 Windows 安装包
      link: https://github.com/ColinHouse/kotobako/releases/latest
    - theme: alt
      text: 头三件事
      link: /guide
    - theme: alt
      text: GitHub
      link: https://github.com/ColinHouse/kotobako

features:
  - title: 看得懂汉字却读不出
    details: 含汉字的词默认生成「看汉字写读音」卡，专治中文母语者最容易糊弄过去的那一类。
  - title: 中日同形词会提醒
    details: 勉強・大丈夫・手紙・怪我… 命中时卡片自动标出来，不让你把中文意思带进去。
  - title: 口语缩约能还原
    details: ちゃう ← てしまう、なきゃ ← なければ，按词边界识别并标注，不是字符串替换。
  - title: 收藏之后真的会复习
    details: 会后三分钟短测 + FSRS 到期复习 + 手机扫码即用的 PWA，桌面采集、手机复习。
  - title: 数据不锁在别人手里
    details: SQLite 加一个媒体目录，一键备份/恢复，可导出 JSON、.apkg 或直接推给 AnkiConnect。
  - title: 本地优先
    details: OCR 和分词都在本机跑。不填 AI 密钥完全可用；填了，才会有台词发给第三方。
---

::: warning 当前是 `v0.1.0-beta.1`
核心流程可以每天用，但**只有 Windows 安装包**，也只有作者一个人完整走过一遍。
macOS 与 Linux 目前只能[从源码运行](/install#从源码运行)。
请先用设置页的备份功能导出一份，再开始积累学习数据。
完整的[已知限制](https://github.com/ColinHouse/kotobako/blob/main/CHANGELOG.md)写在 CHANGELOG 里。
:::
