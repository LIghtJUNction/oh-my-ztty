# Configuration

Keep your shell, editor and terminal-tool settings in one editable profile. `omztty config` copies the included defaults into your configuration directory and links them into place, with backups for existing files.

The included Ink profile comes from zrc. zdot handles the file links and restoration; you edit the application files directly.

## Adopt the defaults

```sh
omztty config init
omztty config plan --json
omztty config apply --backup
omztty config status
```

Open a new zsh session after adoption. Your account's login shell is unchanged. `--backup` saves existing application configurations so you can restore them with `omztty config remove`.

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

`refresh` updates a file only when it still matches the default from the profile's recorded suite version. It lists the paths it updates or preserves. Your edits, removed files, source symlinks, extra personal files and deployment mappings stay in place. Restart the affected application to load the new configuration.

The profile keeps a verified copy of shipped defaults in `.baseline/`. That snapshot contains no personal edits and is replaced after a successful refresh. It lets refresh work after a system package replaces the runtime or an old release directory is removed.

Older profiles without a snapshot need their recorded installed release for the first refresh. Keep that release until refresh succeeds. A missing, modified or mismatched baseline stops the command before it changes the profile. Running it again at the same version does nothing. A change to the default file layout or mappings requires a profile review and is rejected without edits.

## Neovim

Install Neovim 0.11 or newer separately, then run `nvim` for the Ink welcome page or open a file normally. The editor has a native status line, diagnostics, a project picker and a searchable shortcut panel. It needs no plugin bootstrap, download or patched icon font.

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

## Completion

Press Tab after a command, an option or a partial value. The suite includes native zsh completion for its tools, with the same behavior through the `omztty` wrappers.

| Command | Completion |
| --- | --- |
| `ssmcp` | Account, session, browser setup, UI, service and recovery commands; options, themes, log formats and path arguments |
| `ztty` | Session actions, terminal settings and command completion after `-e` or `--` |
| `zdot` | Deployment commands, synchronization actions and repository paths |
| `zfetch` | Output format and color options |
| `zshard` | Plugin actions, locally installed plugin names, hooks and completion directories |
| `zai` | AI actions and ssmcp arguments after `connect` |
| `omztty` | Suite commands and their nested component arguments |

For example, type `ssmcp --theme n` and press Tab to complete `nord`. Try `ssmcp sessions lo`, `zshard plugin ver`, or `ztty -e git checko` for nested commands. `omztty ai connect`, `zai connect` and `zshard ai connect` all share the ssmcp completion.

Completion uses local command definitions and filesystem entries. It starts no component program and makes no relay request; enter remote client identifiers, session names and account values explicitly. The ssmcp definitions match the client's pinned release in `dependencies.lock.json`.

Personal `_command` files in `${XDG_CONFIG_HOME:-$HOME/.config}/oh-my-ztty/completions/` take precedence over included definitions, in both lazy and eager modes. Open a new suite shell after adding one. Existing system completions, including Git, remain available.

The per-user installer prepares an audited completion cache. The default lazy mode loads it on the first Tab; adding or changing completion inputs triggers normal revalidation. Use `ZSHARD_COMPLETION=eager` in `options.zsh` to initialize at startup, or `off` to disable completion.

### AI, development and author tools

The suite also ships these native definitions. Completion definitions do not install the external applications.

| Family | Commands |
| --- | --- |
| AI clients | `codex`, `claude`, `gemini`, `opencode`, `pi`, `amp` |
| Developer tools | `go`, `npx`, `yarn`, `rustc`, `rustup`, `node`, `cmake` |
| Project Z services and input | `zcalld`, `ssmcpd`, `ztype`, `zuse` |
| Project Z desktop and game tools | `zmcl`, `onim`, `lmm`, `mechrevo-console` |
| Other author tools | `wgt`, `douyin`, `lightjunction`, `coolapk`, `binance-cli` |

Try `codex exec --sandbox work<Tab>`, `claude mcp add demo --transport ht<Tab>`, `go mod ti<Tab>`, `rustc -C panic=ab<Tab>`, or `zcalld library mcp apply --agent gem<Tab>`. Prompt text and remote identifiers stay free text. Options that require directories exclude ordinary files, including when paths contain spaces or non-ASCII characters.

Git, uv, Cargo, npm, pnpm, Bun, Python/pip, container tools and ordinary shell utilities retain their installed system completion definitions. Coverage depends on the corresponding completion package being installed. Rust uses the commands `rustc`, `cargo` and `rustup`; there is no generic `rust` command to register. Distribution definitions and commands delegated after `--` may perform their own local discovery.

The bundled definitions read local paths and static command grammar. They do not query AI accounts, relays, cloud APIs, game services or hardware for candidates. Personal definitions still take priority. Version targets and extension instructions are in the [completion reference](https://github.com/LIghtJUNction/oh-my-ztty/blob/main/docs/completions.md).


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

For a custom theme with terminal integration, follow the zero-width OSC boundary handling in the [actual Ink implementation](https://github.com/LIghtJUNction/oh-my-ztty/blob/main/config/zsh/ink.zsh). `ZSHARD_PROMPT=off` leaves prompt variables alone.

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

See the [full zshard option reference](https://github.com/LIghtJUNction/zshard/blob/v0.2.1/docs/plugins.md) and [AI provider configuration](ai.md#use-a-provider).
