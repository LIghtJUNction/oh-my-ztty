# A working terminal setup for Linux

oh-my-ztty gives Linux developers a configured zsh shell and a terminal to run it in. Open a session to get a directory and Git-branch prompt, Tab completion, history suggestions and command highlighting.

Use the shell in your current terminal or open the included ztty window. An optional application profile adds matching Neovim and terminal-tool settings, which you can edit as ordinary configuration files.

The current suite release is **0.2.11** once its Linux x86_64 and ARM64 bundles are published. The quick start uses the latest published installer.

## Quick start

Install zsh 5.9 or newer and the [required system libraries](installation.md#requirements), then download and run the per-user installer:

```sh
curl -fLO https://github.com/LIghtJUNction/oh-my-ztty/releases/latest/download/install.sh
sh install.sh
~/.local/bin/omztty shell
```

This opens the configured shell in your current terminal. Type `exit` to return to your previous session. Run `~/.local/bin/omztty terminal` to open a new ztty window.

The installer keeps the terminal runtime in your account's data directory and enables zmem as the system memory manager using sudo. Use `--no-memory-manager` when system setup is not needed. Your login shell stays as it is; adopting application configuration is a separate step. The [installation guide](installation.md) covers dependencies, offline installation and the [Arch Linux package](installation.md#arch-linux-aur).

## What you can use

| For daily work | Included support |
| --- | --- |
| Work in the shell | A prompt with your directory and Git branch, command completion, history suggestions and first-command highlighting |
| Edit code | An optional Neovim profile with file search, a shortcut panel, diagnostics and support for installed language servers |
| Keep a consistent setup | Editable profiles for zsh, ztty, Neovim and everyday terminal tools, with backups when you adopt them |
| Work with an AI client | Commands to inspect local context, connect the current workspace and put proposed commands into the editing buffer |
| Manage memory pressure | zmem as the default system manager, with Swap policy, background scopes and JSON status |

Neovim and other applications are installed separately. The suite supplies their configuration. AI connections and provider requests start when you invoke them.

## Adopt the application profile

To use the included application settings, create a profile and inspect its plan before applying it:

```sh
omztty config init
omztty config plan
omztty config apply --backup
```

The profile lives under `~/.config/oh-my-ztty/profile` by default. Edit its files to suit your workflow. After a suite update, `omztty config refresh` updates defaults you have left unchanged and preserves your edits. See [configuration](configuration.md) for the Neovim keys, shell options and how to restore your previous files.

## How it fits together

| Component | Its part in the setup |
| --- | --- |
| [ztty](https://github.com/LIghtJUNction/ztty) | Opens terminal windows and runs shell sessions |
| [zshard](https://github.com/LIghtJUNction/zshard) | Adds the prompt, completion, suggestions, highlighting and plugins to system zsh |
| [zrc](https://github.com/LIghtJUNction/zrc) | Supplies native configuration files for the editor and terminal tools |
| [zdot](https://github.com/LIghtJUNction/zdot) | Links configuration files into place, saves originals and restores them |
| [zfetch](https://github.com/LIghtJUNction/zfetch) | Shows system information when you run `omztty info` |
| [ssmcp](https://github.com/LIghtJUNction/ssmcp) | Connects an AI client to a workspace on request |
| [zmem](https://github.com/LIghtJUNction/zmem) | Manages system memory pressure and Swap, with an AI-readable interface |

The source lock records the exact component commits selected for each suite release. The [release page](https://github.com/LIghtJUNction/oh-my-ztty/releases/latest) provides published bundles and checksums. See [configuration](configuration.md#completion) for completion behavior.

## Next steps

- [Configure the shell and editor](configuration.md).
- [Manage memory and Swap](memory.md).
- [Load a shell plugin](plugins.md).
- [Manage your own dotfile repository](dotfiles.md).
- [Connect an AI client or provider](ai.md).
- [Read the architecture](architecture.md) or [inspect the measured performance](performance.md).
