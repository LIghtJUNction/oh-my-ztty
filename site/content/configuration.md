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
| `~/.local/share/oh-my-ztty/completions/` | Personal completion files loaded on demand |

The corresponding XDG variables change these roots. `omztty config path` prints the profile directory. Repeating `init` and updating the suite preserve the editable profile.

## Neovim

Run `nvim` for the Ink welcome page, or open a file normally. The editor has a native status line, diagnostics, a project picker and a searchable shortcut panel. It needs no plugin bootstrap, download or patched icon font.

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
git config --global --add include.path "$HOME/.config/zrc/git.inc"
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

Uninstalling the suite restores this adopted home profile first. A restoration failure preserves the installed runtime for recovery. Other deployments made through `omztty dot` remain independently managed.

Legacy framework removal is a deliberate maintenance step after the replacement works. Packages required by other installed software stay under the package manager's dependency rules.

## Configuration files

Create files below `${XDG_CONFIG_HOME:-$HOME/.config}/oh-my-ztty`:

| File | Load order | Use |
| --- | --- | --- |
| `options.zsh` | Before zshard initializes | Keymap, completion and other startup options |
| `local.zsh` | After zshard and the default theme | Aliases, plugins, custom themes and AI provider configuration |

Both files are optional. The installer and uninstaller preserve them.

## Startup options

For example, put these settings in `options.zsh`:

```zsh
ZSHARD_KEYMAP=vi
ZSHARD_COMPLETION=lazy
ZSHARD_HISTORY_SCAN=200
```

| Option | Default in the suite | Other choices |
| --- | --- | --- |
| `ZSHARD_KEYMAP` | `emacs` | `vi` |
| `ZSHARD_COMPLETION` | `lazy` | `eager`, `off` |
| `ZSHARD_SUGGESTIONS` | `1` | `0` disables history suggestions |
| `ZSHARD_HISTORY_SCAN` | `200` | Bound the number of inspected history events |
| `ZSHARD_HIGHLIGHT` | `1` | `0` disables first-command-token highlighting |
| `ZSHARD_SHELL_INTEGRATION` | `1` | `0` disables OSC 7 / OSC 133 integration |

Highlighting recognizes the first command token. It is not a full shell grammar checker. At the end of the input buffer, Right or Ctrl-F accepts a history suggestion; otherwise the keys move forward normally.

## Aliases and plugins

Put aliases and plugin loading in `local.zsh`:

```zsh
alias ll='ls -alF'
zshard load "$ZSHARD_HOME/examples/hello.plugin.zsh"
```

The included hello plugin is a working example with a command, a hook and cleanup. See [plugins](plugins.md) for loading modes and pinned remote installations.

## Prompt selection

The default Ink preset separates the path and cached Git branch from the input line. It also shows nonzero exit status and commands lasting at least two seconds. Its callback runs with zsh builtins.

To use zshard's own minimal prompt, add this to `options.zsh`:

```zsh
OMZTTY_THEME=framework
```

A custom `zshard theme` registration in `local.zsh` runs after Ink and replaces its callback. The callback receives the previous exit status and elapsed whole seconds, then assigns `PROMPT` and `RPROMPT`.

For a custom theme with terminal integration, follow the zero-width OSC boundary handling in the [actual Ink implementation](https://github.com/LIghtJUNction/oh-my-ztty/blob/v0.2.0/config/zsh/ink.zsh). `ZSHARD_PROMPT=off` leaves prompt variables alone.

## State and cache

The launcher sets these suite-specific locations, using XDG defaults when the environment variables are absent:

| Data | Location |
| --- | --- |
| History | `$XDG_STATE_HOME/oh-my-ztty/history` |
| Completion cache | `$XDG_CACHE_HOME/oh-my-ztty/zshard/<release-directory>` |
| Personal configuration | `$XDG_CONFIG_HOME/oh-my-ztty` |

The usual XDG fallbacks are `~/.local/state`, `~/.cache` and `~/.config`. The release-specific cache lets different installed versions retain their matching completion inputs.

## Terminal sessions

The terminal launcher uses a suite-specific broker socket, `@oh-my-ztty-<uid>-<suite-version>`. Set `OMZTTY_SOCKET` when you explicitly want a different socket.

The default terminal configuration requests a 13 pt font and 28 px padding. Fontconfig chooses among installed font families; personal Fontconfig rules can change the resolved font. The prompt does not require private-use icon glyphs.

See the [full zshard option reference](https://github.com/LIghtJUNction/zshard/blob/v0.2.0/docs/plugins.md) and [AI provider configuration](ai.md#use-a-provider).
