# Overview

oh-my-ztty assembles a terminal, a zsh framework, a native application configuration framework, a dotfile manager, a native system overview and an MCP client into one versioned Linux environment. System zsh runs your commands; the suite supplies the configuration and the tools around it.

The current suite release is **0.2.3**, available for Linux x86_64 and ARM64.

## Quick start

Install system zsh 5.9 or newer and the terminal's [system dependencies](installation.md#requirements). Download and inspect the installer, then run it:

```sh
curl -fLO https://github.com/LIghtJUNction/oh-my-ztty/releases/latest/download/install.sh
sh install.sh
~/.local/bin/omztty shell
```

This opens the preset shell in your current terminal. Use `~/.local/bin/omztty terminal` to open it in ztty.

Installation is per user. The suite keeps its runtime in a separate directory. Use `omztty config init`, inspect `omztty config plan`, then run `omztty config apply --backup` to adopt the native application profile. Account login-shell records remain unchanged.

## What's included

| Component | Pinned version | Responsibility |
| --- | --- | --- |
| [ztty](https://github.com/LIghtJUNction/ztty) | 0.4.1 | Terminal window, rendering and PTY |
| [zshard](https://github.com/LIghtJUNction/zshard) | 0.2.0 | Prompt, completion, suggestions, highlighting and plugins |
| [zrc](https://github.com/LIghtJUNction/zrc) | 0.1.0 | Native editor and terminal-tool profiles |
| [zdot](https://github.com/LIghtJUNction/zdot) | 0.2.0 | Dotfile plans, managed links, backups and Git sync |
| [zfetch](https://github.com/LIghtJUNction/zfetch) | 0.1.0 | Native system overview on request |
| [ssmcp](https://github.com/LIghtJUNction/ssmcp) | 0.10.10 | An explicit MCP connection to your workspace |

Each component has its own repository and release. Git submodules record the exact source revisions used by the suite.

## How it fits together

The prompt and editing features run inside zsh. Completion initializes when needed, using a cache prepared during installation and checked against the current completion inputs.

Dotfile management and AI connections are explicit commands. Opening a shell does not start a model or connect to a remote service. A ztty window uses ztty's resident broker; detached terminal sessions may outlive the window.

## Next steps

- [Install and check the environment](installation.md).
- [Keep personal options and aliases](configuration.md).
- [Load a plugin](plugins.md) or [manage dotfiles](dotfiles.md).
- [Set up AI integration](ai.md).
- [Read the measurements](performance.md) and their scope.

The [0.1.1 release report](https://github.com/LIghtJUNction/oh-my-ztty/blob/main/docs/reports/release-0.1.1.md) records source pins, public download checks and both native architecture validations.
