# A unified workspace

The Ink profile puts the shell, Neovim and everyday terminal tools under one zdot deployment. zrc provides the native application configuration; zdot previews changes, creates links and restores original files.

## Set up shell configuration

Run `omztty setup` to prepare an editable profile, connect an existing zsh startup file and optionally create a private GitHub dotfiles repository. `omztty setup --local` prepares configuration without a remote repository. Application deployment remains available through `config apply` below.

```sh
omztty setup --local
omztty env set EDITOR nvim --shared
omztty env set API_BASE_URL https://api.example.invalid
omztty path add "$HOME/.local/bin"
omztty path add "$HOME/dev tools/bin" --append
omztty rc add aliases
omztty rc edit aliases
omztty rc check
omztty shell
```

An environment variable is a named value passed to programs the shell starts. `env set` saves a machine-specific value; `--shared` saves a value in the profile repository. Local values override shared values with the same name. `env list` shows names and sources, while `env get NAME` and `env list --show` explicitly show values. `env unset NAME` removes a local definition; add `--shared` to remove a shared definition.

PATH is the ordered list of directories searched for commands. `path add` adds a directory at the front; `--append` places it after the inherited PATH. `path move DIR first|last` changes its priority, and `path remove DIR` removes its saved rule. Home-relative paths are portable between machines. `path list` shows rules; `path list --effective` shows the environment inherited by the command. The profile stores selected rules instead of copying a session's full PATH.

Rc snippets hold ordinary zsh code such as aliases and functions. Use `rc add NAME`, `rc edit NAME`, `rc show NAME`, `rc enable NAME`, `rc disable NAME` and `rc remove NAME`. `rc add NAME --from FILE` imports an existing snippet. `rc check` checks syntax without executing snippets.

For an ordinary zsh session to load these settings, run `omztty rc install --dry-run`, then `omztty rc install`. The loader block is added to `$ZDOTDIR/.zshrc` when set, otherwise `~/.zshrc`, preserving the existing startup code. `omztty rc uninstall` removes that block. Both install and uninstall accept `--dry-run`.

A new shell loads the saved settings. In an existing suite shell, `source "$OMZTTY_ROOT/config/zsh/settings.zsh"` reloads them and runs enabled snippets again. Programs cannot change their parent shell's environment; saving a rule does not immediately alter the shell that ran the command. Use a fresh session to check removed settings.

For a complete command walkthrough, see the [shell guide](../site/content/shell.md).

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
| `~/.config/oh-my-ztty/profile/` | Shared profile repository, application files and `profile.zdot` |
| `~/.config/oh-my-ztty/profile/shell/env.tsv` | Shared environment values |
| `~/.config/oh-my-ztty/profile/shell/path.tsv` | Ordered, portable PATH rules |
| `~/.config/oh-my-ztty/profile/shell/rc.d/` | Shared zsh snippets |
| `~/.config/oh-my-ztty/local/env.tsv` | Machine-specific environment values, outside profile sync |
| `~/.config/oh-my-ztty/options.zsh` | Local options read before zshard initializes |
| `~/.config/oh-my-ztty/local.zsh` | Existing local shell additions |
| `~/.local/state/oh-my-ztty/backups/` | File snapshots created before profile Git is enabled |
| `~/.local/state/zdot/oh-my-ztty/` | Application deployment journal and original files |
| `~/.local/state/oh-my-ztty/history` | Interactive shell history |
| `~/.config/oh-my-ztty/completions/` | Personal completion files loaded on demand |

The corresponding XDG variables change these roots; XDG_CONFIG_HOME must be inside HOME for a home deployment. `omztty config path` prints the profile directory. Repeating `init` and updating the suite preserve the editable profile.

Print the actual paths with `omztty env file`, `omztty env file --shared`, `omztty path file` and `omztty rc file NAME`. Open them through `env edit`, `path edit` or `rc edit NAME`, or use your editor directly. Keep the data-file format intact and run `omztty rc check` after manual edits.

