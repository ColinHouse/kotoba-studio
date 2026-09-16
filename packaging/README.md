# 打包（Windows）

把后端、前端 `dist/` 与分词词典装进一个双击可用的目录，并可选地打出 Inno Setup 安装包。

```bash
make package-windows                    # 便携 onedir（dist/KotobaStudio）
make package-windows ARGS="--installer" # 再打 Inno Setup 安装包
make package-windows ARGS="--no-smoke"  # 跳过构建后的冒烟测试
```

`packaging/build.py` 依次做四件事：

1. `npm run build` 构建前端（`--skip-frontend` 可跳过）。
2. `PyInstaller kotoba.spec` 产出 `dist/KotobaStudio/KotobaStudio.exe` 与 `_internal/`。
3. **冒烟测试**：用临时数据目录启动打包好的 exe，断言健康检查、SPA 首页、Windows OCR 可用性与
   **一次真实 OCR 往返**（`今日は俺が奢ってやるよ。` 渲染成图再识别）、分词（fugashi + unidic-lite）
   都正常；任何一项失败都会让构建失败。这是这套脚本存在的理由——PyInstaller 坏掉的通常正是这几处。
4. 可选签名（先签 exe 再打安装包再签安装包，见 [docs/CODE_SIGNING.md](../docs/CODE_SIGNING.md)）
   与可选 Inno Setup 打包。

## 布局

| 文件 | 作用 |
| --- | --- |
| `entrypoint.py` | 冻结入口：无参数等同 `serve`，参数照常传给 CLI |
| `kotoba.spec` | PyInstaller 配置：前端、`kotoba/data`、Alembic 脚本、unidic 词典、WinRT/winocr、pynput 后端 |
| `build.py` | 编排构建、冒烟、签名与安装包 |
| `installer.iss` | Inno Setup 脚本（必须保持 UTF-8 **带 BOM**，否则中文会乱码） |

## 实测数字（Windows 11，2026-09）

| 项 | 值 |
| --- | --- |
| onedir 体积 | 321.8 MB（其中 unidic-lite 词典约 260 MB） |
| 安装包体积 | 56.1 MB（lzma2 压缩） |
| 安装耗时 / 安装后体积 | 约 7 秒 / 326.4 MB（用户目录安装，无需管理员） |
| 首次启动到 `/api/health` 就绪 | 1.6–2.9 秒（本机 SSD） |
| 卸载 | 静默卸载后无残留文件与开始菜单项 |

体积的大头是分词词典，不是应用代码。`kotoba.spec` 显式排除了 `torch`（FSRS 优化器）与
`rapidocr/onnxruntime`（可选 OCR 后端）：优化器单独安装 `--extra optimizer`，ONNX OCR 单独安装
`--extra ocr-onnx`，都不应该进默认包。

## 依赖

- 构建需要 `--extra packaging`（PyInstaller）；`make package-windows` 已带。
- 安装包需要 Inno Setup 6（`winget install JRSoftware.InnoSetup`，会装到用户目录）。
- 安装向导：Inno Setup 官方不带简体中文语言文件。把 `ChineseSimplified.isl` 放进 Inno 的
  `Languages` 目录后，`installer.iss` 会自动启用中文；否则向导按钮是英文，自定义文案仍是中文。
- 签名需要证书与 Windows SDK 的 `signtool.exe`，见 [docs/CODE_SIGNING.md](../docs/CODE_SIGNING.md)。
- macOS 的 `.app` 与公证不在本目录范围，尚未实现（见 issue #61）。
