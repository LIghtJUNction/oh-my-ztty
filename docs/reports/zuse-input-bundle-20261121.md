# Zuse 输入更新后的 bundle 来源与 CLI 验收（2026-11-21）

本轮 Linux x86_64 bundle 已完成四个真实二进制的 release 构建，以及新建临时 HOME/XDG 目录中的安装生命周期 smoke。构建和 smoke 的退出码均为 0；下文分别记录源码身份、执行结果和归档身份，原始证据保留在工作树的 ignored `dist` 目录。

## 1. 固定的源码

suite 的构建基线是 `ec7c9c6550e2b16bf7222a18b6b468baa3726573`，已合入并发 main `19a3bdbe48f6b7d4425191c1bc5db37407bc937e` 的 shell 管理与打包更新。随后通过 `scripts/workspace.py sync ztty` 更新 ztty gitlink 与来源锁；这两项更改与本文一同提交。SSMCP 也由同一工具的 `sync ssmcp` 路径同步，zrc 保留已验证的固定来源。

所有组件的来源分支均为 `main`。构建前后 `verify_sources` 均通过：六个组件 HEAD 与锁一致，递归子模块已初始化且源码干净；构建期间锁文件保持不变。归档内 `BUILD.json` 的六个提交也已逐项核对。

| 组件 | 完整提交 |
| --- | --- |
| ztty | `dd4ea6f6f375761ddb5bfd126e68a40db8ab6a12` |
| ssmcp | `5f4a35482c6353750248ddee8761e5fd3daffad6` |
| zshard | `f7842f70e439c4abda2a46698f0ebe067d38b297` |
| zdot | `a3c6a75b1e66747822b9b69d9e046d2aac249210` |
| zrc | `995d22a2bde9722bfb6e817fb8303eaa6fd8f339` |
| zfetch | `f0614f3b76eca222f4b3880f8dd1707d1308f098` |

最终 `dependencies.lock.json` 的 SHA256 为
`781ad768f37a9eaf3606ea411fc204ef8243ae595b0b42b38667cd0d527c6631`，
更新时间为 2026-11-21 10:24:04 UTC。递归 Git 子模块如下，路径相对于 `components/`：

| 子模块 | 完整提交 |
| --- | --- |
| ssmcp/crates/zharness | `fb2948f78467dd92b216aabda6f18a5645f0e7f6` |
| ssmcp/crates/zplugin | `592a1be623b81a775026c470e6f0efe91fcf78f3` |
| ssmcp/crates/ztuio | `9c632b30f7e2c2fd51a19b4bc5d90d529041ae7e` |
| ssmcp/crates/zuse | `ac5713c2bfc3cc4848e89107cc1a6929ec48e2dc` |
| ztty/crates/zgpui | `b4d5493e0cd985d00558c7be0b5726965ab5163a` |
| ztty/crates/zgraphics | `aa0ed19fb706ad147aff1df54c4ef762d918e864` |
| ztty/crates/zinput | `da22743e1ad16bedb79751c8e8bb71e63c45d197` |
| ztty/crates/zpty | `d263f9a8f0881d259e46c51a7b6753c61ab9be59` |
| ztty/crates/zterm | `fde08990612a8e8eb62dd90c664faab917214a8b` |

## 2. 实际执行的验收

| 验收 | 实测结果 | 命令耗时 |
| --- | --- | --- |
| 合并后的 `make check` | 181 项测试全部通过；shell/zsh 语法与 Python 编译检查通过 | 101.433 秒，其中 unittest 为 100.967 秒 |
| 正式 bundle 构建 | ztty、ssmcp、zdot、zfetch 四次 `cargo build --locked --release` 均成功；ztty 启用 `wayland` | 265.199 秒 |
| 实际归档 smoke | 临时 HOME/XDG 下安装、重复安装、doctor、CLI 与配置生命周期全部通过 | 1.660 秒 |

