# oh-my-ztty 0.2.3 迭代与交付报告

日期：2026-11-20（Asia/Taipei）。本报告记录已经完成的发布、AUR 分发、实际升级和官网改进。所有测量均注明环境与范围，原始私人配置、历史内容及其哈希不在公开附件中。

## 1. 交付结果

**oh-my-ztty 0.2.3 已正式发布，AUR 的 `oh-my-ztty-bin 0.2.3-1` 可下载，开发机现有的用户级安装已从 0.2.1 升至 0.2.3，官网新文案已上线。**

| 交付项 | 位置或结果 |
|---|---|
| 正式发行 | [GitHub Release v0.2.3](https://github.com/LIghtJUNction/oh-my-ztty/releases/tag/v0.2.3) |
| AUR 包 | [oh-my-ztty-bin 0.2.3-1](https://aur.archlinux.org/packages/oh-my-ztty-bin) |
| 官网 | [lightjunction.github.io/oh-my-ztty](https://lightjunction.github.io/oh-my-ztty/) |
| 套件源码 | `915db41a5791b906db72ef79f18cea6b658db521` |
| 已验收的发行树 | `50721d16333ae313449f88935b1827e05d8327fb` |
| 官网源码 | `d2fa82b706c9f7c78c5d331a718e6f241f1fd276` |
| AUR 源码 | `5ca2747d2e63c26defa5b27e2b35333f4027d0d1` |

发行、AUR 和实际安装状态分别见 [public-release.json](workspace-0.2.3/public-release.json)、[aur.json](workspace-0.2.3/aur.json) 和 [installed.json](workspace-0.2.3/installed.json)。官网文案是在发行完成后独立合入的文档变更，因此官网提交与套件发行提交不同。

### 使用入口

Arch Linux 新安装可以执行：

~~~sh
yay -S oh-my-ztty-bin
~~~

现有用户级安装的更新入口是 `omztty update`；更新已接管的默认配置使用 `omztty config refresh`。本轮已经在开发机执行这两步，无须重复安装 AUR 包。`config refresh` 本身会直接应用符合条件的变更，没有 `--apply` 或预览参数。AUR 安装由 pacman/AUR helper 更新和卸载，套件会识别该来源并给出对应提示。

## 2. 命令补全：按真实语法交接给下一层

这一轮补全工作的关键是正确识别当前输入处于哪一层：套件命令、组件选项、文件路径，或者 `-e` / `--` 后交给另一个程序的命令。进入下一层后，补全器必须传递正确的词数组和光标位置。

完成的行为包括：

- `omztty config` 按具体动作补全适用选项，支持同步的 `status`、`pull`、`push` 层级。
- ztty 的 backend、text-plugin、session 和 MCP 命令按当前正式版本补全；选项值恰好是 `-e` 时，不会提前误判为执行边界。
- `-e` / `--` 后调用实际命令的补全器，覆盖 Git 子命令、中文分支名，以及空格与中文路径。
- text-plugin 参数支持带引号的 `NAME=绝对路径` 补全。
- 用户已经提供的组件补全器优先，并获得正确的上下文。
- zdot 的全局参数放在子命令前时仍能定位，例如 `omztty dot --root . sync pul<Tab>` 和 `omztty dot --root . plan --b<Tab>`。

6 组测试在独立 HOME、100×24 的真实 PTY 中发送 Tab，并检查得到的编辑缓冲区。测试还用标记证明首次 Tab 读取了预热缓存，用哨兵证明补全过程没有启动组件程序。测试与实现见 [PR #4](https://github.com/LIghtJUNction/oh-my-ztty/pull/4) 及 [发行版本的测试文件](https://github.com/LIghtJUNction/oh-my-ztty/blob/v0.2.3/tests/test_completion.py)。

另用实际公开发行包作了一次独立缓存核查：普通已接管 zsh 与 `omztty shell` 得到相同的物理运行时路径、缓存目录和 `fpath`；缓存中的一次性无害标记确实被读入，三次检查的缓存哈希、修改时间和 inode 均未改变。这里约 14.4–15.75 ms 的补全初始化时间只是三次诊断读数，不作为性能基准。[缓存证据](workspace-0.2.3/completion-cache.json)

## 3. 配置刷新与 Neovim 修复

### 只更新仍然等于旧默认值的文件

配置刷新依据三个版本作判断：旧版随包默认值、当前用户文件、新版随包默认值。只有当前文件仍与旧默认值一致，才会换成新版默认值。用户改动过、主动删除、额外添加的文件，以及自定义映射和源符号链接，都保留原状。

旧默认值存入 `.baseline`，其中仅包含公开的随包默认文件。这使得 AUR 原地替换运行时后，仍有依据判断哪些文件可安全刷新。旧 0.2.1 用户级安装先借助仍然存在的旧发行目录完成迁移，再形成独立基线。刷新前校验基线归属、版本和校验和；同版本重跑不产生变更，默认映射布局变化需要明确处理。实现使用 POSIX shell 与系统基础工具，没有新增 Python 运行依赖。

15 项针对性回归覆盖这些分支和失败处理。实现和讨论见 [PR #2](https://github.com/LIghtJUNction/oh-my-ztty/pull/2)。

### `:ZrcConnect` 保留未保存内容

旧实现用 `botright split` 复用当前缓冲区；当其中有未保存内容时，创建终端任务会失败。zrc 0.1.1 改为创建独立的 `botright new` 终端缓冲区，并在失败时清理临时窗口，恢复原缓冲区、焦点、文本和修改状态。

回归在真实 Neovim 中使用无害 shell 任务检查终端创建和失败恢复，没有启动真实 AI 服务或模型。本机升级后也确认了 Neovim 能加载 `:ZrcConnect`。组件发行见 [zrc v0.1.1](https://github.com/LIghtJUNction/zrc/releases/tag/v0.1.1)。

## 4. 正式发行与跨架构验证

本地最终验收对发行树执行了 **70 项套件测试**、两种架构的完整打包与清单检查，并实际运行 x86_64 安装器、shell 和图形终端。图形检查覆盖窗口可见、键盘命令执行、首次补全后 shell 可继续使用，以及组件版本。测试使用独立显示服务，完成后没有残留子进程，宿主显示状态不变。[验收记录](workspace-0.2.3/acceptance.json) · [清理记录](workspace-0.2.3/closure.json)

![0.2.3 本地图形终端验收截图](workspace-0.2.3/terminal.png)

正式发布工作流在原生 x86_64 和原生 ARM runner 上分别执行套件检查、实际捆绑程序 smoke test、图形窗口/键盘/补全/清理检查，然后发布资产。两种架构和 publish 共三个 job 全部成功。[正式工作流](https://github.com/LIghtJUNction/oh-my-ztty/actions/runs/44684467902) · [工作流记录](workspace-0.2.3/workflows.json)

发布后重新下载 6 个公开资产，检查 GitHub digest 和校验文件，并验证两个归档中的全部清单。每个架构均为 84 个清单文件，文件内容哈希与本地已验收候选完全一致。公开归档与本地归档的整体哈希不同，因此这里仅声明文件内容一致，不声明归档逐字节相同。[下载验证](workspace-0.2.3/public-release.json)

### 随包组件锁定

| 组件 | 版本 | 源提交 |
|---|---|---|
| ztty | 0.5.0 | `c4f8f48c9598284a589e609f25242b49ceabfea8` |
| ssmcp | 0.10.10 | `52a531a59e9ec9236a76eafc0f4f068799e44b15` |
| zshard | 0.2.0 | `1cfa1a1eb761d14e2ccfd5381282b6ccd1491cff` |
| zdot | 0.2.0 | `e6b5feb98b05c59e0986624c0742dfe4a9187a2a` |
| zrc | 0.1.1 | `f4a0fe84c3499c00c5a01f1831e34fcbf5d5790c` |
| zfetch | 0.1.0 | `f19b278676206d76626dd01e4b89f7ad9ce9318f` |

SSMCP 保持已经验收的 0.10.10 正式锁定；其他维护会话的源码候选不作为本次套件的已安装版本。具体锁定见 [dependencies.lock.json](https://github.com/LIghtJUNction/oh-my-ztty/blob/v0.2.3/dependencies.lock.json)。

### 主要公开资产 SHA-256

| 资产 | SHA-256 |
|---|---|
| `install.sh` | `63357dcfc811c8e43657797b4f242c499cbd3b90d829fe5eb1926bfb74a2342b` |
| `oh-my-ztty-0.2.3-linux-x86_64.tar.gz` | `58862acd3c4ce0584b60b00494b620336dd91b188ca9d8102f3cb867a99f1cef` |
| `oh-my-ztty-0.2.3-linux-aarch64.tar.gz` | `8b0d7c8ff30f165e51e8dd5c1e65506fc57c382709aac7bb122cdc35e16a1da6` |

### 修正过的失败及验证范围

较早的 0.2.2 ARM 发布检查在 doctor 阶段失败，阻止了资产发布。检查实际 ELF 依赖后，补齐了新版 ztty 需要的 Wayland、xkbcommon、FreeType、HarfBuzz、EGL/GLES 和 X11 运行库；doctor 现在保留加载器原始错误，smoke 失败时输出 stdout/stderr。最终 0.2.3 的双架构正式工作流通过。0.2.2 标签没有改写，也不将那次运行记录为成功发行。[运行库与诊断修复](https://github.com/LIghtJUNction/oh-my-ztty/commit/89c26cb911da0758d4a21ac8ee11770416d3df3c)

## 5. AUR：公开下载到实际包生命周期

AUR 的 `oh-my-ztty-bin 0.2.3-1` 已推送，公开 RPC 返回正确版本，匿名 HTTPS 克隆与发布提交一致。x86_64 与 aarch64 两次 makepkg 均从空源缓存开始，实际下载 GitHub 正式发行归档、核对校验和并完成包构建。AUR 源码：[Git](https://aur.archlinux.org/oh-my-ztty-bin.git) · [快照下载](https://aur.archlinux.org/cgit/aur.git/snapshot/oh-my-ztty-bin.tar.gz)。

包将运行时放在 `/usr/lib/oh-my-ztty`，唯一全局命令 `/usr/bin/omztty` 使用相对符号链接，手册、图标、许可证和补全放在 `/usr/share`。`PACKAGE_MANAGER=pacman` 标记让套件拒绝自行修改包管理器拥有的运行时，转而提示使用 pacman/AUR helper。安装包没有写用户 HOME 的 hook；保留上游二进制和清单，禁用 strip/debug 分拆。

实际提取 x86_64 包，在独立 HOME 验证了 12 类行为：布局、相对启动链接、84 文件清单、doctor、预设 shell、包内补全、更新/卸载保护、配置接管与普通 zsh、刷新保留修改、移除恢复旧配置、运行时文件不被改动、desktop 文件有效。

本机没有执行 host pacman 安装或移除。ARM 的本地检查覆盖包构建与文件校验；ARM 原生执行由上游正式工作流提供。三项 namcap 检查为 0 errors，仍有已记录的静态二进制加固、未 strip、shell 依赖推断以及 x86 主机检查 ARM 加载器相关 warnings，不宣称 lint 零警告。[完整 AUR 回执](workspace-0.2.3/aur.json)

## 6. 开发机实际升级与个人配置保护

真实执行 `~/.local/bin/omztty update`，从公开 Release 获取 0.2.3，随后执行 `omztty config refresh`。当前运行时指针为 `releases/0.2.3-linux-x86_64`，已接管配置版本也为 0.2.3。

| 项目 | 升级后结果 |
|---|---|
| 已管理映射 | 21 个，保持不变 |
| 检查的配置文件 | 30 个，其中 28 个不变 |
| 更新的文件 | 2 个经核实未修改的旧默认文件：`files/.zshrc`、`files/.config/nvim/lua/zrc/context.lua` |
| 意外变化或缺失 | 0 |
| 终端默认项、桌面链接/源、映射清单 | 保持不变 |
| shell 历史 | 升级前即时检查点到升级验证之间，逐字节一致 |
| 新默认值基线 | 0.2.3，已核验仅含公开默认文件 |
| 重复刷新 | 成功，无变更 |
| 已安装发行清单 | 84 个文件全部验证通过 |
| 升级前已运行的旧终端进程 | 4 个仍在运行，未被关闭 |

这里对历史文件的判断仅适用于升级窗口。用户在较早任务阶段仍可能正常使用终端，不能把这个结论扩展成整个工作期间历史文件从未变化。[已脱敏安装回执](workspace-0.2.3/installed.json)

初次升级验证脚本曾错误地要求启动后立即存在补全注册；项目采用延迟初始化，因此该最后探针返回失败，而实际更新、配置刷新和保护检查均已通过。修正后的针对性探针先调用 `zshard complete`，确认 READY 从 0 变成 1，并核对加载的新补全源文件；Neovim 与清单检查随后全部通过。报告保留这一验证脚本修正，避免把失败记录隐藏或误报成产品缺陷。

## 7. 启动耗时：同一机器上的有限观测

每个场景先预热 3 次，再测量 21 次；使用阻塞 waitpid 计时。测量对象为已接管用户配置下的暖缓存进程启动，排除终端绘制、交互提示符和网络操作。

| 场景 | 0.2.1 中位数 / p95 | 0.2.3 中位数 / p95 |
|---|---:|---:|
| `zsh -d -i -c exit` | 9.423 / 11.223 ms | 10.785 / 11.861 ms |
| `zsh -d -i -l -c exit` | 10.005 / 11.209 ms | 8.992 / 12.174 ms |
| `nvim --headless +qa` | 13.826 / 15.538 ms | 15.195 / 19.132 ms |

这批观测中不同场景有升有降，机器负载也在变化。数据支持报告具体测量结果，不足以说明这轮改动导致整体变快或变慢。全部样本、命令和负载信息见 [startup.json](workspace-0.2.3/startup.json)。

## 8. 官网文案与上线检查

首页标题改为 **“A working terminal setup for Linux”**，开头先交代适合谁、解决什么问题，再给三条起步命令和可选择的配置接管路径。9 页说明统一了组件职责、安装、更新、移除、补全、插件加载时机、AI 按需使用和保留个人修改的边界。旧组件版本硬编码被移除；历史性能数据继续标注其旧测量版本，避免被误读为当前结果。

本轮沿用已有模板和样式，保持留白与克制视觉。静态构建生成 9 页、17 个文件，验证 490 条站内链接，版本更新脚本与文档的契约检查保留。文案经独立事实核对后合入 [PR #5](https://github.com/LIghtJUNction/oh-my-ztty/pull/5)，GitHub Pages build 与 deploy 均成功。[部署工作流](https://github.com/LIghtJUNction/oh-my-ztty/actions/runs/44685625981)

![已上线的官网首页](workspace-0.2.3/website.jpg)

通过实际在线 Chromium 页面确认了新标题和正文。桌面视口为 1363×936，文档宽 1348；桌面 400% 缩放下的 CSS 视口为 340×234，文档宽 337、标题宽 295，没有页面级横向溢出。后者是窄视口近似检查，不代表真机手机测试。检查后已恢复 100% 缩放。[在线检查记录](workspace-0.2.3/website.json) · [窄视口截图](workspace-0.2.3/website-narrow.jpg)

## 9. 证据索引与边界

| 附件 | 内容 |
|---|---|
| [acceptance.json](workspace-0.2.3/acceptance.json) | 本地发行树、组件来源、打包与实际程序检查 |
| [closure.json](workspace-0.2.3/closure.json) | 70 项测试计数及隔离显示/进程清理 |
| [public-release.json](workspace-0.2.3/public-release.json) | 公开资产哈希、84 文件清单与本地内容比对 |
| [aur.json](workspace-0.2.3/aur.json) | AUR 发布、匿名读取、双架构构建和生命周期验证 |
| [installed.json](workspace-0.2.3/installed.json) | 真实升级、配置保留与探针修正 |
| [completion-cache.json](workspace-0.2.3/completion-cache.json) | 一次性私有 HOME 中的缓存实际读取证据 |
| [startup.json](workspace-0.2.3/startup.json) | 升级前后启动耗时的全部样本 |
| [website.json](workspace-0.2.3/website.json) | 已部署页面的文案和视口检查 |
| [workflows.json](workspace-0.2.3/workflows.json) | 正式发行与 Pages 工作流各 job/step 结果 |
| [figures.json](workspace-0.2.3/figures.json) | 三张原始截图的来源、大小与哈希 |

本报告的公开附件只包含任务结果、测试用一次性环境及必要的计数。私人配置内容、私人配置校验和和历史文本没有随报告发布。对 AI 连接的测试范围是终端创建、配置加载和失败恢复；本轮没有把真实模型会话连通性作为已经验证的结果。
