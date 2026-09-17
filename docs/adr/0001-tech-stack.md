# ADR 0001：技术栈选择 —— Vue 3 (TS) + FastAPI + SQLite

日期：2026-09-15 · 状态：已采纳

## 背景

Kotobako 需要同时具备：屏幕截取与 OCR（Windows / macOS）、日语分词与词典、FSRS 复习调度、Anki 导出、局域网内的手机 PWA，以及本地数据的备份与迁移。用户提议 Vue 3 (TS) + FastAPI + SQLite，并询问 Node.js / Ruby / Java Spring Boot 是否更合适。

## 决策

保留 **Vue 3 (TypeScript) + FastAPI (Python 3.12) + SQLite（SQLAlchemy 2 + Alembic）**，前端由 FastAPI 静态托管，单端口对局域网提供服务。

## 理由

| 需求 | Python 生态 | Node | Java / Ruby |
|---|---|---|---|
| macOS OCR | `pyobjc-framework-Vision`（本机验证 0.9 s，带坐标） | 需自写原生桥 | 需 JNI/FFI |
| Windows OCR | `winocr`（Windows.Media.Ocr）、`oneocr` | 需原生模块 | 需 JNI |
| 跨平台 OCR | `rapidocr`（onnxruntime，PP-OCRv5 含日语） | 无同等成熟包 | 无 |
| 分词/读音 | `fugashi` + unidic-lite（17 ms/句，含词元与读音） | kuromoji.js（IPADIC，读音较弱） | Kuromoji（Java，可用） |
| 语音活动检测 | `silero-vad` | 需 onnxruntime-node 手工接 | 无 |
| FSRS | `py-fsrs`（官方） | `ts-fsrs`（官方） | 无官方实现 |
| Anki 导出 | `genanki` + AnkiConnect | 需自写 .apkg 生成 | 无 |
| 桌面壳 | `pywebview`（单工具链）| Electron/Tauri（成熟） | jpackage（重） |

Node 后端在 Web/API 层完全可行，但 OCR、VAD、分词都要回到 Python，等于两套运行时；Java/Ruby 缺少 OCR 与 FSRS 生态。Python 后端把所有"脏活"放在一个进程里。

## 结果

- `server/`：FastAPI + SQLAlchemy 2 + Alembic（首日即有迁移），py-fsrs，fugashi，mss，OCR 提供者抽象（Vision / WinOCR / RapidOCR / manual）。
- `web/`：Vue 3.5 + Vite 8 + Tailwind 4 + vite-plugin-pwa；由后端托管 `web/dist`。
- 调度只在服务端；手机端 v1 在线复习。离线复习（M3）再引入 ts-fsrs 与同步协议。
- 桌面壳延后到 M2：pywebview + pystray；如需更精细的覆盖层再评估 Tauri sidecar。

## 已知代价

- Python 打包体积与冷启动比 Tauri 差；用 PyInstaller，onnxruntime 是主要体积来源。
- macOS 截屏与全局快捷键都需要系统权限，未授权时只能得到壁纸；分发需签名的 .app。