`make check` 覆盖同一套 suite 脚本，使用 shell/Python、临时 HOME、本地 Git 与模拟 CLI；它在最终 ztty pin 同步前执行。随后只更新了 ztty gitlink 和来源锁，真实 Rust 构建与归档 smoke 使用上表的最终六个来源。构建于 10:24:15–10:28:40 UTC 执行，smoke 于 10:28:40–10:28:42 UTC 执行。

smoke 使用归档中的真实二进制，验证重复安装的目标与链接 inode 保持稳定、交互 zsh、无历史/环境收集的本地 AI context、组件命令、zfetch boot-chain JSON、配置初始化幂等性、冲突拒绝、带备份采用、原内容恢复、自定义 XDG 路径、损坏标记拒绝和卸载。临时目录由测试夹具创建并清理。

## 3. 归档身份

产物为 `dist/zuse-input-bundle/oh-my-ztty-0.2.6-linux-x86_64.tar.gz`，大小 **8,595,986 字节**，SHA256：

```text
ac66110bbfdc8a85b72a79c65e440fdb57697fd2760614f9889ec81265f2fbcc
```

同目录的 `.sha256` 文件与实测归档哈希一致。构建器从 Cargo 的产物消息中选择每个二进制，检查 ELF 架构并立即复制到打包目录；归档内 `MANIFEST.sha256` 记录每个文件，`BUILD.json` 记录来源。下表大小来自实际归档成员：

| 二进制 | 字节数 |
| --- | ---: |
| ztty | 1,406,712 |
| ssmcp | 16,219,448 |
| zdot | 58,344 |
| zfetch | 58,120 |

## 4. 复现入口

本轮全部真实 Cargo 构建持有同一外层 flock，使用显式共享 target 和离线缓存。以下命令与本轮调用的标准入口一致；运行目录为 suite 工作树：

```sh
make check
CARGO_TARGET_DIR=/var/tmp/project-z-cargo-target CARGO_NET_OFFLINE=true \
  flock /var/tmp/project-z-cargo-target/.project-z-cargo-owner.lock \
  python3 -B scripts/build_bundle.py --arch x86_64 --output dist/zuse-input-bundle
python3 -B scripts/smoke_bundle.py \
  dist/zuse-input-bundle/oh-my-ztty-0.2.6-linux-x86_64.tar.gz
```

本轮记录器在同一锁文件上使用 `fcntl.flock(LOCK_EX)`，覆盖完整四二进制构建。构建完成后释放锁，再对固定归档运行 smoke。这里的耗时是命令完成时间；归档哈希标识本次输出字节。

## 5. 证据与验收范围

完整日志和机器可读记录保留于 `dist/suite-input-gate-yg_z6chk/`。日志 SHA256 如下：

```text
make-check.log
7f8e070c7f1e5612dce475dae0e4b96e7ef6ec5e75f7b7fdbd3fa5a477f203b7

bundle-build.log
50588b2af0acc4952b4f9d5abda3682c2ac62dd8b19653cf39b9ef985aafbbad

bundle-smoke.log
7f34e1696bbeba788898e7604f8d3673138bd0d2d48a2cd9f4199ab6d2d61a6b
```

`sync-ssmcp-summary.json`、`sync-ztty-summary.json`、`make-check-summary.json`、
`bundle-build-summary.json`、`bundle-smoke-summary.json` 与 `bundle-gate-summary.json`
分别记录默认分支观察、来源锁、命令、起止时间、退出码和产物身份。Git 提交保存 gitlink、来源锁与本文；二进制、归档和完整原始日志保留在 ignored `dist`。

本次 smoke 验收的是 bundle 的 CLI 与安装生命周期。GUI 渲染和原生输入验证属于独立上游验收，证据见固定来源的
[Zuse 验收报告](https://github.com/LIghtJUNction/zuse/blob/ac5713c2bfc3cc4848e89107cc1a6929ec48e2dc/docs/validation-20261121.md)
与
[SSMCP 输入集成报告](https://github.com/LIghtJUNction/ssmcp/blob/5f4a35482c6353750248ddee8761e5fd3daffad6/docs/zuse-input-20261121.md)。
本轮安装与卸载仅作用于 smoke 的临时 HOME；现有用户系统没有安装本候选产物。
