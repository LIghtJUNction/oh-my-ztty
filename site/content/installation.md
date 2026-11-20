# Installation

The release bundle includes ztty, zshard, zrc, zdot, zfetch and ssmcp. Installation and configuration commands from a release do not require Rust or Python.

## Requirements

| Requirement | Supported configuration |
| --- | --- |
| Operating system | Linux x86_64 or ARM64 |
| Shell | System zsh 5.9 or newer |
| Editor profile | Neovim 0.11 or newer, installed separately |
| Graphical session | X11 or XWayland |
| Graphics libraries | X11, Xrender, Xft, Fontconfig, Wayland, xkbcommon, FreeType, HarfBuzz, EGL and GLES |
| Binary ABI | glibc 2.34 or newer and libgcc for ztty and ssmcp |

The ztty 0.5.0 binary needs all of the listed graphics libraries even when selecting the X11 backend. The formal native validation platform is Ubuntu 24.04 on both architectures. The glibc symbol floor alone does not establish compatibility with every distribution. zdot is a static executable without a glibc dependency.

Application and language-server installation is separate from configuration deployment.

On Ubuntu 24.04, install the basic dependencies with:

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

With Git and Arch's `base-devel` tools installed, the package can also be built directly:

```sh
git clone https://aur.archlinux.org/oh-my-ztty-bin.git
cd oh-my-ztty-bin
makepkg -si
```

The package uses prebuilt release binaries; runtime and configuration commands need no Rust or Python. Upgrades go through your AUR helper, and the system package manager owns installed files. Configuration adoption is explicit. After upgrading an adopted profile, run `omztty config refresh` to update defaults you have not changed.

Restore adopted configurations before removing the package:

```sh
omztty config remove
sudo pacman -R oh-my-ztty-bin
```

## Install a release

The following installer manages a per-user installation.

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

The first command starts the preset inside your current terminal. The second opens ztty with the same configuration. These commands try the environment in a separate shell session. Adopt the home profile below to make its configuration the default; account login-shell records remain unchanged.

## Adopt the default workspace

```sh
omztty config init
omztty config plan --json
omztty config apply --backup
omztty config status
```

The profile unifies zsh, ztty, Neovim and everyday terminal-tool configurations. Read the plan before applying it. `--backup` preserves conflicting originals, and `omztty config remove` restores them. Git display colors use the explicit include in [configuration](configuration.md).

Open a new terminal after adoption. Editable files live under `${XDG_CONFIG_HOME:-$HOME/.config}/oh-my-ztty/profile`. The journal and backups live under `${XDG_STATE_HOME:-$HOME/.local/state}/zdot/oh-my-ztty`. HOME adoption requires an absolute `XDG_CONFIG_HOME` within HOME; roots outside HOME are rejected.

Suite upgrades preserve the editable profile. Run `omztty config refresh` after upgrading to update files that still match their shipped defaults. Custom edits, added files and deliberately removed files are preserved.

Personal completion files belong in `${XDG_CONFIG_HOME:-$HOME/.config}/oh-my-ztty/completions/`. The preset registers that directory for on-demand loading. It stays outside the runtime and survives updates and uninstallation.

## System overview

Run `omztty info` to display system information through the bundled zfetch utility. `omztty zfetch` invokes the same tool directly. The shell does not run it automatically.

The standalone Arch Linux package names are `zfetch-project-z` and `zfetch-project-z-bin`. See the [zfetch repository](https://github.com/LIghtJUNction/zfetch) for publication status and installation details.

## Install options

Choose another absolute command directory or omit the desktop entry:

```sh
sh install.sh --bin-dir "$HOME/bin" --no-desktop
```

A new installation creates a desktop entry by default. `--no-desktop` disables it; `--desktop` enables it again. When neither option is supplied, repeat installations and updates preserve the last successful choice.

Disabling an existing installation removes only desktop links that still point to this suite. Replacement files and foreign links are preserved. Enabling the entry stops if an unrelated file or link already occupies its path.

Personal shell configuration belongs outside the release directory. See [configuration](configuration.md) before adding aliases, themes or plugins.

## Offline installation

Download an archive and its matching `.sha256` file from the [same release](https://github.com/LIghtJUNction/oh-my-ztty/releases/tag/v0.2.3), then run:

```sh
sh install.sh --from ./oh-my-ztty-0.2.3-linux-x86_64.tar.gz
```

Use the aarch64 archive on ARM64. If you have already obtained the digest from the release record, the installer's `--sha256` option can supply it instead of a sidecar file.

## Update or reinstall

For a per-user installation:

```sh
omztty update
```

If you adopted a home profile, run `omztty config refresh` after updating to receive changes to unmodified defaults. Upgrade the AUR package through your AUR helper.

To change the desktop entry choice during an update, select one option:

```sh
omztty update --no-desktop
omztty update --desktop
```

For installations created by v0.1.1 or older, the first successful installation with this installer infers the choice from the existing desktop-entry record: present means enabled, absent means disabled. Either explicit option overrides it. The preference is saved after installation succeeds; failed preparation leaves the previous choice intact.

Each version has its own directory. A `current` link selects the active version, and completion caches are separated by release.

Before activation, the installer prepares an audited completion cache. A failed preparation leaves the previous version active. Reinstalling the same archive verifies the existing files; it preserves and reports an installed version that has been modified.

## Uninstall

For a per-user installation:

```sh
omztty uninstall
```

Uninstallation restores the adopted `omztty config` home profile before removing the runtime. Failed restoration or inconsistent deployment records preserve the installation for recovery. After restoration, suite-owned installation files and links are removed; personal profiles, additions, completion files and history are retained.

Independent repositories deployed through `omztty dot` have a separate lifecycle. Use [zdot remove](dotfiles.md#remove-a-deployment) first if you also want to restore those deployments.

The [earlier 0.1.1 installation audit](https://github.com/LIghtJUNction/oh-my-ztty/blob/main/docs/reports/public-release-0.1.1.json) records that release’s installer and managed-link lifecycle; it predates the unified home profile described here.
