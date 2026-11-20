# oh-my-ztty

A lean Linux terminal setup built on Project Z: **ztty + zsh + zshard + zrc + zdot + zfetch + ssmcp**.

[Website](https://lightjunction.github.io/oh-my-ztty/) · [中文](README.zh-CN.md) · [Install guide](docs/installation.md) · [Performance](docs/performance.md) · [0.2.1 workstation report](docs/reports/workspace-0.2.1.md)

## Install

Download and inspect the installer, then run it:

```sh
curl -fLO https://github.com/LIghtJUNction/oh-my-ztty/releases/latest/download/install.sh
sh install.sh
~/.local/bin/omztty shell
```

Linux x86_64 and ARM64. Requires system zsh; the graphical terminal uses X11/fontconfig. The bundle includes the Project Z components and a native application configuration profile. Installation is per user and repeatable. Your login shell and existing tools remain available.

## The suite

| Component | Job |
| --- | --- |
| [ztty](https://github.com/LIghtJUNction/ztty) | Native terminal |
| [zshard](https://github.com/LIghtJUNction/zshard) | Original zsh framework: completion, suggestions, highlighting and lazy plugins |
| [zrc](https://github.com/LIghtJUNction/zrc) | Native Neovim and terminal-tool configuration with one warm Ink palette |
| [zdot](https://github.com/LIghtJUNction/zdot) | `no_std` dotfiles manager with plans, reversible links and explicit Git sync |
| [zfetch](https://github.com/LIghtJUNction/zfetch) | On-demand native system overview, zero crate dependencies |
| [ssmcp](https://github.com/LIghtJUNction/ssmcp) | On-demand MCP workspace connection for AI |

Each is a separate open-source repository, pinned here as a Git submodule. zsh is supplied by your Linux distribution.

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

One editable profile manages zsh, ztty, Neovim, Kitty, Foot, Ghostty, tmux, fzf, bat, ripgrep and Git display settings. Existing configurations are backed up by zdot. [Configuration and recovery](docs/configuration.md) explains the native editor, application coverage and file locations.

## Everyday commands

```sh
omztty terminal        # Open ztty with the suite's zsh configuration
omztty shell           # Try the shell in your current terminal
omztty info            # Native system overview
omztty doctor          # Check binaries and system dependencies
omztty ai context      # Emit explicit shell context
omztty ai connect      # Start ssmcp in your workspace
omztty dot plan --root ~/dotfiles --target "$HOME"  # Preview dotfile changes
omztty update          # Install the latest suite release
omztty uninstall       # Remove this installation's managed files
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
