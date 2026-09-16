# 代码签名

分发安装包前签名解决两件事：Windows 的 SmartScreen / 杀软拦截，macOS 的 Gatekeeper。
**本文只描述做法；本仓库目前没有证书，Windows 签名脚本未在真机实测过**，macOS 打包与公证也尚未实现，
不要把这里的命令当成已验证的流程。

## 绝对不能做的事

- **证书、PFX、密码、App 专用密码一律不进仓库**。`.githooks/pre-commit` 会拦截私钥与常见令牌；
  签名材料放在 OS 证书存储、CI secret 或本机临时文件里。
- 不要把密码写进命令行参数或日志。`packaging/build.py` 的 PFX 密码只从环境变量
  `KOTOBA_PFX_PASSWORD` 读取，且打印命令时会打码。

## Windows

### 证书从哪来

- 传统 OV / EV 代码签名证书：DigiCert、Sectigo、SSL.com 等，需要企业或个人实名认证，
  期限 1–3 年。EV 证书签发即有一定 SmartScreen 信任。
- 云签名服务（无需自己保管私钥）：Azure Trusted Signing、SSL.com eSigner 等，适合 CI。
- 自签名证书**只用于本机测试**，别人打开仍会报警，不要拿去分发。

### 使用本仓库的构建脚本

```powershell
# 证书已在当前用户证书存储：给 SHA1 指纹
make package-windows ARGS="--installer --sign-thumbprint <SHA1>"

# 或者用 PFX；密码通过环境变量提供，不要出现在命令里
$env:KOTOBA_PFX_PASSWORD = Read-Host -AsSecureString | ConvertFrom-SecureString -AsPlainText
make package-windows ARGS="--installer --sign-pfx C:\keys\kotoba.pfx"
```

脚本会按「先签 exe → 再打安装包 → 再签安装包」的顺序调用 `signtool.exe`
（自动从 PATH 或 Windows SDK 里找），时间戳用 DigiCert 的 RFC3161 服务，
摘要算法 SHA-256。`signtool` 本身随 Windows SDK 安装。

### 手动验证签名

```powershell
signtool verify /pa /v "dist\KotobaStudio-0.1.0-setup.exe"
Get-AuthenticodeSignature "dist\KotobaStudio\KotobaStudio.exe" | Format-List Status,SignerCertificate
```

### CI 里怎么放证书

在仓库 Secrets 里存两样：PFX 的 base64（`KOTOBA_PFX_BASE64`）与密码（`KOTOBA_PFX_PASSWORD`）。
构建步骤临时解码到 runner 的临时目录，签完立即删除；不要 `echo` 任何一样。
证书过期提醒要人为设置——签名过期不会让已签文件失效，但新构建会失败。

### 已知限制

- 新证书的 SmartScreen 声誉需要时间积累，前几个下载可能仍提示「未知发布者」；
  这是证书新旧问题，不是签名失败。
- 云签名（Azure Trusted Signing 等）的 `signtool` 参数不同（`/dlib` + `/dmdf`），
  本脚本目前只覆盖证书存储与 PFX 两种。

## macOS（未实现）

方向（参考 localsend 的发布流程）：Developer ID Application 证书
`codesign --force --deep --options runtime --timestamp --sign "Developer ID Application: …" app`，
再用 `xcrun notarytool submit --apple-id … --team-id … --password …` 公证，最后
`xcrun stapler staple` 装订票据。CI secret 需要 p12 证书与 App 专用密码。
本仓库还没有 macOS 打包脚本，`.app` 与公证都不在已实现范围内。

## 验证状态

| 项 | 状态 |
| --- | --- |
| Windows 安装包构建与安装/卸载 | 真机实测通过（未签名） |
| `--sign-thumbprint` / `--sign-pfx` 路径 | 已实现，**没有证书，未实测** |
| `signtool verify` 验证步骤 | 未实测 |
| macOS `.app` / 公证 | 未实现 |
