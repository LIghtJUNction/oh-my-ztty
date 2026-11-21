# Zuse 输入更新后的 bundle 来源与 CLI 验收（2026-11-21）

本轮 Linux x86_64 bundle 已完成首轮和最终两次真实四二进制 release 构建，两次临时 HOME/XDG smoke 均退出 0。最终归档采用修正后的 zdot Git 来源声明；首轮归档、日志与构建身份完整保留。源码提交、构建时根 HEAD、来源锁和归档哈希在下文分别记录。

## 1. 最终固定来源

suite 已保留并发 main `19a3bdbe48f6b7d4425191c1bc5db37407bc937e` 的 shell 管理与打包更新。SSMCP、ztty、zdot 均通过 `scripts/workspace.py sync <component>` 正式同步。最终一次仅将 zdot 从 `a3c6a75b1e66747822b9b69d9e046d2aac249210` 更新到 `f540adcd11a7ed56339895d3d52e0a9e5e3506c6`；其他五个组件来源记录逐字段保持不变。

zdot 的唯一源码变更是删除内部 Git 依赖 zclap 的 `version` 条件。zdot 包版本仍为 0.2.0，`Cargo.lock` 逐字节保持不变，zclap 仍锁定 `4d87f3ae3743e81509d5ac5500909955667c860f`。同步前后核对了已验证的公开默认 HEAD；另于 10:38:06 UTC 只读确认 zshard 默认 main 仍为下表提交。

所有组件的来源分支均为 `main`。两轮构建前后 `verify_sources` 均通过：六个组件 HEAD 与锁一致，递归子模块已初始化且源码干净，构建期间各自锁文件保持不变。两份归档内 `BUILD.json` 的六个提交分别与各自来源锁逐项核对。

| 组件 | 最终完整提交 |
| --- | --- |
| ztty | `dd4ea6f6f375761ddb5bfd126e68a40db8ab6a12` |
| ssmcp | `5f4a35482c6353750248ddee8761e5fd3daffad6` |
| zshard | `f7842f70e439c4abda2a46698f0ebe067d38b297` |
| zdot | `f540adcd11a7ed56339895d3d52e0a9e5e3506c6` |
| zrc | `995d22a2bde9722bfb6e817fb8303eaa6fd8f339` |
| zfetch | `f0614f3b76eca222f4b3880f8dd1707d1308f098` |

两轮递归 Git 子模块相同，路径相对于 `components/`：

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
| 合并后的 `make check`，复用既有结果 | 181 项测试全部通过；shell/zsh 语法与 Python 编译检查通过 | 101.433 秒，其中 unittest 为 100.967 秒 |
| 首轮正式 bundle 构建 | 四次 `cargo build --locked --release` 均成功 | 265.199 秒 |
| 首轮实际归档 smoke | 临时 HOME/XDG 安装与 CLI 生命周期通过 | 1.660 秒 |
| 最终正式 bundle 构建 | 同一共享 target 下四次构建均成功 | 4.041 秒 |
| 最终实际归档 smoke | 对最终归档重新执行并通过 | 1.593 秒 |

181 项检查在此前检查点执行，覆盖 shell/Python、临时 HOME、本地 Git 与模拟 CLI。此后 suite 产品与打包脚本没有变化，仅更新 gitlink、来源锁和报告，因此复用该结果。两轮真实 Rust 构建和归档 smoke 则各自实际执行；四个二进制是 ztty、ssmcp、zdot、zfetch，ztty 启用 `wayland`。

首轮构建于 10:24:15–10:28:40 UTC 执行，smoke 于 10:28:40–10:28:42 UTC 执行。最终构建于 10:38:47–10:38:51 UTC 执行，smoke 于 10:38:51–10:38:53 UTC 执行。以上是命令耗时。

smoke 使用归档中的真实二进制，验证重复安装的目标与链接 inode 保持稳定、交互 zsh、无历史/环境收集的本地 AI context、组件命令、zfetch boot-chain JSON、配置初始化幂等性、冲突拒绝、带备份采用、原内容恢复、自定义 XDG 路径、损坏标记拒绝和卸载。临时目录由夹具创建并清理。

## 3. 两份归档与各自构建身份

**首轮归档，已保留：** `dist/zuse-input-bundle/oh-my-ztty-0.2.6-linux-x86_64.tar.gz`，大小 **8,595,986 字节**。构建时根 HEAD 为 `ec7c9c6550e2b16bf7222a18b6b468baa3726573`，加上当时工作树中已同步的 ztty gitlink 与来源锁；该状态随后随首轮报告提交为 `aff323687b6a55d01f5da02f217d34d4643dca5c`。

```text
首轮归档 SHA256
ac66110bbfdc8a85b72a79c65e440fdb57697fd2760614f9889ec81265f2fbcc
首轮来源锁 SHA256
781ad768f37a9eaf3606ea411fc204ef8243ae595b0b42b38667cd0d527c6631
```

