# Installation

The release bundle includes ztty, zshard, zdot and ssmcp. Installation from a release does not require Rust or Python.

## Requirements

| Requirement | Supported configuration |
| --- | --- |
| Operating system | Linux x86_64 or ARM64 |
| Shell | System zsh 5.9 or newer |
| Graphical session | X11 or XWayland |
| Graphics libraries | X11, Xrender, Xft and Fontconfig |
| Binary ABI | glibc 2.34 or newer and libgcc for ztty and ssmcp |

The formal native validation platform is Ubuntu 24.04 on both architectures. The glibc symbol floor alone does not establish compatibility with every distribution. zdot is a static executable without a glibc dependency.

On Ubuntu 24.04, install the basic dependencies with:

```sh
sudo apt-get install zsh git curl libx11-6 libxrender1 libxft2 libfontconfig1
```

## Install a release

Download the installer so you can inspect it before execution:

```sh
curl -fLO https://github.com/LIghtJUNction/oh-my-ztty/releases/latest/download/install.sh
sh install.sh
~/.local/bin/omztty doctor
```

The installer downloads the archive for your architecture, verifies its SHA-256 and file manifest, then installs under `${XDG_DATA_HOME:-$HOME/.local/share}/oh-my-ztty`.

Commands go into `~/.local/bin` by default. If that directory is not already on PATH, add it in your normal shell configuration. For the current shell:

```sh
export PATH="$HOME/.local/bin:$PATH"
```

An unrelated existing `omztty` executable stops installation. Existing tools with other names are preserved; the `omztty` launcher selects its bundled components explicitly.

## Start the environment

```sh
omztty shell
omztty terminal
```

The first command starts the preset inside your current terminal. The second opens ztty with the same configuration. The suite uses its own zsh configuration directory; your account's login shell and original `.zshrc` remain available.

## Install options

Choose another absolute command directory or omit the desktop entry:

```sh
sh install.sh --bin-dir "$HOME/bin" --no-desktop
```

A new installation creates a desktop entry by default. `--no-desktop` disables it; `--desktop` enables it again. When neither option is supplied, repeat installations and updates preserve the last successful choice.

Disabling an existing installation removes only desktop links that still point to this suite. Replacement files and foreign links are preserved. Enabling the entry stops if an unrelated file or link already occupies its path.

Personal shell configuration belongs outside the release directory. See [configuration](configuration.md) before adding aliases, themes or plugins.

## Offline installation

Download an archive and its matching `.sha256` file from the [same release](https://github.com/LIghtJUNction/oh-my-ztty/releases/tag/v0.1.1), then run:

```sh
sh install.sh --from ./oh-my-ztty-0.1.1-linux-x86_64.tar.gz
```

Use the aarch64 archive on ARM64. If you have already obtained the digest from the release record, the installer's `--sha256` option can supply it instead of a sidecar file.

## Update or reinstall

```sh
omztty update
```

To change the desktop entry choice during an update, select one option:

```sh
omztty update --no-desktop
omztty update --desktop
```

For installations created by v0.1.1 or older, the first successful installation with this installer infers the choice from the existing desktop-entry record: present means enabled, absent means disabled. Either explicit option overrides it. The preference is saved after installation succeeds; failed preparation leaves the previous choice intact.

Each version has its own directory. A `current` link selects the active version, and completion caches are separated by release.

Before activation, the installer prepares an audited completion cache. A failed preparation leaves the previous version active. Reinstalling the same archive verifies the existing files; it preserves and reports an installed version that has been modified.

## Uninstall

```sh
omztty uninstall
```

Uninstallation removes suite-owned installation files and links that still point to them. Personal configuration, history, dotfile repositories and unrelated commands are preserved.

Dotfile deployments have a separate lifecycle. Use [zdot remove](dotfiles.md#remove-a-deployment) first if you also want to remove those managed links.

The [public installation audit](https://github.com/LIghtJUNction/oh-my-ztty/blob/main/docs/reports/public-release-0.1.1.json) verifies the downloaded installer, repeated installation, configuration and history preservation, and removal of managed command, desktop and manual-page links.
