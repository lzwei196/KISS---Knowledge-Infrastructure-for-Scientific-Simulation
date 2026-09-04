# GeoForge Desktop changelog / 桌面版更新日志

This is the human-readable companion to [`release-manifest.json`](release-manifest.json).
Desktop update agents should read the JSON manifest first and use this file to explain the update.

这是 `release-manifest.json` 的用户版说明。Windows、macOS 和 Linux 的更新 Agent
应先读取 JSON，再用本文件向用户解释更新内容。

## v0.6.52 — 2026-09-03

### 中文

- 修复干净 Linux/Windows 环境没有安装 GeoPandas 时，可选地理空间能力名称未初始化，
  导致发布测试无法注入替身的问题。运行时仍由显式能力标志控制，不会假装依赖可用。
- 延续 v0.6.51 的失败关闭发布闸门和 v0.6.50 的完整 Desktop 功能集。

### English

- Define optional geospatial dependency handles consistently when GeoPandas is absent, allowing
  clean Linux/Windows environments to probe and test the capability without pretending it is
  installed.
- Retains v0.6.51's fail-closed release gate and the complete v0.6.50 Desktop feature set.

## v0.6.51 — 2026-09-03

### 中文

- **完整重发 v0.6.50 的功能**：首次 `v0.6.50` CI 因两项依赖开发机环境的测试而停止，
  但旧发布脚本仍错误地公开了一个只有 KI 包、没有 Desktop App 的不完整 Release。
- **发布闸门已修复**：只有 macOS Apple Silicon、Windows x86_64 和 Linux x86_64
  三个平台均构建、冻结运行检查并上传成功，GitHub 才能公开 Release；精确文件检查不再
  使用会把不存在文件误判为存在的 Bash 数组长度。
- **测试可跨机器复现**：Kimi 路径权限测试不再依赖开发机的安全模式或用户主目录。

除上述发布工程修复外，Desktop 功能与下面完整记录的 v0.6.50 相同。

### English

- **Complete reissue of the v0.6.50 feature set:** the first v0.6.50 CI run stopped on two
  tests that accidentally depended on the developer machine, while the old release job still
  published an incomplete metadata/KI-only release with no Desktop application.
- **Fail-closed release gate:** a public release now requires successful builds, frozen-runtime
  smoke tests and uploaded Desktop archives for macOS Apple Silicon, Windows x86_64 and Linux
  x86_64. Exact file checks replace the Bash-array test that misclassified a missing file.
- **Host-independent tests:** Kimi path-permission tests no longer depend on a developer's security
  setting or home-directory layout.

Desktop behavior is otherwise the v0.6.50 feature set documented in full below.

## v0.6.50 — 2026-09-03

### 中文

- **KI harness 从提示词升级为执行闸门**：Desktop 现在正式执行“理解任务 → 盘点数据 →
  生成计划 → 用户批准 → 下载/运行 → 证据验证”。批准前 Agent 只能读取、查询和规划；
  模型工具、下载和结果声明必须对应已批准的步骤与可检查的运行凭据。
- **冻结版完整性修复**：harness 及 Flow 的 9 个运行模块都作为 Python 模块打包。
  启动检查和跨平台 CI 会验证真实合同、工具信任模块及数据构建模块均来自当前 App，
  不再悄悄退回四行弱化提示。
- **内部 intake 标记不再显示**：`GEOFORGE_INTAKE` JSON 仍用于可靠地传递研究区、
  时段、过程、输出和缺失数据，但 Desktop 会在展示消息前将其消费并移除。
- **本地服务安全加固**：所有写操作要求本次 App 随机生成的 SameSite token 与本地同源
  请求；恶意网页不能再跨站请求 localhost 来创建会话或修改设置。
- **设置并发保存修复**：API key、代理和服务商设置改用加锁、原子替换及仅用户可读写权限，
  避免同时保存时丢失字段或产生损坏 JSON。
- **科学数据空间选择修复**：NetCDF 工具支持降序坐标、0–360 经度及跨日期变更线范围；
  流域矢量会按 CRS 转换到经纬度。曲线网格、空选择、全缺测结果会明确失败，避免返回
  看似正常但实际错误的数据。
