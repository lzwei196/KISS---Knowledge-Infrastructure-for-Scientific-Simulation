# GeoForge Desktop 0.6.53 — Windows x64

推荐下载 `GeoForge-Desktop-Setup-v0.6.53-Windows-x64.exe`，直接运行安装。
安装器自带 Python 3.11 和必需的运行时 DLL，无需自行安装 Python。
便携版请完整解压 ZIP，不要将 EXE 从 `_internal` 文件夹旁单独移走。

本次更新：

- 全部 127 个 KI 都有 Windows 安装经验；23 个 KI 携带独立 Windows 配方。
  Agent 按当前系统读取，不覆盖 macOS 配方。
- 修复便携工具链与依赖查找、安装路径、超时进程及输出管道回收。
- FSM2 官方 Alptal 示例和 MARRMoT 真实 Octave 运行已通过；安装压测快照为
  91 installed / 35 needs-user / 1 failed（RAPID）。安装成功不等于科学校准完成。
- 保留稳定浏览器前端、托盘退出、Kimi 全电脑访问确认；KI 更新仍从 `main` 获取。

Windows 打包验证包括：应用及共享库回归测试、冻结程序从独立目录启动、127 个 KI
及平台经验/配方检查、9 个 HTTP 路由、harness/Flow/校准依赖加载、静默安装与卸载。
本轮发布验证不包含重新运行全部 DeepSeek 安装任务，也未覆盖每一种其他电脑配置。
详细证据见随包发布的 `Windows-release-validation.json`。

现有项目、API 设置和模型安装目录不需要迁移。本包不包含 AI 账号、密钥或全部科学模型二进制。
当前安装器未代码签名；Windows 可能显示未知发布者提示，请先核对下载来源与
`SHA256SUMS-Windows.txt` 校验和。

This Windows-only release ships a self-contained Python 3.11 installer and portable archive.
It does not replace the macOS/Linux release assets. Read `release-manifest.json` and
`DESKTOP_CHANGELOG.md` for the application baseline, Windows KI overlay, and update details.
