# 平台说明

## macOS

截屏需要在「系统设置 → 隐私与安全性 → 屏幕录制」中授权启动服务器的终端或应用；
**未授权时只会截到壁纸**——这是最常见的「功能好像坏了」。

全局快捷键还需要同一处的「辅助功能」授权，未授权时设置页会给出提示。

## Windows

内置 OCR 需要日语语言包：

```powershell
Add-WindowsCapability -Online -Name Language.OCR~~~ja-JP~0.0.1.0
```

该路径已在 Windows 11 真机验证；没有语言包时自动回退到 RapidOCR（安装 `--extra ocr-onnx`）。
全局快捷键（默认 `Ctrl+Shift+S`，设置页可改）也已在 Windows 11 真机验证。

### 游戏内覆盖层

Windows 下窗口化 / 无边框窗口可用（**独占全屏显示不出来**），默认 `Ctrl+Shift+O` 呼出或隐藏。
面板显示当前句分词，点词看释义、可直接收藏。

## 行尾

仓库用 `.gitattributes` 在所有平台检出 LF。早于该文件的旧检出如果 `format:check` 全红，
在无未提交改动时运行 `git read-tree --reset -u HEAD` 重新检出即可，不必重新 clone。