- **可移植安装修复随 KI 发布**：CRHM、Alpine3D 与 WRF-Hydro 的已有安装路径、编译产物
  和预检位置保持一致，不再依赖作者机器上的绝对目录。
- **发布过程统一**：macOS、Windows、Linux 均由已纳入版本控制的 spec 构建；release
  同时包含源码、更新清单、更新日志、校验和与完整 KI 安装包。

本地验证：Desktop/Flow **311 通过、3 跳过**；KI 工具 **98 通过、2 跳过**；
气候与单位 **83 通过**；诊断框架 **46 通过**。真实本地接口回归中，同源写入返回 200，
跨域写入返回 403。最终冻结 App 与 GitHub 跨平台构建结果记录在 release 中。

### English

- **The KI harness is now an execution gate:** Desktop enforces task intake, data inventory,
  planning, explicit user approval, execution and evidence verification. Before approval, the Agent
  can inspect and plan but cannot download data or run model tools. Runs are bound to approved steps
  and produce checkable receipts.
- **Frozen-runtime integrity:** the harness and all nine Flow runtime modules are collected as Python
  modules. Startup and cross-platform CI prove that the full contract, tool-trust module and data
  builder load from the current app; a packaged build cannot silently fall back to weaker guidance.
- **Internal intake metadata stays internal:** GeoForge still consumes the structured
  `GEOFORGE_INTAKE` record for deterministic model selection and readiness, but removes it from the
  message shown to the user.
- **Local-service hardening:** every state-changing request requires a random process-local SameSite
  token and matching loopback origin, blocking cross-site pages from writing to GeoForge's localhost API.
- **Atomic settings:** API keys, provider and proxy settings use a locked transaction, restrictive
  permissions and atomic replacement so concurrent saves cannot lose fields or leave malformed JSON.
- **Scientific spatial correctness:** NetCDF helpers now handle descending coordinates, 0–360
  longitudes and antimeridian windows; basin vectors are reprojected from their declared CRS. Curvilinear
  grids, empty selections and all-missing means fail explicitly instead of returning plausible bad data.
- **Portable KI installation repairs:** CRHM, Alpine3D and WRF-Hydro use the selected existing-install
  location consistently across setup, compilation and preflight.
- **One release build contract:** macOS, Windows and Linux builds use version-controlled specs, and the
  release carries source history, a machine-readable manifest, human changelog, checksums and the full
  KI installation pack.

Local validation: **311 passed / 3 skipped** Desktop and Flow tests; **98 passed / 2 skipped** KI-tool
tests; **83 passed** climate/unit tests; and **46 passed** diagnostic checks. A live localhost regression
returned HTTP 200 for a token-bearing same-origin write and HTTP 403 for a simulated cross-origin write.
The final frozen-app and GitHub cross-platform results are recorded with the release.

## v0.6.49 — 2026-08-28

### 中文

- **Auto-KI 任务理解成为独立入口阶段**：未预选 KI 时，自然语言科研目标先交给 Agent 完整理解，再由 Desktop
  校验结构化的研究区、时段、物理过程、输出、关键缺口和候选 KI；不会再由正则先把整句话
  当成模型名，也不会仅凭选择了 KI 就跳进规划。API 与 Claude、Codex、Kimi CLI 使用同一
  intake 合同，缺口未清空时不能开始规划、下载或运行。
- **新增分层 KI 观测台**：从聊天主页或 KI 库进入，先查看 14 个科学领域，再进入
  领域查看 KI；点击 KI 后直接进入它的内部科学流程。跨 KI 关系降为可选辅助视图，
  默认不绘制关系线。图谱采用 KISS 论文
  `arXiv:2605.17856` 的 14 个地球科学领域框架，并明确区分论文的 119 个 KI
  基线与本地后来新增的 KI。
- **关系有实际依据且可筛选**：跨 KI 连线来自各自 `dag.yaml` 声明的输入和输出语义，
  可以分别查看科学耦合、共享数据或全部证据；不会用名称相似度伪造科学关系。
