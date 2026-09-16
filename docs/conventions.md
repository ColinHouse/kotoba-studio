# 开发约定 · Conventions

给人和给 AI 工具看的同一份约定。硬性的提交约束在 [`AGENTS.md`](../AGENTS.md)，这里是写代码时的
具体做法。

## 通用

- **文件保持聚焦。** 超过约 300 行通常说明它做了不止一件事。后端目前最大的手写文件是 186 行。
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