When the profile has its own Git repository, shared shell edits made through the CLI create local commits. They are pushed only on request. Use `omztty sync history` to review those commits and `omztty sync restore COMMIT [PATH]` to restore shared shell configuration or a selected profile file. Git identity must be configured before a managed shared edit; otherwise the edit stops before writing.

Before Git is enabled, `omztty rc backups` and `omztty rc restore BACKUP_ID` manage local file snapshots. Enabling profile Git stops new snapshots, including for machine-specific variables and the ordinary home rc file; those local files stay outside Git. Existing snapshots are retained locally. In Git mode, the rc backup commands direct you to Git history and restore.

## Refresh defaults after an upgrade

Update the suite with `omztty update` for a per-user installation, or `yay -Syu oh-my-ztty-bin` for the AUR package. Then refresh its defaults:

```sh
omztty config refresh
```

`refresh` compares the editable profile with the defaults from its recorded suite version, then updates files that you have left unchanged. Customized files, removed files, source symlinks, extra personal files and the existing deployment manifest stay in place. It prints each updated or preserved path. Restart the affected application to load its refreshed configuration.

The profile keeps a verified reference copy of shipped defaults in `.baseline/`, separate from your editable files. Refresh replaces that reference with the new shipped defaults after updating the profile; it never copies your personal changes into it. This keeps refresh usable when a system package replaces the runtime in place or an obsolete suite release is removed.

Profiles created before the baseline copy was introduced use the recorded installed release once, then save that reference on successful refresh. Keep that old release until the first refresh completes. A missing, modified or mismatched baseline stops refresh before any profile changes. Repeating refresh at the same suite version does nothing. Refresh handles changes to existing defaults; a changed default file layout or mapping requires a deliberate profile review and is rejected without edits.

## Native completion

Press Tab after a command, an option or a partial value. The suite provides native zsh completion for its tools and their `omztty` entrypoints.

| Command | Completion |
| --- | --- |
| `ssmcp` | Client 0.10.20 commands and options, including `local`, `--account-compat` and `007 upgrade` |
| `ztty`, `omztty ztty` | ztty 0.5.2 launch options and control commands, including `reload --binary` |
| `omztty terminal` | Preset launch options, paths, and command completion after `-e` or `--` |
| `zdot` | Deployment commands, synchronization actions and repository paths |
| `zfetch` | 0.1.1 output format and color options. The last format flag selects the output |
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

The bundled definitions read local paths and static command grammar. They do not query AI accounts, relays, cloud APIs, game services or hardware for candidates. Personal definitions still take priority. Version targets and extension instructions are in the [completion reference](completions.md).


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

Identity, credentials and signing settings remain in the user's existing Git configuration. `omztty setup` can help create a private profile repository under your own GitHub account. Synchronization runs when you request it:

```sh
omztty sync status
omztty sync pull
omztty sync push
```

`omztty config sync` is an alias for these profile-sync commands. `omztty update --config-only` updates your configured profile repository; `omztty update --with-config` updates both a per-user suite installation and its profile repository. Plain `omztty update` updates the suite. Local variables, shell history and existing restoration records remain outside the profile repository. Shared shell edits use Git commits once profile Git is enabled; manual edits can be reviewed and committed by `omztty sync push`.

## Restore and maintain

```sh
omztty config audit
omztty config remove
```

`remove` uses the saved manifest, checks link ownership and restores originals. A destination replaced outside zdot is preserved and reported. To change manifest mappings, remove the deployment, edit the manifest and apply it again.

For a per-user installation, `omztty uninstall` restores this adopted home profile first. A restoration failure preserves the installed runtime for recovery. For the AUR package, run `omztty config remove` before `sudo pacman -R oh-my-ztty-bin`; package removal leaves home files in place. Other deployments made through `omztty dot` remain independently managed.

Legacy framework removal is a deliberate maintenance step after the replacement works. Packages required by other installed software stay under the package manager's dependency rules.