- **动态 KI 科学生产线**：数据入口、核心处理引擎、验证闸门和结果出口组成一条持续流动的
  主线；数据包沿连线移动，处理站依次点亮。长说明、可选模块和技术辅助节点默认折叠到
  “完整技术 DAG”，每个节点仍可单独查看并询问聊天 Agent。
- **科学叙事取代源码清单**：观测台默认把 DAG 投影为“汇集研究信息、构建模型对象、
  推演系统、连接组件、可信检查、形成结果”等科学阶段。程序模块名、变量名和文件位置
  只在每个阶段的“技术依据”或“完整技术 DAG”中显示。
- **Agent 状态具有证据等级**：聊天现在分别显示子进程、工具事件、项目阶段和项目文件变化。
  只有检测到下载工具或输入文件增长时才会显示“数据传输”；仅有进程心跳而长时间没有事件时，
  会明确提示“当前动作未确认/可能卡住”，并提供重新检查和新建对话按钮。Kimi Code 与
  Claude Code 的结构化工具事件还会显示经过脱敏的具体命令、脚本或文件路径，不再只写 `Bash`。
- **“询问 Agent”自动使用新对话**：从 KI、科学阶段或技术节点提问时，观测台会创建一个
  绑定当前 KI 的全新项目会话、跳转到聊天页并自动发送问题；不会再复用任意旧对话。
- **实时项目观察**：从观测台选择一个聊天项目，可查看当前 Agent、KI、准备、验证、运行、
  等待用户和结果状态。界面只读取桌面端已经记录的事件，不运行或导入 KI 代码。
- **通用与专用展示分层**：所有 KI 都有从 DAG 自动生成的通用视图；声明
  `visualization_contract.yaml` 的 KI 可继续加载地图、动画、三维模型、剖面或仪表盘。
- **中英文完整适配**：观测台跟随 GeoForge 语言设置，中文会话不再出现半中文半英文的导航。

验证结果：GeoForge 正式测试 **179/179 通过**；127 个本地 KI 均成功生成动态流程数据，
JavaScript 语法检查、冻结 App 启动检查与 macOS 签名验证通过。

### English

- **Task understanding is now a separate Auto-KI entry phase:** when no KI is preselected, a natural-language scientific goal reaches
  the Agent intact before the Desktop validates a structured study area, period, process, outputs,
  material gaps, and proposed KIs. Choosing a KI alone cannot start planning. Direct APIs and the
  Claude, Codex, and Kimi CLIs share the same read-only intake contract; unresolved gaps block
  planning, downloads, and execution.
- **Hierarchical KI Observatory:** open it from Chat or the KI Library, begin with 14 scientific
  domains, enter one domain to see its KIs, then open a KI directly into its internal scientific
  workflow. Cross-KI relationships are now an optional secondary view and are hidden by default.
  Its 14-domain frame follows the KISS KI paper
  (`arXiv:2605.17856`) while distinguishing the paper's 119-KI baseline from newer local packages.
- **Evidence-backed relationship filters:** links come from input and output semantics declared in
  each `dag.yaml`; users can switch between scientific coupling, shared data, and all evidence.
- **Animated scientific production line:** data intake, core processing engine, verification gate,
  and result outlet form one flowing story. Packets move along the line and processing stations light
  in sequence. Long descriptions and technical helpers remain in **Full technical DAG**.
- **Scientific narrative instead of a source listing:** the default view projects DAG semantics into
  human stages such as gathering evidence, building the model world, evolving the system, connecting
  components, passing a trust gate, and making results usable. Exact identifiers stay under
  **Technical evidence** and **Full technical DAG**.
- **Evidence-graded Agent state:** Chat separates process life, tool events, project reports, and
  project-file changes. It claims a data transfer only when a download tool or growing input is
  observed; a quiet heartbeat is shown as unconfirmed work and may be flagged as stalled. Structured
  Kimi Code and Claude Code tool events also show a redacted command, script, or path summary instead
  of the generic word `Bash`.
- **Ask Agent always starts a new chat:** asking about a KI, scientific phase, or technical node now
  creates a fresh project chat pinned to that KI, navigates to it, and sends the question automatically.
  No existing conversation is reused.
- **Live project observation:** selecting a chat project shows recorded Agent, KI, preparation,
  validation, execution, user-wait, and result state. The Observatory never imports or executes KI code.
