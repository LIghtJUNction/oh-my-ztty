# Installation

The release bundle includes ztty, zshard, zrc, zdot, zfetch, ssmcp and zmem. Installation and existing configuration commands from a release do not require Rust or Python. The optional completion manager requires Python 3.11 or newer. Install system zsh 5.9 or newer first.

The suite window runs on X11 or XWayland. The pinned ztty 0.5.2 executable links X11, Xrender, Xft, Fontconfig, Wayland, xkbcommon, FreeType, HarfBuzz, EGL and GLES. These runtime libraries are required even when you select the X11 backend.

ztty 0.5.2 and ssmcp 0.10.20 require glibc 2.34 or newer and libgcc on both architectures. zdot is static. The release workflow targets Ubuntu 24.04 for validation.

Using the editor profile requires Neovim 0.11 or newer, installed separately. The configuration commands do not install applications or language servers.

On Ubuntu 24.04, install the system dependencies with:

```sh
sudo apt-get install zsh git curl libx11-6 libxrender1 libxft2 libfontconfig1 \
  libwayland-client0 libwayland-egl1 libwayland-cursor0 libxkbcommon0 \
  libfreetype6 libharfbuzz0b libegl1 libgles2 libgcc-s1
```

## Arch Linux (AUR)

Install the [oh-my-ztty-bin package](https://aur.archlinux.org/packages/oh-my-ztty-bin) with an AUR helper:

```sh
yay -S oh-my-ztty-bin
omztty doctor
```

With Git and Arch's `base-devel` tools installed, you can also build the package directly:

```sh
git clone https://aur.archlinux.org/oh-my-ztty-bin.git
cd oh-my-ztty-bin
makepkg -si
```

This package uses prebuilt release binaries. Runtime and existing configuration commands need no Rust or Python. Use Python 3.11 or newer for `omztty completion`. Use your AUR helper to upgrade it; the system package manager owns installed files. Adopt the home profile explicitly with the commands below. After upgrading an adopted profile, run `omztty config refresh` to bring forward unchanged defaults.

Restore adopted configurations before removing the package:

```sh
omztty config remove
sudo pacman -R oh-my-ztty-bin
```

## Install a release

The installer manages a per-user terminal suite and, by default, its independent system memory service.

```sh
curl -fLO https://github.com/LIghtJUNction/oh-my-ztty/releases/latest/download/install.sh
sh install.sh
~/.local/bin/omztty doctor
~/.local/bin/omztty shell
```

Read the downloaded script before executing it. It downloads the bundle for your Linux architecture, checks its SHA-256 and content manifest, and installs under `${XDG_DATA_HOME:-$HOME/.local/share}/oh-my-ztty`. Linux x86_64 and aarch64 are supported.

The default command directory is `~/.local/bin`. Use `--bin-dir /absolute/path` to select another directory. Add your command directory to PATH if it is not already there.

A new installation creates a desktop entry by default. Use `--no-desktop` to disable it or `--desktop` to enable it. Repeat installations and updates reuse the last successful choice when neither option is supplied. Disabling an existing installation removes only desktop links that still point to this suite; replacement files and foreign links are preserved. Enabling the entry stops if an unrelated file or link already occupies its path.

An unrelated `omztty` executable causes installation to stop. Other existing tools, including ztty and ssmcp, are preserved; `omztty` selects its bundled tools explicitly.

## System memory manager

The release installer enables zmem by default using sudo. zmem adopts existing Swap, installs a root-owned executable at `/usr/local/bin/zmem`, and keeps the system policy in `/etc/zmem/zmem.conf`. Existing configuration is preserved during upgrades.

```sh
omztty memory status --json --processes
omztty memory plan --json
omztty memory run --class background -- cargo build
```

For a per-user-only install or a machine without systemd, run `sh install.sh --no-memory-manager`. This skips system setup and remembers the choice on subsequent updates. It leaves an existing manager running. `omztty memory setup` enables the bundled zmem immediately; `omztty update --memory-manager` also records the choice for future updates.

Use `omztty memory rollback` to restore the previous managers and configuration. The system service remains installed when the per-user terminal suite is removed; its independent recovery command is `sudo /usr/local/bin/zmem rollback`.

See [memory policy and recovery](../site/content/memory.md) for defaults, workload classes and AI output.

## Try the environment

```sh
omztty shell
omztty terminal
```

The first command starts a shell in the current terminal. The second opens ztty with that same environment. These commands try the preset in a separate shell session. Use the explicit home-adoption steps below to make it the default configuration; account login-shell records remain unchanged.

The terminal launcher uses a suite-specific ztty broker socket, `@oh-my-ztty-<uid>-<suite-version>`. Set `OMZTTY_SOCKET` to select another socket explicitly. The terminal uses ztty's resident broker; starting `omztty shell` alone does not start a terminal or AI daemon.

Inside the preset shell, `zai context` produces a small context record for AI tools. `zai connect` starts ssmcp in the current directory. Configure and authenticate ssmcp using its own instructions. Merely starting the shell creates no remote connection.

## Adopt the default workspace

```sh
omztty config init
omztty config plan --json
omztty config apply --backup
omztty config status
```

The editable profile covers zsh, ztty, Neovim, Kitty, Foot, Ghostty, tmux, fzf, bat, ripgrep and Git display settings. Existing files are backed up before deployment when `--backup` is supplied. Git display colors use the explicit include described in [configuration](configuration.md); identity and signing remain in the user's Git configuration.

Open a new terminal after adoption. The profile lives under `${XDG_CONFIG_HOME:-$HOME/.config}/oh-my-ztty/profile`; its journal and backups live under `${XDG_STATE_HOME:-$HOME/.local/state}/zdot/oh-my-ztty`. HOME adoption requires an absolute `XDG_CONFIG_HOME` within HOME. Roots outside HOME are refused.

Repeated `config init` and suite updates preserve the editable profile. After upgrading, run `omztty config refresh` to update files that still match their shipped defaults. Custom edits, added files and deliberately removed files are preserved. Use `omztty config remove` to restore the saved originals, or `omztty config audit` to inspect managed files and known legacy framework locations. See [configuration and recovery](configuration.md) for application coverage and local extensions.

## System overview

Run `omztty info` to display the system overview through bundled zfetch, or use `omztty zfetch` to invoke it directly. The shell does not run zfetch automatically.

The standalone Arch Linux package names are `zfetch-project-z` and `zfetch-project-z-bin`. Consult the [zfetch repository](https://github.com/LIghtJUNction/zfetch) for publication status and installation details.

## Ink appearance

The default Ink preset uses a warm graphite background, linen text and copper accents, a complete ANSI palette, 28 px padding and a 13 pt font request. Fontconfig tries installed JetBrains Mono, JetBrainsMono Nerd Font, Caskaydia Mono, Cascadia Mono and ordinary monospace in that order. The prompt does not require private-use icon glyphs. Personal Fontconfig rules may change the selected family.

The two-line prompt separates the path and cached Git branch from command input. It shows a nonzero exit code and commands lasting at least two seconds. Its theme callback uses zsh builtins only.

To use zshard's own minimal prompt, put `OMZTTY_THEME=framework` in `options.zsh`. To install a custom prompt, register it with `zshard theme YOUR_FUNCTION` in `local.zsh`; that file is loaded after Ink. See the [theme API](https://github.com/LIghtJUNction/zshard/blob/v0.2.0/docs/plugins.md).

## Personal configuration and plugins

Create configuration below `${XDG_CONFIG_HOME:-$HOME/.config}/oh-my-ztty`. The suite reads two optional files:

| File | Loaded when | Intended use |
| --- | --- | --- |
| `options.zsh` | Before framework initialization | Startup options such as `ZSHARD_KEYMAP=vi` or `ZSHARD_COMPLETION=eager` |
| `local.zsh` | After framework initialization | Aliases, plugin loading, themes and the `ZSHARD_AI_COMMAND` provider argv array |

Both files remain outside the installed release and survive upgrades and uninstallation. Personal completion files belong in `${XDG_CONFIG_HOME:-$HOME/.config}/oh-my-ztty/completions/`, which the preset adds to `fpath` for on-demand loading; that directory is also retained. To try the included example plugin, add this to `local.zsh`:

```zsh
zshard load "$ZSHARD_HOME/examples/hello.plugin.zsh"
```

For remote plugins, install a reviewed full Git commit explicitly, then put `zshard use NAME` in `local.zsh`. [The plugin guide](https://github.com/LIghtJUNction/zshard/blob/main/docs/plugins.md) documents locking, restoration, lazy loading, hooks and themes.

Configure an installed AI provider's executable and arguments as the `ZSHARD_AI_COMMAND` array in `local.zsh`, then use `zai ask` inside the preset shell or `omztty ai ask` from another shell. The provider receives the context and request on standard input. Its output is displayed, without automatic command evaluation. The `context` and `connect` subcommands remain independent of that provider configuration.

## Offline installation

Download the archive and its matching `.sha256` file from the same published release. The following example uses the x86_64 archive for [v0.2.6](https://github.com/LIghtJUNction/oh-my-ztty/releases/tag/v0.2.13) once that release is published.

```sh
sh install.sh --from ./oh-my-ztty-0.2.13-linux-x86_64.tar.gz
```

Use the aarch64 archive on ARM64. An explicit `--sha256 HEX` can replace the sidecar file when the digest has already been obtained from the release record.

## Updates and repeat installation

For a per-user installation:

```sh
omztty update
```

If you adopted a home profile, run `omztty config refresh` after updating to receive changes to unmodified defaults. Upgrade the AUR package through your AUR helper.

To change the desktop entry choice during an update:

```sh
omztty update --no-desktop
omztty update --desktop
```

For installations created by v0.1.1 or older, the first successful installation with this installer infers the choice from the existing desktop-entry record: present means enabled, absent means disabled. Either explicit option overrides that choice. The installer saves the preference after installation succeeds; failed preparation leaves the previous choice intact.

Each version has its own directory; a `current` symlink chooses the active one. Completion caches also use the immutable release directory name, so upgrades and rollback use their matching inputs. Before changing that link, the installer prepares an audited completion cache using the system functions, zshard and suite completions. The first Tab can reuse that cache. Changing completion paths or plugins causes normal revalidation. A failed preparation leaves the previously active version selected. Installing the same archive again verifies the existing installation. If an installed version's files were modified, the installer preserves them and reports the conflict.

## Dotfiles

Create a dotfile directory and profile (this does not initialize Git):

```sh
omztty dot init --root "$HOME/dotfiles"
```

Place managed files in that repository and add source/destination mappings to `profile.zdot`. Then preview and apply:

```sh
omztty dot plan --root "$HOME/dotfiles" --target "$HOME"
omztty dot apply --root "$HOME/dotfiles" --target "$HOME"
```

Conflicts stop by default. Read [zdot's documentation](https://github.com/LIghtJUNction/zdot) before selecting its explicit backup or Git-sync commands.

## Uninstall

For a per-user installation:

```sh
omztty uninstall
```

The uninstaller first restores the adopted `omztty config` home profile, including originals saved by `apply --backup`. If restoration fails or the deployment records are inconsistent, it preserves the installed runtime for recovery. After successful restoration it removes the installation and suite-owned links.

Personal profiles, shell additions, completion files and history remain outside the runtime and are preserved. Independent repositories deployed through `omztty dot` keep their separate lifecycle; use their `zdot remove` command first if you also want to restore those deployments.
