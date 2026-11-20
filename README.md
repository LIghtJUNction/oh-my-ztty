# oh-my-ztty

A lean Linux terminal setup built on Project Z: **ztty + zsh + zshard + zrc + zdot + zfetch + ssmcp**.

[Website](https://lightjunction.github.io/oh-my-ztty/) · [中文](README.zh-CN.md) · [Install guide](docs/installation.md) · [Performance](docs/performance.md) · [0.2.1 workstation report](docs/reports/workspace-0.2.1.md)

## Install

### Per-user release

Download and inspect the installer, then run it:

```sh
curl -fLO https://github.com/LIghtJUNction/oh-my-ztty/releases/latest/download/install.sh
sh install.sh
~/.local/bin/omztty shell
```

Linux x86_64 and ARM64. Requires system zsh; the graphical terminal uses X11/fontconfig. The bundle includes the Project Z components and a native application configuration profile. Installation is per user and repeatable. Your login shell and existing tools remain available. Runtime and configuration commands need no Rust or Python.

### Arch Linux (AUR)

Install the [oh-my-ztty-bin package](https://aur.archlinux.org/packages/oh-my-ztty-bin) with an AUR helper:

```sh
yay -S oh-my-ztty-bin
omztty doctor
```

Use your AUR helper to upgrade the system package. Configuration adoption remains explicit through the commands below. Before removing the package, run `omztty config remove` to restore adopted configurations, then remove it with your package manager. [Installation guide](docs/installation.md#arch-linux-aur) includes the `makepkg` route.

## The suite

| Component | Job |
| --- | --- |
| [ztty 0.5.2](https://github.com/LIghtJUNction/ztty/tree/v0.5.2) | Native terminal |
| [zshard](https://github.com/LIghtJUNction/zshard) | Original zsh framework: completion, suggestions, highlighting and lazy plugins |
| [zrc 0.1.2](https://github.com/LIghtJUNction/zrc/tree/v0.1.2) | Native Neovim and terminal-tool configuration with one warm Ink palette |
| [zdot](https://github.com/LIghtJUNction/zdot) | `no_std` dotfiles manager with plans, reversible links and explicit Git sync |
| [zfetch 0.1.1](https://github.com/LIghtJUNction/zfetch/tree/v0.1.1) | On-demand native system overview, zero crate dependencies |
| [ssmcp 0.10.20](https://github.com/LIghtJUNction/ssmcp/tree/v0.10.20) | On-demand MCP workspace connection for AI |

These are the component versions selected for oh-my-ztty 0.2.6. The suite records their source revisions as Git submodules. Your Linux distribution supplies zsh. See the [completion reference](docs/completions.md) for command and version coverage.

## Ink preset

A warm graphite, linen and copper palette, generous spacing and a two-line prompt with the path, cached Git branch and command status. The prompt uses zsh builtins; installed fonts fall back through Fontconfig. [Customize the preset](docs/installation.md#ink-appearance).

![The native Ink editor running in ztty](docs/reports/workspace-0.2.1/nvim-home.jpg)

Actual deployed configuration photographed on an isolated display. The documented workstation's real desktop launch chain was verified separately with a new suite broker, program execution and broker reuse; its default entry is now oh-my-ztty. See the [report, recovery history and acceptance scope](docs/reports/workspace-0.2.1.md).

## Make it your default workspace

~~~sh
omztty config init
omztty config plan --json
omztty config apply --backup
~~~

One editable profile manages zsh, ztty, Neovim, Kitty, Foot, Ghostty, tmux, fzf, bat, ripgrep and Git display settings. Existing configurations are backed up by zdot. After upgrading, run `omztty config refresh` to update defaults you have not changed; your edits and deliberately removed files are preserved. [Configuration and recovery](docs/configuration.md) explains the native editor, application coverage and file locations.

## Everyday commands

```sh
omztty terminal        # Open ztty with the suite's zsh configuration
omztty shell           # Try the shell in your current terminal
omztty info            # Native system overview
omztty doctor          # Check binaries and system dependencies
omztty ai context      # Emit explicit shell context
omztty ai connect      # Start ssmcp in your workspace
omztty dot plan --root ~/dotfiles --target "$HOME"  # Preview dotfile changes
omztty update          # Update a per-user installation
omztty uninstall       # Restore configs and remove a per-user installation
```

AI-generated commands are reviewed in the shell input line before execution. The suite does not start an AI model or resident agent at shell startup.

## Develop together

```sh
git clone --recurse-submodules https://github.com/LIghtJUNction/oh-my-ztty.git
cd oh-my-ztty
python3 scripts/workspace.py status
```

[Development and release guide](CONTRIBUTING.md) covers local checks, component updates and one-command version bumps. [Architecture](docs/architecture.md) describes the runtime boundaries and extension interfaces.

MIT license. Performance claims and their measurement conditions belong together; see [the benchmark record](docs/performance.md).