- **Generic plus specialized rendering:** every KI receives a safe DAG-derived view; KIs with a
  `visualization_contract.yaml` may add maps, animation, 3D models, sections, or dashboards.
- **Bilingual behavior:** the Observatory follows the shared GeoForge language preference.

Validation: **179/179 GeoForge tests passed**. All 127 local KIs produced valid animated-flow
data; JavaScript syntax, frozen-app startup, and macOS bundle signing checks passed.

## v0.6.48 — 2026-08-27

### 中文

- **验证已经安装的软件**：Agent 设置页新增“使用已经安装的软件”。用户可以选择安装
  文件夹或可执行文件，也可以让 Agent 在系统标准位置与索引中查找。外部安装只允许
  读取和运行；链接、配置、日志和验证记录仍写入 GeoForge 自己的模型工作区。
- **DeepSeek API 路径规则补全**：用户明确选择的已有安装路径会作为受控的只读/可执行
  路径交给 API Agent，同时继续禁止它写入项目以外的个人文件。
- **验证徽章即时刷新**：聊天中的 Agent 修好模型并通过预检后，页面会立即重新读取机器
  状态，不再出现回复已经说“通过”、顶部仍显示红色“验证失败”的情况。
- **WRF-Hydro 安装路径修复**：兼容当前 CMake 的旧项目策略，并把完整 `Run` 目录放到
  KI 预检和运行工具共同使用的位置，避免二进制已经编译却被报告为找不到。

### English

- **Verify software already installed:** Agent setup can use a selected installation folder or
  executable, or search standard indexed locations. External software is read/executed only;
  GeoForge keeps links, configuration, logs, and verification evidence in its own workspace.
- **DeepSeek API path contract:** explicitly approved existing installations are available to the
  restricted API tool runner without opening unrelated personal files for writing.
- **Immediate verification refresh:** a successful repair and preflight now refreshes the chat
  header, removing stale red failure badges.
- **WRF-Hydro path repair:** current CMake policy handling and a shared complete `Run` directory
  prevent a successfully compiled executable from being mistaken for a missing installation.

## v0.6.47 — 2026-08-27

### 中文

- **Windows 可以在 App 内启用 Kimi Code**：AI 设置会明确显示“禁用 Kimi（安全）”和
  “允许完整电脑访问并启用 Kimi”。选择完整访问时必须确认风险；Windows 不再把尚未
  支持的项目范围 Kimi 沙箱标为可用的推荐项。

### English

- **Kimi Code can be enabled from the Windows app:** AI Settings clearly offers either keeping
  Kimi disabled or enabling it with full-computer access. Enabling requires an explicit risk
  confirmation; Windows no longer presents the unavailable project-scoped sandbox as usable.

## v0.6.46 — 2026-08-27

### 中文

- **KI 库页面现在能直接设置代理**：点击右上角 `⚙ → 网络与代理`，选择系统代理或
  手动输入本地 HTTP/mixed 端口，再勾选“GitHub 与 KI 更新”。更新失败窗口也新增了
  “网络设置”快捷按钮。
- **内置 KI 更新器正式使用独立代理线路**：不再依赖当前选中的 Claude、Codex 或 Kimi。
  老版本已经保存的代理设置会自动为新线路启用一次，用户仍可随时关闭。
- **避免 GitHub 分支缓存错配**：先读取分支的精确 commit，再下载该 commit 的归档；
  API 与压缩包不会再分别指向新旧两个版本。更新报告会显示实际线路和 commit。
- **实机验证**：通过 `http://127.0.0.1:7897` 连接 GitHub，锁定 commit
  `d3751874f6be277003fed19a3a1aa2dde612d166`，下载并安全解包 88,618,886 字节、
  127 个 KI，绝对符号链接为 0。

验证结果：GeoForge 测试 **159/159 通过**。

### English

- **Proxy settings are available in the KI Library:** use `⚙ > Network & proxy`, choose the
  system route or a local HTTP/mixed proxy port, and enable “GitHub & KI updates”. The update
  report now also offers a direct Network settings button.
