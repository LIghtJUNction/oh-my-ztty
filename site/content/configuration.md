# Configuration

Keep personal configuration outside the installed release. Upgrades can then replace the suite while retaining your choices.

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

For a custom theme with terminal integration, follow the zero-width OSC boundary handling in the [actual Ink implementation](https://github.com/LIghtJUNction/oh-my-ztty/blob/v0.1.1/config/zsh/ink.zsh). `ZSHARD_PROMPT=off` leaves prompt variables alone.

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

The default terminal configuration requests a 13 pt font and 24 px padding. Fontconfig chooses among installed font families; personal Fontconfig rules can change the resolved font. The prompt does not require private-use icon glyphs.

See the [full zshard option reference](https://github.com/LIghtJUNction/zshard/blob/v0.1.2/docs/plugins.md) and [AI provider configuration](ai.md#use-a-provider).
