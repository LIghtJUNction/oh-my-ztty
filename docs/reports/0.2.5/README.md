# Oh My Ztty v0.2.5：33 个原生命令补全入口

日期：2026-11-20。发行源码：[74e492c](https://github.com/LIghtJUNction/oh-my-ztty/commit/74e492c88a3ba8b6b59802a0fad3e74cf73712c7)。[正式发行](https://github.com/LIghtJUNction/oh-my-ztty/releases/tag/v0.2.5)。

本次更新为套件组件、常见 AI 客户端、开发工具以及作者的公开 CLI 提供 33 个原生 zsh 补全入口。补全按光标所在位置选择有效的子命令、选项、枚举值或路径；中文与空格路径、目录参数、自由文本和被调用命令的参数边界都有实际 Tab 回归覆盖。

## 覆盖范围

33 按命令入口计数，共享辅助函数和复用的系统补全不计入。

| 类别 | 数量 | 命令 |
| --- | ---: | --- |
| 套件 | 7 | omztty、ztty、zdot、zfetch、zshard、zai、ssmcp |
| AI 客户端 | 6 | codex、claude、gemini、opencode、pi、amp |
| 开发工具 | 7 | go、node、npx、yarn、rustc、rustup、cmake |
| 作者的其他 CLI | 13 | zcalld、ssmcpd、ztype、zuse、zmcl、onim、lmm、mechrevo-console、wgt、douyin、lightjunction、coolapk、binance-cli |

Git、uv、Cargo、npm／pnpm／Bun、Python／pip、Docker／Podman、gh、just 和常见基础命令继续使用已安装的系统定义。Rustup 在实际终端检查中暴露了顶层及 target 子命令的插入问题，因此本轮为它提供单独的原生定义。[完整覆盖与版本清单](../../completions.md)。

## 实际使用

在以下输入末尾按 Tab：

| 输入 | 补全结果 |
| --- | --- |
| `ssmcp --theme nor` | `ssmcp --theme nord` |
| `ssmcp sessions lo` | `ssmcp sessions logs` |
| `codex exec --sandbox work` | `codex exec --sandbox workspace-write` |
| `claude mcp add demo --transport ht` | `claude mcp add demo --transport http` |
| `go mod ti` | `go mod tidy` |
| `rustup target ad` | `rustup target add` |
| `zcalld library mcp apply --agent gem` | `zcalld library mcp apply --agent gemini` |
| `binance-cli spot klines --interval=15` | `binance-cli spot klines --interval=15m` |

目录参数严格排除普通文件；AI 提示词、源码文本、账号名和动态 ID 保留为自由文本。用户的个人补全始终优先于套件定义。相关加载顺序修复已同步至 [zshard v0.2.1](https://github.com/LIghtJUNction/zshard/tree/v0.2.1)。

新定义使用静态语法及本地路径。按 Tab 不启动对应 AI、编译、游戏、硬件或交易程序，也不为获取候选而查询远程 API。已有系统补全及 `--` 之后委托给其他命令的补全，仍可能进行各自的本地发现。

## 语法边界

补全依据实际安装版帮助或明确版本的源码维护。ssmcp 客户端对应套件固定的 **0.10.10**，独立 ssmcpd 对应 **0.10.15**。Codex、Claude Code、Gemini CLI 分别核对 **0.170.0、2.1.329、0.46.0**；OpenCode、pi、Amp 分别核对 **2.3.2、1.5.2、0.0.1795147237-g4dbcdb**。

Binance CLI 使用 **2.3.0** 的 916 个公开帮助节点，其中 39 个分组、877 个叶命令。静态表包含公开帮助和 binance-sdk 77.2.0 已确认的枚举；它注册的是 `binance-cli`，保留独立的 `binance` 命令。内联 JSON 不会误补成文件名，任意 request 尾参也不会重新解释为 CLI 全局选项。

这份覆盖表不承诺自动识别未来新增参数、用户插件定义的选项或私人账号数据。没有用户命令入口的库、内部测试及基准二进制不生成虚构命令。

## 验证

| 层次 | 结果 |
| --- | --- |
| 最终源码全量检查 | `make check`：**87 项测试全部通过**，27.604 秒 |
| 实际终端补全 | 全量检查包含 **23 个真实 PTY 补全测试组**；检查编辑后的输入缓冲区与应用执行陷阱 |
| 文档站点 | 9 页、17 个文件、492 个本地链接检查通过 |
| 本地发行包 | 安装、重复安装、doctor、组件命令、配置采用／恢复、卸载通过 |
| 正式双架构发行 | run 44703223337 成功；x86_64 与 aarch64 正式归档已发布 |
| Arch/AUR 包 | 0.2.5-1 已推送并安装；双架构包构建、12 项 x86_64 生命周期及 15/15 个普通 zsh Tab 用例通过 |
| 本机用户安装 | 用户运行时从 0.2.3 升级至 0.2.5；doctor 通过，个人 profile 与补全保持原样 |

AUR 的 ARM 包完成了构建、清单与 ELF 架构检查；本轮本机包生命周期和安装验收使用 x86_64，未在 ARM 设备上执行 AUR 包。

具体记录见 [verification.json](verification.json)。正式流程：[Release 44703223337](https://github.com/LIghtJUNction/oh-my-ztty/actions/runs/44703223337)。

## 安装后的表现

在同一次交错测量中，每组先预热 3 次，再采样 21 次；使用隔离 HOME、净化环境与显式 `-i -c 'exit 0'`。套件数据包含启动器与 shell 初始化。

| 场景 | 中位数 | p95 |
| --- | ---: | ---: |
| 普通 zsh | 6.208 ms | 12.673 ms |
| 已安装 0.2.3 | 10.366 ms | 14.187 ms |
| 已安装 0.2.5 | 10.793 ms | 15.170 ms |

这些数值描述本机当前负载下的暖启动样本。新旧版样本中位数相差约 0.427 ms，不能由这一轮数据单独判断性能变化。计时范围不包含提示符绘制、首次 Tab 或网络，原始样本与执行顺序保存在验证 JSON 中。

真实用户配置下的 **11/11 个 Tab 用例**通过；个人补全目录位于套件及框架定义之前，实际选中了个人覆盖函数。

[已安装版本中的 ssmcp 原生补全（截图归档）](https://github.com/LIghtJUNction/oh-my-ztty/releases/download/v0.2.6/oh-my-ztty-generated-evidence-20261121.tar.gz)

截图在隔离图形显示环境中使用已安装的 ztty 与新运行时生成，并核对真实命令缓冲区。它不影响当前桌面的输入或已有终端会话。

## 更新记录

本轮分批提交了 [套件组件补全](https://github.com/LIghtJUNction/oh-my-ztty/commit/9cdf90bae1b61d148cc4a4ae457a75a872f9bbba)、[AI 与开发工具补全](https://github.com/LIghtJUNction/oh-my-ztty/commit/ad5fca81b9ab19226fae98531c25478671407a36)以及[完整 CLI 覆盖与 v0.2.5](https://github.com/LIghtJUNction/oh-my-ztty/commit/74e492c88a3ba8b6b59802a0fad3e74cf73712c7)。升级后打开新的套件 shell，即可加载匹配新版本的补全缓存。
