# 架构

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
docs/          开发约定、ADR、路线图、这个文档站
```

## 数据模型

作品 → 会话 → 句子（截图/音频）→ 语境（某句里的某个词）→ 词条/义项 →
卡片（FSRS 状态 + 设备归属）→ 复习记录（正式 / 短测分开）。

「语境」是这条链上最关键的一环：它把「某个词」和「你在哪句话里遇到它」绑在一起，
所以一张卡永远知道自己是从哪来的。模型定义见
[backend/kotoba/models/](https://github.com/ColinHouse/kotobako/tree/main/backend/kotoba/models)。

## 技术栈

FastAPI · SQLAlchemy 2 + Alembic · py-fsrs · fugashi/unidic · mss ·
Apple Vision / Windows OCR / RapidOCR · Vue 3 + Vite + Tailwind 4 + PWA。

选型理由见 [ADR 0001](/adr/0001-tech-stack)。

## 改代码

```bash
make dev      # 后端（自动重载）+ Vite（5174，代理 /api /media /ws）
make check    # 提交前必须通过，CI 跑的就是这个
```

代码约定见[这里](/conventions)，给 AI 工具的操作规则见
[AGENTS.md](https://github.com/ColinHouse/kotobako/blob/main/AGENTS.md)，
人看的入口是 [CONTRIBUTING.md](https://github.com/ColinHouse/kotobako/blob/main/CONTRIBUTING.md)。

## 打包

```bash
make package-windows ARGS="--installer"
```

PyInstaller onedir + Inno Setup。构建后会自动冒烟：真实跑一次内置 OCR 识别与分词，
再检查 SPA 与健康检查。体积、耗时与签名做法见
[packaging/README.md](https://github.com/ColinHouse/kotobako/blob/main/packaging/README.md)
与[代码签名](/CODE_SIGNING)。
