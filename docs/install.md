# 安装

## Windows

到 [Releases](https://github.com/ColinHouse/kotoba-studio/releases) 下载安装包，双击安装即可，
**不需要装 Python 或 Node**。

安装包**没有签名**，Windows 会弹 SmartScreen 警告，点「更多信息 → 仍要运行」。
为什么没签名、以后打算怎么签，见[代码签名](/CODE_SIGNING)。

## macOS / Linux

还没有安装包，只能从源码运行。macOS 的 `.app` 与签名进度见
[#61](https://github.com/ColinHouse/kotoba-studio/issues/61)。

## 从源码运行

### 一次性准备

**macOS**

```bash
brew install uv node        # Python 由 uv 自己装，Node 需要 22 以上
```

**Windows**（用 PowerShell 装，装完之后所有命令都在 Git Bash 里跑）

```powershell
winget install --id=astral-sh.uv -e
winget install --id=OpenJS.NodeJS.LTS -e
winget install --id=Git.Git -e
winget install --id=ezwinports.make -e
```

Windows 上 `make` **必须在 Git Bash 里运行**。PowerShell 与 CMD 会让 make 回退到 cmd.exe，
Unix 风格的 recipe 会失败。

### 跑起来

```bash
git clone https://github.com/ColinHouse/kotoba-studio.git
cd kotoba-studio
make setup     # 装两端依赖并启用 git hooks
make run       # 构建前端，在 8720 端口同时提供 API 与网页
```

浏览器打开 <http://127.0.0.1:8720>。`make help` 看全部命令。

## 配置

改数据目录、端口或接 DeepSeek：`cp .env.example .env`，里面列了全部环境变量。

**AI 密钥更推荐在 设置 → AI 解释 里填**——那样会存进系统钥匙串，而不是磁盘上的明文文件。
不填密钥也能用，AI 解释是可选的。
