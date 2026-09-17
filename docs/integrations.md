# Hook 与导入导出

这一页写的是 Kotoba Studio **对外的契约**——别的程序怎么把文本送进来、怎么把学习数据拿出去。

内部那 90 多个 REST 端点不在这里：它们是应用自己前后端之间的接口，两半永远一起发布，
不承诺稳定。真要看，本机跑起来之后 <http://127.0.0.1:8720/docs> 有一份永远最新的 Swagger。

## Hook 协议

文本钩子工具（Textractor / Agent / LunaTranslator 等）连到：

```
ws://127.0.0.1:8720/ws/hook
```

每条消息是**一整行台词**。两种格式都收：

```
こんにちは、元気？
```

```json
{ "text": "こんにちは、元気？", "speaker": "佐藤", "session_id": 12 }
```

`speaker` 和 `session_id` 可省略；省略时归入当前进行中的会话。

服务端对每条消息回一个 JSON。**失败是显式的**，不会静默丢弃：

| 回包 | 含义 |
| --- | --- |
| `{"ok": true, ...}` | 已入库 |
| `{"ok": false, "error": "empty"}` | 文本是空的或只有空白 |
| `{"ok": false, "error": "paused"}` | 采集被暂停，或正在做词典导入这类长写入 |

收到 `paused` 就等一会儿再发——那一行**没有**被存下来。

## 把文本导入一部作品

不靠截图也能建立语料。三种格式各有一个端点，都是往某一部作品里灌：

| 格式 | 端点 | 说明 |
| --- | --- | --- |
| 字幕 | `POST /api/sources/{id}/subtitles` | `.srt` / `.ass` |
| 轻小说 | `POST /api/sources/{id}/epub` | 按 EPUB spine 顺序切成章节与句子 |
| 漫画 | `POST /api/sources/{id}/mokuro` | [mokuro](https://github.com/kha-white/mokuro) 的 `.mokuro`，保留每块文字在页面上的位置 |

编码不用自己转：上传的文本文件按日语字幕和词表实际的编码习惯解码。

界面上的入口在 **作品 → 某部作品 → 导入**。

## 词典与已知词

| 用途 | 端点 |
| --- | --- |
| Yomitan 词典包（zip） | `POST /api/dictionary/yomitan/import` |
| JMdict / KANJIDIC2 / 音高重音 | `POST /api/dictionary/{jmdict,kanjidic,pitch}/install` |
| 已知词列表 | `POST /api/known/import` |

导入大词典期间会触发上面说的 `paused`——那是有意的，不是 bug。

## 导出

| 目标 | 端点 |
| --- | --- |
| AnkiConnect（Anki 开着就直接推过去） | `POST /api/export/anki-connect` |
| `.apkg` 文件 | `POST /api/export/apkg` |
| JSON 全量 | `GET /api/export/json` |

**Anki 只是可选出口。** 这个应用自己管着完整的 FSRS 状态与复习记录，不依赖 Anki 存在。

备份走另一条路（`设置 → 备份`），导出的是数据库加媒体目录，能原样恢复。
