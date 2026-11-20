# oh-my-ztty 0.1.1 发布与验收报告

日期：2026-11-20（Asia/Taipei）。正式资产发布于 2026-11-19 20:33:19 UTC，公开下载验收于同日 20:35:36 UTC 完成。

**oh-my-ztty v0.1.1 已公开发布，x86_64 与 ARM64 原生发布检查、公开网络安装及卸载复验均通过。** 新项目 oh-my-ztty、zshard 和 zdot 均为公开 MIT 仓库。

- [套件发行页](https://github.com/LIghtJUNction/oh-my-ztty/releases/tag/v0.1.1)
- [GitHub Pages 官网](https://lightjunction.github.io/oh-my-ztty/)
- [正式发布工作流](https://github.com/LIghtJUNction/oh-my-ztty/actions/runs/44609624654)
- [公开资产与安装验收原始记录](public-release-0.1.1.json)

## 1. 版本与仓库结构

套件发布提交为 [`94e173a7b61bba34db913b1dd1764518f2e46ccd`](https://github.com/LIghtJUNction/oh-my-ztty/commit/94e173a7b61bba34db913b1dd1764518f2e46ccd)。四个组件均通过真正的 Git submodule 固定到具体提交，见 [发布时的 .gitmodules](https://github.com/LIghtJUNction/oh-my-ztty/blob/v0.1.1/.gitmodules)。

| 组件 | 固定版本 | 职责 | 固定提交 |
| --- | --- | --- | --- |
| [ztty](https://github.com/LIghtJUNction/ztty) | 0.4.1 | 终端、PTY 与渲染 | `6b91e29e923aaee0207953f2b04393087f19e0d8` |
| [zshard](https://github.com/LIghtJUNction/zshard/releases/tag/v0.1.2) | 0.1.2 | 新写的原生 zsh 框架 | `a2dd935ede92fb96a0dc0556ce16e5f7494a0448` |
| [zdot](https://github.com/LIghtJUNction/zdot/releases/tag/v0.1.1) | 0.1.1 | 新写的 no_std dotfiles 管理器 | `43cc523c0fd4331402d2393280509ac2c672a262` |
| [ssmcp](https://github.com/LIghtJUNction/ssmcp) | 0.10.10 | 按需连接 AI 的 MCP 工作区客户端 | `52a531a59e9ec9236a76eafc0f4f068799e44b15` |

zsh 由 Linux 发行版提供。套件版本记录一组经过验证的组件版本；各组件仍可独立安装、开发和发布。

## 2. 已实现的用户体验

### Ink 默认预设

实际配置包含石墨色背景、完整低饱和 ANSI 配色、24 px 内边距、13 pt 字体请求和两行提示符。第一行显示路径与缓存的 Git 分支，第二行留给输入；失败状态和至少两秒的命令耗时按需显示。

字体通过 Fontconfig 在已安装字体间回退，提示符不依赖私用区图标。当前隔离环境实际选择了 JetBrainsMono Nerd Font；用户的字体安装情况和 Fontconfig 规则会影响结果。提示符回调只使用 zsh 内置命令，不创建外部进程。

[真实运行截图（截图归档）](https://github.com/LIghtJUNction/oh-my-ztty/releases/download/v0.2.6/oh-my-ztty-generated-evidence-20261121.tar.gz) · [Ink 配置](https://github.com/LIghtJUNction/oh-my-ztty/blob/v0.1.1/config/zsh/ink.zsh)

### Shell 与插件接口

zshard 提供延迟初始化的补全、历史建议、轻量命令高亮、vi/emacs 键位，以及立即、延后、首次使用三种插件加载方式。主题、钩子、卸载清理和示例插件均已发布。远程插件固定完整 Git commit，并提供验证、导出和恢复入口。

安装器先预热经过原生审计的补全缓存，再切换当前版本。v0.1.2 继续执行原生 `compinit -i` 审计，并识别所有权变化及同数量文件替换，避免把失效缓存当作可用结果。

插件生态在这里指已实现并公开的扩展接口、文档、示例与锁定机制；不据此声称已有大型第三方社区。[插件文档](https://github.com/LIghtJUNction/zshard/blob/v0.1.2/docs/plugins.md) · [缓存设计与兼容性记录](https://github.com/LIghtJUNction/zshard/blob/v0.1.2/docs/completion-cache.md)

### AI 接口

`zai context` / `omztty ai context` 输出明确的结构化上下文，默认不附带环境变量、历史、文件内容或上一条命令。提供者通过 argv 数组配置，请求和上下文走标准输入，返回文本不会被自动求值。`zai propose` 把命令放入编辑缓冲区，执行仍由用户按 Enter 决定。

`omztty ai connect` 在当前工作区启动预装的 ssmcp。普通 shell 启动不连接远端模型。实际外部提供者与 ssmcp 身份认证由用户配置；本轮验证了本地上下文和提供者接口契约，没有把外部付费模型调用列为已完成测试。

### Dotfiles

zdot 支持先 plan、再 apply，默认拒绝冲突；显式 backup 支持冲突备份与恢复。remove 会检查链接归属，Git 同步为显式操作，pull 使用 fast-forward-only。

当前实现使用有界缓冲区：每个 profile 最多 128 条映射、64 KiB profile、4 KiB 路径。新 Rust 库与 Linux CLI 均为 no_std，不使用 allocator、libc 或动态 ELF interpreter，依赖 Project Z 的 zclap。正式 x86_64 可执行文件为 53,848 bytes，ARM64 为 66,168 bytes。[zdot 文档](https://github.com/LIghtJUNction/zdot/tree/v0.1.1)

## 3. 安装、配置与卸载

支持 Linux x86_64、ARM64，要求系统 zsh 5.9+。正式运行验证平台为 Ubuntu 24.04。图形终端使用 X11/XWayland，依赖 X11、Xrender、Xft、Fontconfig；两种架构的 ztty 与 ssmcp 直接 glibc 符号下限均为 2.34。该 ABI 下限不等于已经验证所有发行版。

Ubuntu 24.04 的基本依赖与安装方式：

```sh
sudo apt-get install zsh git curl libx11-6 libxrender1 libxft2 libfontconfig1
curl -fLO https://github.com/LIghtJUNction/oh-my-ztty/releases/latest/download/install.sh
sh install.sh
~/.local/bin/omztty doctor
~/.local/bin/omztty shell
~/.local/bin/omztty terminal
```

下载后可先查看安装脚本。发行包安装不需要 Rust 或 Python。默认命令目录是 `~/.local/bin`；安装器按用户安装，验证下载包及文件清单，以版本目录和 current 链接管理活动版本。

`~/.config/oh-my-ztty/options.zsh` 在框架初始化前加载，`local.zsh` 在默认主题之后加载。个人配置保留在发行包之外，可用于选项、别名、插件、主题和 AI 提供者配置。

```sh
omztty update
omztty uninstall
```

重复安装相同发行包验证现有内容；冲突或被修改的版本会被保留并报告。卸载移除仍属于套件的安装文件和入口，保留用户配置、历史与 dotfile 仓库。dotfile 管理的链接有独立生命周期，可先用 zdot remove 撤销。

[完整安装说明](../installation.md)

## 4. 实测性能及解释

### 框架初始化

开发机为 Intel Core i9-12900HX、Arch Linux、zsh 5.9.2。每项 31 次交错运行，预热 3 次；测量包含进程创建和初始化，所有配置均不包含首次提示符绘制。

| 配置 | 中位数，ms | p95，ms | 空闲 PSS，KiB |
| --- | ---: | ---: | ---: |
| 最小配置 zsh | 1.679 | 2.005 | 767 |
| zsh + 原生审计补全 | 12.291 | 15.236 | 2,308 |
| zshard，补全延迟 | 4.106 | 5.114 | 1,161 |
| zshard，补全已就绪 | 19.185 | 24.213 | 2,500 |
| Oh My Zsh，git + robbyrussell | 28.403 | 33.335 | 2,824 |

此配置中的 Oh My Zsh 初始化时间为延迟 zshard 的 6.92 倍，或补全已就绪 zshard 的 1.48 倍。功能组合不同，不能把它解释为所有插件配置的排名。Oh My Zsh 固定到 `c0140703a53eb0d22be44f7bac318d0baacc927c`，关闭自动更新，没有额外建议或高亮插件。

首次 Tab 的暖缓存中位数为 15.848 ms；新建缓存为 147.310 ms。延迟初始化把工作移到首次需要的时候，安装预热减少冷缓存成本，二者都没有消除实际工作量。

[方法与完整样本](https://github.com/LIghtJUNction/zshard/blob/v0.1.2/docs/benchmarks/release-0.1.2.json)

### 完整 Ink 套件

完整 shell 路径另做 40 次交错运行：`omztty shell -i -c exit` 中位数 **10.914 ms**、p95 **13.057 ms**。同一轮最小配置 zsh 中位数 **2.700 ms**、p95 **3.893 ms**。该实验包含 launcher 和预设初始化，不包含提示符、首次 Tab、模型或网络调用，不与上面的独立框架实验直接相减。

真实窗口使用隔离 Xvfb、临时 HOME 和 Git checkout、100×28 字符网格、Ink 字体与 padding，无 AI 连接：

| 进程 | 首次 Tab 前 PSS，KiB | 首次 Tab 后 PSS，KiB |
| --- | ---: | ---: |
| ztty broker 与渲染 | 10,425 | 10,425 |
| 预设 zsh | 2,718 | 3,746 |
| 等待中的 launcher/client | 850 | 850 |
| 合计 | 13,993（13.67 MiB） | 15,021（14.67 MiB） |

PSS 按映射该内存页的进程分摊共享页，可减少把共享库重复计入合计的影响。这是对应空闲点的驻留内存，不是峰值，不包含 X server 或活跃 AI 会话。ztty 的 broker 包含在合计中。

实测候选包 SHA-256 为 `6d4a608a037c625b76be3b2d19f269fef69046112868a732e9c8dbf7e69e7e6f`。正式包在 GitHub 原生 runner 单独构建，其精确校验值见下文，不能把两个不同字节的包混为一谈。

首次真实 Tab 前后，安装器生成的 completion dump 的 SHA-256 和 mtime 均保持不变。[完整性能说明](../performance.md) · [套件原始记录](linux-x86_64-suite.json) · [缓存复用证据](linux-x86_64-completion-cache.json)

另外保留了 Xvfb/software-GL 的终端诊断。它只有一次启动，ztty padding 为 24 px、kitty 为 24 pt，不属于原生 GPU 桌面或严格同条件排名，本报告不从该记录推导通用领先倍数。

## 5. 发布验证结果

[正式套件工作流](https://github.com/LIghtJUNction/oh-my-ztty/actions/runs/44609624654) 已成功完成 Ubuntu 24.04 x86_64、ARM64 原生构建、安装生命周期、真实程序与图形验证。最终本地 suite 检查为 11/11。

正式发布之后，重新下载全部 6 个公共资产，核对 GitHub digest、3 个 sidecar、2 个完整 MANIFEST，并审计两架构的 6 个 ELF 文件。zdot 两架构均无动态依赖；ztty 与 ssmcp 的系统依赖已记录。

公开下载的 install.sh 使用默认联网路径执行，没有 `--from`、版本覆盖或下载地址覆盖。隔离 HOME 名字含空格，以下检查全部通过：

- 默认安装两次，current 链接目标和 inode 均保持不变。
- doctor、交互 shell 和本地 AI context 均退出为 0。
- 预置配置与一个真实历史文件经过安装和卸载后保持不变。
- 卸载移除安装目录、5 个托管命令入口、桌面入口和 man-page 链接。
- 没有启动 AI 连接；临时 HOME 已清理。

[公开验收 JSON](public-release-0.1.1.json) 包含步骤输出、资产摘要、ELF 依赖和归一化路径。官网的[最后部署](https://github.com/LIghtJUNction/oh-my-ztty/actions/runs/44609624729)成功，线上 HTML 与该次提交一致；桌面及窄屏布局、主要链接和交互此前已检查。

## 6. 正式资产校验值

| 文件 | Bytes | SHA-256 |
| --- | ---: | --- |
| [install.sh](https://github.com/LIghtJUNction/oh-my-ztty/releases/download/v0.1.1/install.sh) | 8,728 | `de2744d907b2d8bf32d377541b6fcefab50f47e44097b412789a7f052f1ce947` |
| [install.sh.sha256](https://github.com/LIghtJUNction/oh-my-ztty/releases/download/v0.1.1/install.sh.sha256) | 77 | `e77ccc65504ba7043953555612311f907b7a95db3b1bbaa1a08061292081f182` |
| [oh-my-ztty-0.1.1-linux-x86_64.tar.gz](https://github.com/LIghtJUNction/oh-my-ztty/releases/download/v0.1.1/oh-my-ztty-0.1.1-linux-x86_64.tar.gz) | 5,247,053 | `323bd20b9d5048db2ce034184036b54feef677c0e28bc7828e80639666c1def8` |
| [oh-my-ztty-0.1.1-linux-x86_64.tar.gz.sha256](https://github.com/LIghtJUNction/oh-my-ztty/releases/download/v0.1.1/oh-my-ztty-0.1.1-linux-x86_64.tar.gz.sha256) | 103 | `dd6561b07545096db65d1c713fa2d205dad1133113e56795328779989e815720` |
| [oh-my-ztty-0.1.1-linux-aarch64.tar.gz](https://github.com/LIghtJUNction/oh-my-ztty/releases/download/v0.1.1/oh-my-ztty-0.1.1-linux-aarch64.tar.gz) | 5,054,011 | `043b221a74bbacae195caebce7a17d2c6690415a9cde3b89b1bfd85855f1977a` |
| [oh-my-ztty-0.1.1-linux-aarch64.tar.gz.sha256](https://github.com/LIghtJUNction/oh-my-ztty/releases/download/v0.1.1/oh-my-ztty-0.1.1-linux-aarch64.tar.gz.sha256) | 104 | `71eab66a7fec88e56a2dbc2a0897260569dcffcb77bac0c1dc905688f5c19c37` |

## 7. 后续迭代

从干净的 main 工作区运行：

```sh
python3 scripts/workspace.py status
python3 scripts/workspace.py check
python3 scripts/bump.py patch --release
```

每个新项目提供 major/minor/patch bump 接口。组件先发布，再更新套件 gitlink 和依赖锁，随后发布套件。日常检查在开发机执行；保留手动验证入口，正式 tag 执行双架构发布门禁，网站变更独立部署 Pages。普通代码 push/PR 不启动重复的日常测试矩阵。

[开发与发布说明](../../CONTRIBUTING.md)

## 8. 依赖与结论边界

新的 zdot 库和 CLI 是 no_std、无 allocator、无 libc；zshard 使用系统 zsh；固定的 ztty core 与可执行程序也使用 Rust no_std，但图形前端仍有 X11 和系统库依赖。预装 ssmcp 保留自身 Rust 标准库和网络依赖，按需启动。因此不能把整个软件包称为“完全没有任何标准库或系统库”。

性能优势的来源是减少常驻进程、把可选工作留到使用时执行、保持提示符本地运行，以及复用仍通过审计的缓存。当前记录支持上面列出的配置与环境；“所有环境都最快、最省内存”仍需要更广泛且同条件的证据。
