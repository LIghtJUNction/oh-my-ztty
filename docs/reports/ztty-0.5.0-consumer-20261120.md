# ztty 0.5.0：套件消费候选验收

候选源码为 [5a99afc170dc51455beb1491e04ab76cf18f4564](https://github.com/LIghtJUNction/oh-my-ztty/commit/5a99afc170dc51455beb1491e04ab76cf18f4564)。两架构包已使用正式 ztty 附件组装并核验，x86_64 完成真实安装生命周期和私有图形验收。套件 VERSION 保持 0.2.1；这些是未发布的私有候选，既有正式 0.2.1 附件、开发机安装和默认终端保持原样。[执行原件](ztty-0.5.0-consumer-20261120/acceptance.json) · [清理回执](ztty-0.5.0-consumer-20261120/closure.json)

## 来源与兼容改动

ztty 固定正式 [v0.5.0](https://github.com/LIghtJUNction/ztty/releases/tag/v0.5.0) 的 `c4f8f48c9598284a589e609f25242b49ceabfea8`，发行流程为 [44668398577](https://github.com/LIghtJUNction/ztty/actions/runs/44668398577)。原 `workspace.py pin` 完成稳定发布、双架构摘要和递归子模块检查，再同步 gitlink 与锁。[pin 原件](ztty-0.5.0-consumer-20261120/pin.json)

新参数 `--backend` 和 `--text-plugin` 各消费一个值。启动器同步参数数量，使只有选项的调用继续追加预设 zsh，同时保留空格、重复插件、显式命令边界和缺失值诊断。该兼容改动独立提交为 [86bbbe3](https://github.com/LIghtJUNction/oh-my-ztty/commit/86bbbe3a54b62a1beffbc3f4596a9338b8ef7530)。

SSMCP 仍为 0.10.10，其他五个组件源码未变。zdot、zfetch 复用正式 suite 0.2.1 的同源码二进制；两份原包各 84 个 MANIFEST 文件先完整核验。本次没有编译 Rust。

## 验收与边界

| 门槛 | 结果与实际范围 |
|---|---|
| `make check` | 42 项通过，含安装夹具和 stub ztty 的 argv 转发。[原始日志](ztty-0.5.0-consumer-20261120/local-check.log) |
| 两架构 `build_bundle.py` | 均 exit 0；每包 84 文件摘要通过，ztty ELF 与正式附件字节相同 |
| x86_64 `smoke_bundle.py` | 原脚本通过：重复安装、doctor、实际 zsh、本地 AI context、组件命令、配置冲突/备份、幂等应用、损坏标记拒绝、恢复及卸载。[原始日志](ztty-0.5.0-consumer-20261120/smoke.log) |
| x86_64 `verify_graphical.py` | 原四项检查通过：实际窗口、键盘命令、首次 Tab 后 shell 可用、真实组件版本；PTY 为 100×28，补全缓存摘要与 mtime 均复用。[原始 JSON](ztty-0.5.0-consumer-20261120/graphical.json) |
| 新 backend 的真实路径 | 同一次启动补入 `--backend x11`；私有 `SHELL=/bin/sh` 下，实际子进程仍为 `/usr/bin/zsh`。[适配回执](ztty-0.5.0-consumer-20261120/adapter.json) |

原图形脚本及断言未改动。ignored 适配器只补入上述启动参数，并使用 ztty 已验证的高号 Xvfb ownership helper。HOME、runtime、D-Bus、broker 均私有；`LIBGL_ALWAYS_SOFTWARE=1` 下，实际窗口属性为 `software`。

ARM64 本次仅核验组装、ELF 和清单，没有运行验收。`--text-plugin` 仅做套件 argv 转发检查；本次未扩跑插件执行或 Wayland GUI。上游宿主证据保留原源码身份。图形原件中的单次启动样本仅作诊断，不用于性能比较。

[私有 Xvfb 中使用正式 ztty 0.5.0 的实际套件候选（截图归档）](https://github.com/LIghtJUNction/oh-my-ztty/releases/download/v0.2.6/oh-my-ztty-generated-evidence-20261121.tar.gz)

## 私有包与清理

包名保留 VERSION 0.2.1，以候选源码和摘要区分。与正式旧套件相比，两包清单中变化的文件均只有 `BUILD.json`、`bin/omztty`、`bin/ztty` 和 `dependencies.lock.json`。

| 架构 | 字节数 | 私有候选 SHA-256 |
|---|---:|---|
| x86_64 | 5,471,368 | `870c49759625a918ea0b36572beb05c2110c73e497c13a5b1f2c61f3415da476` |
| aarch64 | 5,246,367 | `bc957976e1e23850ec8a726094bfa1a4f9342551d50fb9d3209fdb4f005d75c8` |

新锁 SHA-256 为 `8a547dade3a73ce7cac9840d44be910be90adb3e9388f6e95c25116206ad794c`。两包 BUILD、正式 ztty 附件和 ELF 摘要均保存在执行原件。

两个组装阶段、一次 smoke、一次 GUI 顺序执行，共 23.236 秒，无重试。单元上限 768 MiB、Swap 0、一个 CPU 配额、Nice 10；整个验收单元峰值为 456,372,224 字节，Swap 和 OOM 均为零。

三个自有单元均 inactive/dead、MainPID 0；验收 cgroup 已消失。subreaper 收集两条自有子进程退出记录，未留下已收养子进程。私有 Xvfb 已关闭，原显示端点与已安装终端入口检查值保持不变；主树仍为干净的 740b82f。

本目录执行、pin、本地检查、图形、适配及清理 JSON/日志保留原字节；`ownership.json` 仅公开自有显示结果和原件摘要，完整原显示端点快照保留本机。执行器及适配源码在 `harness/`，摘要见 [files.sha256.json](ztty-0.5.0-consumer-20261120/files.sha256.json)。私有包保留于本机 ignored `dist/consumer-ztty-0.5.0-20261120/acceptance-v050/bundles/`。

本分支交给 LIghtJUNction/oh-my-ztty 现有维护者接收合并；套件版本决策、正式发行和用户安装升级仍由该维护者继续处理。