- **The built-in updater has its own proxy target:** it no longer borrows the currently selected
  Claude, Codex, or Kimi route. Existing saved proxy settings adopt the new target once and remain
  user-controllable.
- **Commit-pinned downloads prevent branch-cache mismatches:** GeoForge resolves the exact branch
  commit first and downloads that immutable archive. Reports include the route and source commit.
- **Real-path validation:** the configured `http://127.0.0.1:7897` route reached GitHub, pinned
  commit `d3751874f6be277003fed19a3a1aa2dde612d166`, and safely extracted 88,618,886 bytes containing
  127 KIs with zero absolute symbolic links.

Validation: **159/159 GeoForge tests passed**.

## v0.6.45 — 2026-08-27

### 中文

- **通用网络配置**：AI 设置中的同一条代理线路现在同时覆盖所选 Agent 以及 Agent
  发起的 Git、pip、curl 和模型下载。支持自动检测、手动 HTTP/SOCKS 地址和关闭代理；
  Claude、Codex、Kimi 可以分别开关，不需要代理的 provider 不受影响。
- **连接失败不再只是 `Load failed`**：DNS、VPN、代理、登录服务不可达等问题会进入
  “需要你”弹窗，告诉用户具体失败位置并允许修改线路后重试。
- **模型安装位置可选**：在 Agent 设置页选择安装目录；目录不存在时 GeoForge 会创建。
  路径同时记录到 `kiss.toml` 和 `.geoforge-install.json`，之后的聊天和预检都能找到它。
- **旧 KI 路径自动兼容**：第一次预检前自动建立当前便携 KI 布局与旧模型脚本路径之间的
  映射，减少“已经安装但 Agent 找不到”的问题。
- **127 个 KI 全量更新**：来自主分支 KI 快照
  `90a9163bd696fa6d42a471fc0c5ac2b347156d64`。VIC、CaMa-Flood 和 Lohmann Routing
  中指向私有服务器的软链接已替换为真实文件，桌面包不再依赖作者机器路径。
- **KI harness 与校准检查加强**：正式加载完整 harness 合同；校准依赖与算法后端通过
  实际 import 重新检查，不再保留过期的“未就绪”结果。
- **版本与发布记录统一**：Mac、Windows、CLI 使用同一个版本源。发布包同时提供
  `release-manifest.json`、本更新日志和 `SHA256SUMS.txt`，方便 Agent 自动判断更新内容。

验证结果：GeoForge 测试 **156/156 通过**；KI 目录 **127/127 可读取**；失效 KI 软链接 **0**。

### English

- **Universal network route:** one configurable route now covers selected AI providers and the
  Git, pip, curl, and model-download commands they launch. Auto, manual HTTP/SOCKS, and off modes
  are available, with a separate switch for Claude, Codex, and Kimi.
- **Actionable connection failures:** DNS, VPN, proxy, and sign-in service failures now open a
  specific Needs You request instead of ending as an unexplained `Load failed`.
- **Selectable model installation:** users may choose or create the model folder. GeoForge records
  it in `kiss.toml` and `.geoforge-install.json` so later chats and preflights use the same location.
- **Legacy KI layout bridge:** portable KI paths are mapped before the first preflight, preventing
  already-installed tools from being mistaken for missing files.
- **All 127 KIs refreshed:** canonical KI snapshot
  `90a9163bd696fa6d42a471fc0c5ac2b347156d64` is included. Server-only VIC, CaMa-Flood, and Lohmann
  Routing links were replaced with real portable files.
- **Harness and calibration proof:** the full KI harness contract is loaded; calibration dependencies
  and numerical backends are proved by current imports rather than a stale cached result.
- **Auditable releases:** macOS, Windows, and CLI builds share one version source. Every release ships
  this changelog, a machine-readable manifest, and checksums.

Validation: **156/156 GeoForge tests passed**, **127/127 KIs catalogued**, **0 broken KI links**.

## v0.6.44 — 2026-08-27

- Added user-selectable and persistent KI model installation locations.
- 增加用户可选、可持久保存的 KI 模型安装目录。

## v0.6.43 and earlier / 更早版本

See the Git history and the GitHub release notes for earlier beta changes.
更早的 beta 更新请查看 Git 历史和 GitHub Release 页面。
