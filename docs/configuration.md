# A unified workspace

The Ink profile puts the shell, Neovim and everyday terminal tools under one zdot deployment. zrc provides the native application configuration; zdot previews changes, creates links and restores original files.

## Adopt the defaults

```sh
omztty config init
omztty config plan --json
omztty config apply --backup
omztty config status
```

Open a new terminal after adoption. The account shell should already be zsh; adoption does not change account records. Existing application configurations are saved when `--backup` is supplied.

The profile covers zsh, ztty, Neovim, Kitty, Foot, Ghostty, tmux, fzf, bat, ripgrep and Git display settings. Application installation is separate.

| Location | Purpose |
| --- | --- |
| `~/.config/oh-my-ztty/profile/` | Editable application files and one `profile.zdot` manifest |
| `~/.config/oh-my-ztty/options.zsh` | Options read before zshard initializes |
| `~/.config/oh-my-ztty/local.zsh` | Personal shell additions |
| `~/.local/state/zdot/oh-my-ztty/` | Deployment journal and original files |
| `~/.local/state/oh-my-ztty/history` | Interactive shell history |
| `~/.config/oh-my-ztty/completions/` | Personal completion files loaded on demand |

The corresponding XDG variables change these roots; XDG_CONFIG_HOME must be inside HOME for a home deployment. `omztty config path` prints the profile directory. Repeating `init` and updating the suite preserve the editable profile.

## Refresh defaults after an upgrade

Update the suite with `omztty update` for a per-user installation, or `yay -Syu oh-my-ztty-bin` for the AUR package. Then refresh its defaults:

```sh
omztty config refresh
```

`refresh` compares the editable profile with the defaults from its recorded suite version, then updates files that you have left unchanged. Customized files, removed files, source symlinks, extra personal files and the existing deployment manifest stay in place. It prints each updated or preserved path. Restart the affected application to load its refreshed configuration.

The profile keeps a verified snapshot of shipped defaults in `.baseline/`, separate from your editable files. Refresh replaces that snapshot with the new shipped defaults after updating the profile; it never copies your personal changes into the snapshot. This keeps refresh usable when a system package replaces the runtime in place or an obsolete suite release is removed.

Profiles created before snapshots were introduced use the recorded installed release once, then save a snapshot on successful refresh. Keep that old release until the first refresh completes. A missing, modified or mismatched baseline stops refresh before any profile changes. Repeating refresh at the same suite version does nothing. Refresh handles changes to existing defaults; a changed default file layout or mapping requires a deliberate profile review and is rejected without edits.

## Neovim

Neovim 0.11 or newer is required for this profile. Run `nvim` for the Ink welcome page, or open a file normally. The editor has a native status line, diagnostics, a project picker and a searchable shortcut panel. It needs no plugin bootstrap, download or patched icon font.

| Key | Action |
| --- | --- |
| `Space ?` | Search the shortcut panel |
| `Space f f` | Find a project file |
| `Space f g` | Search project text |
| `Space f r` | Recent files |
| `Space b b` | Open buffers |
| `Space e` | File explorer |
| `Space w` | Save |
| `Space c a` | Language-server code actions |
| `Space c r` | Rename a symbol |
| `Space c f` | Format the current buffer |
| `Space d` | Diagnostics |
| `Space a c` | Inspect explicit local AI context |

Language servers start for relevant project files when their executables are already installed. Existing Mason executables are recognized. The welcome page starts no server. Large files disable costly features; project search runs on request with bounded output and a timeout.

The [zrc repository](https://github.com/LIghtJUNction/zrc) documents supported servers, local extensions, the palette and the module registry.

## Personal settings

Edit linked application files normally or use the source under the profile directory. The suite reads `local.zsh` after common shell defaults.

Git's module contains display settings only. Activate it once if desired:

```sh
git config --global --add include.path "${XDG_CONFIG_HOME:-$HOME/.config}/zrc/git.inc"
```

Identity, credentials and signing settings remain in the user's existing Git configuration. The suite does not publish personal profiles or choose a Git remote. After initializing a profile repository and configuring its remote, synchronization is explicit:

```sh
omztty config sync status
omztty config sync pull
omztty config sync push
```

## Restore and maintain

```sh
omztty config audit
omztty config remove
```

`remove` uses the saved manifest, checks link ownership and restores originals. A destination replaced outside zdot is preserved and reported. To change manifest mappings, remove the deployment, edit the manifest and apply it again.

For a per-user installation, `omztty uninstall` restores this adopted home profile first. A restoration failure preserves the installed runtime for recovery. For the AUR package, run `omztty config remove` before `sudo pacman -R oh-my-ztty-bin`; package removal leaves home files in place. Other deployments made through `omztty dot` remain independently managed.

Legacy framework removal is a deliberate maintenance step after the replacement works. Packages required by other installed software stay under the package manager's dependency rules.
