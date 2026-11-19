# Installation

The release bundle includes ztty, ssmcp, zdot and zshard. Install system zsh 5.9 or newer first. The graphical terminal uses X11/XWayland and needs X11, Xrender, Xft and their fontconfig dependencies. The x86_64 bundle requires glibc 2.34 or newer and libgcc. Formal release validation targets Ubuntu 24.04; the ABI floor alone does not certify every distribution.

On Ubuntu 24.04, install the system dependencies with:

```sh
sudo apt-get install zsh git curl libx11-6 libxrender1 libxft2 libfontconfig1
```

## Install a release

```sh
curl -fLO https://github.com/LIghtJUNction/oh-my-ztty/releases/latest/download/install.sh
sh install.sh
~/.local/bin/omztty doctor
~/.local/bin/omztty shell
```

Read the downloaded script before executing it. It downloads the bundle for your Linux architecture, checks its SHA-256 and content manifest, and installs under `${XDG_DATA_HOME:-$HOME/.local/share}/oh-my-ztty`. Linux x86_64 and aarch64 are supported.

The default command directory is `~/.local/bin`. Use `--bin-dir /absolute/path` to select another directory and `--no-desktop` to omit the desktop entry. Add your command directory to PATH if it is not already there.

An unrelated `omztty` executable causes installation to stop. Other existing tools, including ztty and ssmcp, are preserved; `omztty` selects its bundled tools explicitly.

## Try the environment

```sh
omztty shell
omztty terminal
```

The first command starts a shell in the current terminal. The second opens ztty with that same environment. The suite supplies its own zsh configuration directory; your account's login shell and original `.zshrc` remain available.

The terminal launcher uses a suite-specific ztty broker socket, `@oh-my-ztty-<uid>-<suite-version>`. Set `OMZTTY_SOCKET` to select another socket explicitly. The terminal uses ztty's resident broker; starting `omztty shell` alone does not start a terminal or AI daemon.

Inside the preset shell, `zai context` produces a small context record for AI tools. `zai connect` starts ssmcp in the current directory. Configure and authenticate ssmcp using its own instructions. Merely starting the shell creates no remote connection.

## Ink appearance

The default Ink preset uses a graphite background, a complete low-saturation ANSI palette, 24 px padding and a 13 pt font request. Fontconfig tries installed JetBrains Mono, JetBrainsMono Nerd Font, Caskaydia Mono, Cascadia Mono and ordinary monospace in that order. The prompt does not require private-use icon glyphs. Personal Fontconfig rules may change the selected family.

The two-line prompt separates the path and cached Git branch from command input. It shows a nonzero exit code and commands lasting at least two seconds. Its theme callback uses zsh builtins only.

To use zshard's own minimal prompt, put `OMZTTY_THEME=framework` in `options.zsh`. To install a custom prompt, register it with `zshard theme YOUR_FUNCTION` in `local.zsh`; that file is loaded after Ink. See the [theme API](https://github.com/LIghtJUNction/zshard/blob/v0.1.2/docs/plugins.md).

## Personal configuration and plugins

Create configuration below `${XDG_CONFIG_HOME:-$HOME/.config}/oh-my-ztty`. The suite reads two optional files:

| File | Loaded when | Intended use |
| --- | --- | --- |
| `options.zsh` | Before framework initialization | Startup options such as `ZSHARD_KEYMAP=vi` or `ZSHARD_COMPLETION=eager` |
| `local.zsh` | After framework initialization | Aliases, plugin loading, themes and the `ZSHARD_AI_COMMAND` provider argv array |

Both files remain outside the installed release and survive upgrades and uninstallation. To try the included example plugin, add this to `local.zsh`:

```zsh
zshard load "$ZSHARD_HOME/examples/hello.plugin.zsh"
```

For remote plugins, install a reviewed full Git commit explicitly, then put `zshard use NAME` in `local.zsh`. [The plugin guide](https://github.com/LIghtJUNction/zshard/blob/main/docs/plugins.md) documents locking, restoration, lazy loading, hooks and themes.

Configure an installed AI provider's executable and arguments as the `ZSHARD_AI_COMMAND` array in `local.zsh`, then use `zai ask` inside the preset shell or `omztty ai ask` from another shell. The provider receives the context and request on standard input. Its output is displayed, without automatic command evaluation. The `context` and `connect` subcommands remain independent of that provider configuration.

## Offline installation

Download the archive and its matching `.sha256` file from the same release, then run:

```sh
sh install.sh --from ./oh-my-ztty-0.1.1-linux-x86_64.tar.gz
```

Use the aarch64 archive on ARM64. An explicit `--sha256 HEX` can replace the sidecar file when the digest has already been obtained from the release record.

## Updates and repeat installation

```sh
omztty update
```

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

```sh
omztty uninstall
```

The uninstaller removes this suite's installation and links that still point to it. Files you replaced and unrelated tools are preserved. Dotfile repositories and their links are separate from the suite installation; remove a managed dotfile profile with zdot before uninstalling zdot if you want those links removed too.
