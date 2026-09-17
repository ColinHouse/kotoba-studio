# 开发约定 · Conventions

给人和给 AI 工具看的同一份约定。硬性的提交约束在 [`AGENTS.md`](https://github.com/ColinHouse/kotobako/blob/main/AGENTS.md)，这里是写代码时的
具体做法。

## 通用

- **文件保持聚焦——按"有几个理由会改它"来判断，不是按行数。** 300 行是个提醒，不是上限。
  真正该问的是：**这个模块有几个独立的原因会让人改它？** 一个 350 行的解析器可能非常内聚；
  一个 150 行、同时掺了 HTTP、数据库生命周期、平台 API、业务规则和后台线程归属的模块不是。
  平台适配器（`services/capture/windows.py`、`services/overlay.py`）和格式解析器
  （`services/text/epub.py`）天然会长，**只在它们有了多个改动理由时才按能力拆，不要为了行数拆。**
- **注释写"为什么"，不写"做了什么"。** 代码已经说明做了什么。值得写注释的是：这里为什么用了
  一个看起来奇怪的做法、哪个坑导致了这行代码。
- **界面文案用简体中文，标识符、注释、提交信息用英文。**
- **不要留下被注释掉的代码。** git 记得它。

## 后端（Python）

### 分层

```
api/       只做 HTTP 的事：解析请求、调用服务、组织响应。不写业务逻辑。
services/  业务逻辑。接收 Session，不接触 Request/Response。
models/    ORM。不写业务逻辑。
schemas/   DTO。`from_model()` 负责 ORM → DTO。
core/      基础设施。不 import services 或 api。
```

判断标准：**一个服务函数应该能在没有 FastAPI 的情况下被调用和测试。** 如果它需要 `Request`，
说明逻辑放错层了。

### 具体做法

- 事务边界在**路由**上，不在服务里。服务用 `db.flush()` 让后续查询看到写入，由路由 `db.commit()`。
  唯一的例外是后台任务（如词典导入），它自己拥有一个 session。
- 抛错用 `ApiError(code, message, status)`，`code` 是稳定的机器可读标识（`not_found`、
  `ocr_unavailable`），`message` 是给用户看的中文。前端靠 `code` 判断，靠 `message` 显示。
- 平台相关的 import 必须延迟到函数内部（见 AGENTS.md 不变量 7）。
- 时间一律 UTC aware。用 `models.utcnow()`，不要用 `datetime.now()`。
- 路径不要用 `Path(__file__).parents[n]` 这种脆弱写法，用 `core/resources.py` 里的常量——
  重构时前者会静默失效。
- **服务不要捕获 `app.state.db.session`。** `restore_backup()` 会整个换掉 `app.state.db`，
  被捕获的绑定方法之后会继续写已经退役的引擎。传 `lambda: app.state.db.session()`，
  每次调用重新取（`app.py` 里所有后台服务都这么做）。
- **分批 commit 的导入器必须能从中途失败恢复。** 词典/词频这类导入先把
  `entry_count` 写成 0，全部成功才置数：半截数据留在库里比失败更糟，用户没有任何办法发现。
  参考 `services/dictionary/yomitan/`。
- 用户自带数据的格式读取放在 `services/dictionary/yomitan/`（只支持格式，不分发内容）；
  文本编码嗅探集中在 `services/text/encoding.py`，导入路径不要各自 decode。

### 测试

- 用 `backend/tests/conftest.py` 的 fixture：`client`（TestClient，临时数据目录）、`db`
  （绑定到同一个库的 Session）、`jmdict_fixture`（导入内置的小词典）。
- **测行为，不测实现。** 断言 API 返回什么、数据库里留下什么，而不是某个内部函数被调用了几次。
- 外部服务用 `httpx.MockTransport` 注入，通过 `app.state.ai_transport` /
  `app.state.anki_transport`。不要打真实网络。
- 改 bug 先写一个会失败的测试。

## 前端（Vue 3 + TypeScript）

### 分工

```
views/        路由页面。编排，尽量少逻辑。
composables/  跨组件的数据流与状态（useScreenCapture、useInboxLines…）。
components/   展示与局部交互，按域分目录。
stores/       真正全局的状态（app、device），只有两个，不要随便加。
api/          客户端与类型。所有网络请求都从这里走。
```

判断标准：**如果一段逻辑需要在两个地方用，或者让组件超过了一屏，就抽成 composable。**

### 具体做法

- 一律 `<script setup lang="ts">`，`defineProps` 在 `defineEmits` 之前（eslint 会管）。
- **不用 `any`。** 后端返回的形状都在 `api/types/` 里有定义；缺了就补上。
- 每个表单控件都要有稳定的 `id` 和关联的 `label`——发布更新时平台会尝试保留表单状态。
- 颜色只用 `style.css` 里的 token（`--color-ink`、`--color-accent`…），不要写死颜色值，
  否则暗色主题会坏。
- 日语内容加 `.jp` class，让它用日文字体栈渲染。中日汉字字形不同，这不是细节。
- `localStorage` 的读写都要 try/catch——隐私模式下会抛异常。

### 测试

- 纯函数（`utils/`）必须有测试，这是目前 vitest 覆盖的部分。
- 组件测试目前没有铺开；加新的纯逻辑时优先把它放进 `utils/` 或 composable 里，这样能测。

## 依赖升级

Dependabot 每月按生态分组提 PR。**主版本升级不进分组**，会单独开 PR，必须手动验证——
分组规则只覆盖 minor 和 patch。

验证的方法是真的跑一遍，不是看 peer 范围：`@vue/tsconfig` 与 `vue-tsc` 的 peer 范围都允许
TypeScript 7，但 `vue-tsc` 依赖 TS 7 已经不再导出的 `typescript/lib/tsc`，`typescript-eslint`
更是直接拒绝在 TS 7.0 上运行。已知不能升的依赖写在 `.github/dependabot.yml` 的 `ignore` 里，
并注明原因和重新评估的条件。

## 数据库变更

```bash
make migrate m="add audio_path to lines"
```

然后**打开生成的 revision 检查**：autogenerate 会把自定义类型写成
`kotoba.models.UTCDateTime()`，需要手动换成 `sa.DateTime()`，否则迁移在干净环境里会报
`NameError`。这个坑已经踩过一次。

## 日语处理

改 `services/jp/` 之前先读现有测试，那里记录了几个反直觉的情况：

- 缩约还原按 token 边界匹配：`奢って` 里的 `って` 是 te 形，不是引用助词。
- 表达式合并要同时校验写法和读音：`今日` + `は` 不能合并成 `こんにちは`。
- 词头按原文用字选择：原文写汉字就用汉字词头，原文写假名且词典标注 `uk`（usually kana）
  就用假名词头。
- `unidic` 的 `lemma` 可能是旧字体（`奢る` 的 lemma 是 `驕る`），要用的是 `orthBase`。

## 可访问性基线（issue #76）

- **墨色对比度**：`frontend/src/utils/contrast.test.ts` 解析 `style.css` 的令牌并固定现状——
  亮色主题 `--ink-50`（3.55–4.13）与 `--ink-35`（2.38–2.77）在 bg / surface / paper 上都达不到
  WCAG AA 4.5:1；暗色主题只有 `--ink-35`（3.60–4.12）达不到；`--ink` 与 `--ink-70` 两套主题
  全部达标。改令牌会让这张表失败，逼你把改动写成明确决定（变好或变坏都要改表）。
  **不单方面推翻设计系统**：可选方案是（a）调整 ink-50 / ink-35 到 4.5:1，（b）给靠墨色深浅
  编码的状态加非颜色冗余（线型、图标、文字），（c）维持现状但限定这些档位只承载非必要信息。
  取舍在 issue #76 里定。
- **axe 棘轮**：`frontend/e2e/a11y.spec.ts` 对首页 / 收件箱 / 复习 / 词库跑 axe，把今天的违规
  种类钉成基线（`color-contrast`、`link-in-text-block`）；出现**新**种类就红，修掉一种也要回来
  改基线。它是棘轮，不是「无障碍通过」的证明。
- **键盘**：复习页可全程键盘走完（空格揭晓、1–4 评分），由 E2E 冒烟测试以纯键盘操作锁定；
  挖词主路径还不能（issue #93）。焦点可见性统一用全局 `:focus-visible` 金色描边，组件不要自造。
- **振假名与屏幕阅读器**：`奢[おご]る` 这类 ruby，主流屏幕阅读器会读成「奢 おごる」（base 后
  跟着 rt），读不出「这是注音」的语义。现状是视觉优先、没有加 `aria-label` 覆盖——这是**已知
  限制**，不要假装没问题；要为读屏用户提供替代信息时另开 issue。
