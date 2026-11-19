# oh-my-ztty

基于 Project Z 的 Linux 终端套件：**ztty + zsh + zshard + zdot + ssmcp**。

[官网](https://lightjunction.github.io/oh-my-ztty/) · [English](README.md) · [安装说明](docs/installation.md) · [性能记录](docs/performance.md)

## 安装

先下载并查看安装脚本，再执行：

```sh
curl -fLO https://github.com/LIghtJUNction/oh-my-ztty/releases/latest/download/install.sh
sh install.sh
~/.local/bin/omztty shell
```

支持 Linux x86_64、ARM64。系统需提供 zsh 5.9+；图形终端使用 X11/XWayland，正式构建在 Ubuntu 24.04 验证。安装包预装全部四个 Project Z 组件，按用户安装，可重复执行。

## 四个独立项目

| 项目 | 作用 |
| --- | --- |
| [ztty](https://github.com/LIghtJUNction/ztty) | 原生终端 |
| [zshard](https://github.com/LIghtJUNction/zshard) | 新写的 zsh 框架，提供补全、历史建议、语法高亮和延迟加载插件 |
| [zdot](https://github.com/LIghtJUNction/zdot) | `no_std` dotfiles 工具，先预览变更，再管理链接、备份冲突文件和显式 Git 同步 |
| [ssmcp](https://github.com/LIghtJUNction/ssmcp) | 按需把工作区接入 AI 的 MCP 工具 |

本仓库用 Git 子模块固定各组件版本。zsh 由系统包管理器安装。启动普通 shell 时无需运行额外的套件守护进程。

## 常用命令

```sh
omztty terminal        # 用 ztty 打开预设 shell
omztty shell           # 在当前终端体验
omztty doctor          # 检查组件和系统依赖
omztty ai context      # 输出明确选择的 shell 上下文
omztty ai connect      # 在当前工作区启动 ssmcp
omztty dot plan --root ~/dotfiles --target "$HOME"  # 预览配置变更
omztty update          # 更新整套发行版
omztty uninstall       # 卸载本套件管理的文件
```

AI 建议的命令先进入输入行，由人确认执行。安装器保留已有工具及登录 shell；套件使用自己的版本目录。

## 一起迭代

```sh
git clone --recurse-submodules https://github.com/LIghtJUNction/oh-my-ztty.git
cd oh-my-ztty
python3 scripts/workspace.py status
```

开发、测试和发布见 [CONTRIBUTING.md](CONTRIBUTING.md)。性能数字与测试条件见 [性能记录](docs/performance.md)。所有新项目采用 MIT 许可证。
