# oh-my-ztty 0.2.6 发布与验收记录

记录日期：2026-11-20（UTC）。

**0.2.6 已正式发布，开发机的用户级套件已升级到这一版。** 两个 Linux 架构的原生发行门禁均通过，六个公开制品于 10:31:09 UTC 发布。实际升级使用重新下载并复验的正式 x86_64 归档。 [正式发行](https://github.com/LIghtJUNction/oh-my-ztty/releases/tag/v0.2.6) · [发行运行](https://github.com/LIghtJUNction/oh-my-ztty/actions/runs/44719594477) · [结构化收据](release.json)

## 本版改动

本版把已经正式发布的组件组合落实到套件的源码指针、归档地址和 SHA-256。ztty 使用 0.5.2，SSMCP 客户端使用 0.10.20，zfetch 与 zrc 分别更新到 0.1.1 和 0.1.2。zshard、zdot 保持已有固定源码。SSMCP 服务端部署不属于本次套件发行。[源码差异](https://github.com/LIghtJUNction/oh-my-ztty/compare/8efa280a43229870a12098626a9e9143709bb231...1e3ce8d3e5a141d09e450fd3f635f987a5732be4)

补全现在遵守实际参数解析方式。zfetch 的最后一个格式参数生效，因此可以在已有 `--json` 后继续补全 `--format`，也可以反过来使用。套件预设入口 `omztty terminal` 补全启动参数、路径以及 `-e` / `--` 后的命令；直接控制入口 `ztty` 和 `omztty ztty` 提供 `attach`、`mcp` 和 `reload --binary`。新增真实 PTY 用例保留个人补全优先级、参数数量和不执行补全目标的检查。[zfetch 修复](https://github.com/LIghtJUNction/oh-my-ztty/commit/00a46287ea732127f38ed65d8d9149ae1687795a) · [终端入口修复](https://github.com/LIghtJUNction/oh-my-ztty/commit/2554847f9085949d81a905d8f320932ced28a1e3) · [补全参考](../../completions.md)

## 不可变来源

发行标签 `v0.2.6` 指向源码 `1e3ce8d3e5a141d09e450fd3f635f987a5732be4`，源码树为 `753a123cd9c1019c92a20f4804b08a00e5e54679`。附注标签对象为 `5a5f45dcc37c443876aee5d29ed280bcf6c6058d`。发布后的报告提交不会移动这一标签。

| 组件 | 版本与用途 | 固定源码提交 |
| --- | --- | --- |
| ztty | 0.5.2，终端可执行文件 | `6e2ce246b0b50e6b82da99756832feae6e966f21` |
| SSMCP | 0.10.20，客户端可执行文件 | `4f4dd88275c205e0e61a7601b4e0d11f56038769` |
| zfetch | 0.1.1，系统概况命令 | `154c9b826a794e22135eda2d77a03b7214f8e427` |
| zrc | 0.1.2，套件采用的配置文件 | `e6e6a7d4a07bc74ae95b5ec1f0391ad4e5155d86` |
| zshard | 0.2.1，shell 框架 | `f7842f70e439c4abda2a46698f0ebe067d38b297` |
| zdot | 0.2.0，配置部署工具 | `e6b5feb98b05c59e0986624c0742dfe4a9187a2a` |

两架构包的 `BUILD.json` 均记录上述六个提交。ztty 与 SSMCP 取自其已发布归档；zdot 和 zfetch 由固定源码构建；zshard 和 zrc 复制固定的受版本控制文件。读取到的 CI 归档与公开 Release API 的 SHA-256 完全一致，每包 126 项内容清单均重新计算通过。发布后，准备方从六个公开 Release URL 独立下载，耗时 9.836 秒。安装前再次核对了六个文件的尺寸与 SHA-256、三份 sidecar 的内容和两个归档的 ELF。[构建入口](https://github.com/LIghtJUNction/oh-my-ztty/blob/1e3ce8d3e5a141d09e450fd3f635f987a5732be4/scripts/build_bundle.py) · [x86_64 运行记录](linux-x86_64-suite.json) · [ARM64 运行记录](linux-aarch64-suite.json)

## 验收结果与边界

正式运行 `44719594477` 的三个 job 全部成功。两个架构均完整检出递归子模块，执行原有检查、真实套件构建、隔离 HOME 安装 smoke，以及真实终端窗口、键盘、补全和进程清理；只有这两项架构工作都成功后，发布 job 才公开制品。工作流和这些门禁没有放宽。[发行工作流](https://github.com/LIghtJUNction/oh-my-ztty/blob/1e3ce8d3e5a141d09e450fd3f635f987a5732be4/.github/workflows/release.yml)

| 验证 | 实际结果 | 证据 |
| --- | --- | --- |
| 本机原 `make check` | 90/90 通过，0 跳过；总用时 37.269 秒 | [本机结果摘要](local-validation.json) |
| 本机两架构候选构建 | x86_64 原生构建、ARM64 实际交叉构建均通过；各包 126 项清单与四个 ELF 核验通过 | [本机结果摘要](local-validation.json) |
| 本机真实 x86_64 安装 smoke | 安装、重复安装、组件命令、配置部署与恢复、卸载通过 | [本机结果摘要](local-validation.json) |
| 本机混合版本生命周期 | 正式 0.2.5 → 候选 0.2.6 → 0.2.5 → 0.2.6 通过；观测到三次 `current` 原子替换；个人编辑、主动删除、Tab 覆盖和备份恢复通过 | [本机结果摘要](local-validation.json) |
| 本机图形脚本 | 未通过环境前置：Xvfb 尚未启动候选 ztty，沙箱的两类 AF_UNIX 监听均返回 EPERM | [本机结果摘要](local-validation.json) |
| 正式 x86_64 全部门禁 | 成功，包括真实图形与清理 | [job 136231641285](https://github.com/LIghtJUNction/oh-my-ztty/actions/runs/44719594477/job/136231641285) |
| 正式 ARM64 全部门禁 | 成功，包括原生运行、真实图形与清理 | [job 136231640959](https://github.com/LIghtJUNction/oh-my-ztty/actions/runs/44719594477/job/136231640959) |
| 站点 | 本机 9 页、493 个本地链接通过；正式 Pages 运行成功 | [Pages 运行](https://github.com/LIghtJUNction/oh-my-ztty/actions/runs/44719510034) |

本机检查使用了明确标注的稀疏输入：ztty 与 SSMCP 保留正式标签、提交及根目录文件，套件采用其已校验二进制；实际构建或复制的另外四个源码组件完整检出。这个范围没有被描述为本机完整递归源码编译。本机图形拒绝记录也被保留，没有通过更改沙箱或另一路主机命令重跑来掩盖；正式 runner 的成功单独记录。

### 正式窗口样本

以下数据来自两个正式 runner 上各一个 100×28 单元的私有 Xvfb 窗口，字体解析为 DejaVu Sans Mono，窗口留白 28 像素。X 服务本身不计入应用内存。shell 启动值是预热后 `omztty shell -ic exit` 的 10 次进程用时样本中位数，不包含提示符、Tab、模型或网络请求。不同 runner 的结果不能当作同机版本性能对照。[x86_64 原始数据](linux-x86_64-suite.json) · [ARM64 原始数据](linux-aarch64-suite.json)

| 观测值 | x86_64 | ARM64 |
| --- | ---: | ---: |
| 窗口首次可见 | 133.571 ms | 167.025 ms |
| 预热 suite shell 启动中位数 | 4.505 ms | 6.335 ms |
| 首次补全后 ztty broker RSS | 101,176 KiB | 105,560 KiB |
| 首次补全后 zsh RSS | 6,632 KiB | 5,884 KiB |
| 首次补全后等待启动器 RSS | 5,992 KiB | 4,984 KiB |
| 预生成补全缓存被复用 | 是 | 是 |

这些单窗口样本不能证明全进程峰值低于 10 MiB，也没有提供相对 0.2.5 的受控性能增益结论。图形报告中的进程清理均成功，临时 HOME 已移除。

![x86_64 正式验收窗口](linux-x86_64-terminal.png)

![ARM64 正式验收窗口](linux-aarch64-terminal.png)

## 公开制品

下面列出 Release `452554850` 公开元数据中的 SHA-256。下载时应同时核验归档和同版本 sidecar；完整 URL、字节数和侧车文件身份保存在 [release.json](release.json)。

| 文件 | 字节数 | SHA-256 |
| --- | ---: | --- |
| `install.sh` | 10,917 | `ec281545ebed3c84027504750621951bcf310e66c5eb5baa8e0a6635b99d26d2` |
| `install.sh.sha256` | 77 | `0d311db16c1911c2b37e7eccbe0aa1745bfab9718bcb4233d0272c20933d4ee5` |
| `oh-my-ztty-0.2.6-linux-x86_64.tar.gz` | 7,273,546 | `94a22ce1300a337e741ef0c2a336e29e90696b621fbdfa05c0b66673ce10dc20` |
| `oh-my-ztty-0.2.6-linux-x86_64.tar.gz.sha256` | 103 | `205da553db6ca352e158b754bb42d4e16788462c49f5673a1dfc98482d01def5` |
| `oh-my-ztty-0.2.6-linux-aarch64.tar.gz` | 7,011,427 | `b035c460e3444e7b33dda4e5dd25bceecf0757af40b095950adb8d0ad001637b` |
| `oh-my-ztty-0.2.6-linux-aarch64.tar.gz.sha256` | 104 | `1445105bc516ead983494c5663a3b8bae1ab0be1d2e412b77fbdc8bb8e91764b` |

## 开发机实际安装

正式安装器用 `--from` 读取已验的 x86_64 归档，沿用原有桌面偏好。安装与重装分别耗时 1.173 秒和 0.624 秒。`current` 由 0.2.5 切到 `releases/0.2.6-linux-x86_64`，重装保持同一链接 inode 和目标。新版的 126 项文件和六个源码提交均已复验。 [实际安装收据](actual-install.json)

0.2.5 目录的 119 项清单与原始归档对应，归档 SHA-256 为 `79d58efac183069e9d50701374fc76dc9938d96d69c9a58d35252a629129a388`。旧版回选已在隔离 HOME 验证。真实机器上的个人 profile、配置树中的链接、`~/.zshrc`、桌面偏好和外部命令链接通过了前后核对。独立的 pacman 包记录仍为 `oh-my-ztty-bin 0.2.5-1`。

| 套件内二进制 | 实际版本输出 | SHA-256 |
| --- | --- | --- |
| `ztty` | ztty 0.5.2 | `9e8f1c084376df913087c10d4b10d11e2c0172a2eb63a31e64813742067dab19` |
| `ssmcp` | ssmcp 0.10.20 | `434b6158bbb8e1ff12ffceb6bc0d703f20d368653c37b59ede2333a128bbfe2e` |
| `zfetch` | zfetch 0.1.1 | `5ddbf53b7ab7332b722883483825c27a3c316bb42c4624566e019b3fc3d0ef39` |

套件内 ztty 的 1,365,456 字节 ELF 与官方 `ztty-linux-x86_64.tar.gz` 中的成员完全一致；该上游归档 SHA-256 为 `a69a4df53b3856d57c3a6f5e9a2109cd7727e5a7f02be902f133a137b186546f`。套件构建器直接复制成员字节，只设置执行权限，不对 ELF 执行 strip 或内容规范化。另一条 `~/.cargo/bin/ztty` 是此前通过官方 registry 0.5.2、`wayland` feature 和 release profile 在本机构建的安装，大小为 1,367,376 字节，SHA-256 为 `0d697554c280ddc51631874d67a4ce729c709cce861d400e052e00e9f95b174a`。本次套件升级保留了它；两个入口分别记录来源与哈希。[固定构建器](https://github.com/LIghtJUNction/oh-my-ztty/blob/1e3ce8d3e5a141d09e450fd3f635f987a5732be4/scripts/build_bundle.py) · [Cargo 安装原始记录](https://github.com/LIghtJUNction/ztty/blob/76fa2cfd13b776c027d5a86fadafde8e035f88f2/docs/releases/0.5.2/report.zh-CN.md)

本机候选包 SHA-256 单独记录。x86_64 为 `73e5fd9872aaada8691159b8b7236f7d5b20e619370b708571d1887394f8d15e`，ARM64 为 `240afc3bf7fb1e0d04814fe0f70f9baa099d0d37292bea44da33cac47472adc3`。实际安装的是上表公开制品中的正式 x86_64 归档。

原生 exec PATH 和真实登录 Zsh 的裸 `ztty`、`ssmcp` 均命中 Cargo，回报 0.5.2 和 0.10.20，对应的二进制哈希一致。登录子进程带原有启动文件执行并以 0 退出。单独核对的外部链接 `~/.local/bin/ztty` 仍指向 `/usr/bin/ztty`，回报 ztty 0.5.0。三种环境都解析到受管 `omztty 0.2.6`。 [PATH 命令与指纹](actual-install.json)

用户 systemd manager 的 PATH 只在短子进程中重放。两个查询先命中 mise shim，先前的 `mise which` 均因工具未激活而返回 1。裸 `ztty --version` 和 `ssmcp --version` 均返回 0，分别输出 `ztty 0.5.0` 和 `ssmcp 0.10.20`。这记录了 shim 在未激活时的实际执行行为。沙箱拒绝 `ptrace`，最终委托的可执行文件及其 SHA-256 未确认。 [命令结果和追踪范围](actual-install.json)

登录核验后，`current`、0.2.5 目录、profile、启动文件和 Cargo 二进制仍与安装后基线一致。此次工作没有停止现有进程或连接。检查范围限于已记录的文件和短查询子进程，真实服务与连接的存活状态未测。此前曾因 ENOSPC 中断，恢复后的安装前检查有足够空间，空间恢复原因未核实。

## 报告副本

Drive 证据副本收录正式发行元数据、两个架构的 CI 原始结果与截图、开发机实际安装和 PATH 收据。 [发行与安装证据包](https://drive.google.com/file/d/15c79p02J6VqnXF2qnSYacMJOj7hp4-6E/view?usp=drivesdk) · [实际安装收据](actual-install.json)