首轮 zdot 为 `a3c6a75b1e66747822b9b69d9e046d2aac249210`；其余五个组件与最终表相同。首轮锁更新时间为 10:24:04 UTC。

**最终归档：** `dist/zuse-input-bundle-final/oh-my-ztty-0.2.6-linux-x86_64.tar.gz`，大小 **8,595,996 字节**。构建时根 HEAD 为 `aff323687b6a55d01f5da02f217d34d4643dca5c`，加上当时工作树中已同步的 zdot `f540adcd` gitlink 与最终来源锁。最终锁更新时间为 10:38:41 UTC。

```text
最终归档 SHA256
57c14e4b0616c9c291c8a622d49924e8e2e1bcad63ec66119e5c008969276622
最终来源锁 SHA256
381ff21b5dde25be21583138fadcbe42388ead2a4e053739f57263e4549e61b4
```

两次构建时的根 HEAD、工作树状态和锁哈希分别来自各轮 `bundle-gate-summary.json`；`BUILD.json` 记录六组件 pins，不记录根仓库 HEAD。最终报告与 pin 的发布提交是之后形成的提交，不作为构建时 HEAD。

两个归档各自的 `.sha256` 文件与实测哈希一致。构建器从 Cargo 的产物消息中选择每个二进制、检查 ELF 架构并立即复制；归档内 `MANIFEST.sha256` 记录文件身份。两轮四个二进制的 SHA256 和字节数逐项相同，归档的来源记录与整体哈希不同。

| 二进制 | 两轮相同的字节数 |
| --- | ---: |
| ztty | 1,406,712 |
| ssmcp | 16,219,448 |
| zdot | 58,344 |
| zfetch | 58,120 |

## 4. 复现入口

两轮全部真实 Cargo 构建均持有同一外层 flock，使用显式共享 target 和离线缓存。以下为最终归档的标准入口，运行目录为 suite 工作树：

```sh
make check
CARGO_TARGET_DIR=/var/tmp/project-z-cargo-target CARGO_NET_OFFLINE=true \
  flock /var/tmp/project-z-cargo-target/.project-z-cargo-owner.lock \
  python3 -B scripts/build_bundle.py --arch x86_64 --output dist/zuse-input-bundle-final
python3 -B scripts/smoke_bundle.py \
  dist/zuse-input-bundle-final/oh-my-ztty-0.2.6-linux-x86_64.tar.gz
```

本轮记录器在同一锁文件上使用 `fcntl.flock(LOCK_EX)`，覆盖每轮完整四二进制构建。构建完成后释放锁，再对各自固定归档运行 smoke。首轮输出目录是 `dist/zuse-input-bundle`，其余标准入口相同。

## 5. 证据与验收范围

首轮证据目录为 `dist/suite-input-gate-yg_z6chk/`；最终证据目录为 `dist/suite-zdot-gate-20261121/`。原始日志 SHA256 如下：

```text
首轮 make-check.log
7f8e070c7f1e5612dce475dae0e4b96e7ef6ec5e75f7b7fdbd3fa5a477f203b7
首轮 bundle-build.log
50588b2af0acc4952b4f9d5abda3682c2ac62dd8b19653cf39b9ef985aafbbad
首轮 bundle-smoke.log
7f34e1696bbeba788898e7604f8d3673138bd0d2d48a2cd9f4199ab6d2d61a6b

最终 bundle-build.log
fabbc994978e450fe6c5d3cefa4a9ab320e4fb960a5f8d5896be8ebed1ef9d6f
最终 bundle-smoke.log
3522f9716299c2d4478349a1ca6b684f981947f30b691ddc8278a2a410f402eb
```

各轮的 `sync-*-summary.json`、`bundle-build-summary.json`、`bundle-smoke-summary.json`
与 `bundle-gate-summary.json` 分别记录默认分支观察、来源锁、命令、起止时间、退出码和产物身份。最终目录还保留 `zshard-default-observation.json` 与 `archive-comparison.json`。Git 提交保存 gitlink、来源锁与本文；两份归档、二进制和完整原始日志保留在 ignored `dist`。

smoke 验收范围是 bundle 的 CLI 与安装生命周期。GUI 渲染和原生输入验证属于独立上游验收，证据见固定来源的
[Zuse 验收报告](https://github.com/LIghtJUNction/zuse/blob/ac5713c2bfc3cc4848e89107cc1a6929ec48e2dc/docs/validation-20261121.md)
与
[SSMCP 输入集成报告](https://github.com/LIghtJUNction/ssmcp/blob/5f4a35482c6353750248ddee8761e5fd3daffad6/docs/zuse-input-20261121.md)。
两轮安装与卸载仅作用于 smoke 的临时 HOME；现有用户系统没有安装本候选产物。
