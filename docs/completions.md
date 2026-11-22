# Completion reference

Oh My Ztty ships native zsh definitions for the suite, AI clients, developer tools and the author's public command-line applications. It preserves personal definitions and the system's completion functions.

## How it works

A completion function receives the words already typed and the position of the cursor. It chooses the next valid command, option, value or path. The bundled definitions use static command grammar and local filesystem entries, so pressing Tab does not launch those applications or request account data. A delegated command, such as Git after `ztty -e`, uses that command's normal completion.

The shell searches personal definitions, the active managed snapshot, suite definitions and existing system paths in that order. zshard retains this order when initializing either lazily or eagerly. The per-user installer builds the audited cache before switching the active release.

## Check and refresh installed commands

`omztty completion` manages local completion snapshots. Python 3.11 or newer and zsh are required for management; shell startup does not run the manager.

```sh
omztty completion list
omztty completion check ssmcp --json
omztty completion refresh ssmcp
omztty completion refresh
omztty completion path
```

`list` shows the bundled source, active snapshot and personal override for each bundled command. `check` compares source and executable fingerprints without executing applications. It exits nonzero when a selected snapshot is missing or stale. `--json` includes the exact paths and SHA-256 values so a caller can distinguish an older bundled executable from a separately upgraded one.

SSMCP refresh explicitly runs the selected local executable with `--version`, `--help` and `--help-full`, each with a five-second deadline and bounded output. The default selection is `ssmcp` on the calling shell's `PATH`. To inspect a specific installation, use:

```sh
omztty completion refresh ssmcp --binary /absolute/path/to/ssmcp
omztty completion check ssmcp --binary /absolute/path/to/ssmcp --json
```

The help parser reads command names and option declarations as data. It generates quoted completion arguments, then checks their syntax with `zsh -n`; it never sources the help output. New top-level commands and connection options can therefore follow an installed SSMCP upgrade. Nested argument grammars still come from the reviewed bundled definition. A newly discovered subcommand is offered by name, without inventing its arguments. Other command providers use their bundled static definitions and do not execute their applications during refresh.

Refresh writes a new private generation and atomically changes a small pointer only after validation succeeds. The generation name includes the bundled source, personal definition and executable fingerprints. A same-name definition or personal `#compdef` edit therefore changes `fpath`, causing the existing audited zshard cache to rebuild. Personal files are only fingerprinted; the manager does not evaluate or copy them. Failed probes, invalid managed syntax and changed sources keep the previous pointer and files. Existing shells retain their current functions; open a new shell to load the new generation. Old generations remain available to shells that already reference them.

The observed SSMCP additions apply only while the resolved executable and its local file identity match that snapshot. Replacing the executable falls back to bundled grammar until the next explicit refresh. `check` additionally hashes the complete executable to detect in-place changes. Neither shell startup nor Tab runs a version command, generator or network request.

`omztty ssmcp` and `omztty ai connect` deliberately run the suite's bundled executable. Upgrading a separate `ssmcp` on `PATH` does not replace that binary. The completion manager reports both locations, and completion for these explicit suite entrypoints uses the bundled identity. It does not silently switch which application they launch. Personal definitions retain priority and are never rewritten by refresh.

## Native coverage and version targets

The suite pins ztty and the ssmcp client in `dependencies.lock.json` and builds zfetch from its pinned source. The ssmcpd row describes completion for the separately installed daemon.

`omztty terminal` completes launch options and paths because it starts ztty with the suite's preset. Both `-e` and `--` delegate completion to the command being launched. Use `ztty` or `omztty ztty` for control commands such as `attach`, `mcp`, and `reload`. The `reload --binary` argument completes absolute executable paths.

The ssmcp 0.10.20 client completion offers `local`, `--account-compat`, and `007 upgrade`.

zfetch 0.1.1 accepts `--json` and `--format` in either order. The last format flag selects the output, so Tab offers either flag after an earlier one.

| Commands | Verified grammar |
| --- | --- |
| omztty, zdot, zshard, zai | Public entrypoints in the suite |
| ztty and omztty ztty | ztty 0.5.2 |
| omztty terminal | ztty 0.5.2 launch options |
| zfetch | 0.1.1 |
| zmem and omztty memory | zmem 0.1.0 and suite setup/rollback entrypoints |
| ssmcp | Client 0.10.20 |
| codex | codex-cli 0.170.0 |
| claude | Claude Code 2.1.329 |
| gemini | Gemini CLI 0.46.0 |
| opencode | OpenCode 2.3.2 |
| pi | 1.5.2 |
| amp | 0.0.1795147237-g4dbcdb |
| go | Go 1.27.4 |
| npx | 12.2.0 |
| yarn | Classic 1.22.22 |
| rustup | 1.29.3 |
| rustc, node, cmake | Installed public help and conventional local file arguments |
| zcalld | 0.2.5, including its pinned compatibility grammar |
| ssmcpd | 0.10.15 |
| ztype | 0.1.0 source; installation is not required to ship its definition |
| zuse | 0.2.2 source; installation is not required to ship its definition |
| zmcl | 0.1.0 |
| onim | 0.1.13 |
| lmm | lmm-cli 0.1.0 source |
| mechrevo-console | 0.1.0 |
| wgt | 0.1.2 |
| douyin | douyin-cli 2026.11.18 |
| lightjunction | 0.3.0 |
| coolapk | 0.1.1; the executable is `coolapk` |
| binance-cli | 2.3.0; the separate `binance` executable is not reassigned |

These are tested grammar targets, not a promise that every historical or future CLI version has the same options. Public command trees, common options, relevant value enums and local path types are covered. Dynamic account names, remote IDs, private credentials and unknown extension-provided flags are not enumerated. Advanced or experimental options should be checked against the application's own help.

Library crates and internal benchmark/test binaries do not receive invented user commands.

## System completion

Existing Git, uv, Cargo, npm/pnpm/Bun, Python/pip, Docker/Podman, gh, just, SSH/SCP, rsync, curl/wget, tar/make and rg/fd/jq definitions remain available when supplied by the operating system or tool package. The suite avoids replacing these established implementations.

System completion functions may inspect the relevant executable or local project. For example, a distribution's Cargo loader may locate upstream scripts through rustc. The bundled static definitions' no-application-execution behavior does not extend to every third-party completion.

## Add a personal command

Place a file such as `_example` in `${XDG_CONFIG_HOME:-$HOME/.config}/oh-my-ztty/completions/`:

```zsh
#compdef example
_arguments \
  '--format[Output format]:format:(text json)' \
  '1:action:(check build)' \
  '*:file:_files'
```

Open a new suite shell after adding or changing a definition. Keep its `#compdef` command name equal to the actual executable. Existing personal definitions override the suite without editing the release directory.

## Maintaining a definition

Confirm the executable name and installed public help before editing its grammar. Use versioned source when a command cannot be inspected locally. Account for aliases, options that consume values, nested subcommands, free text, command delegation and mutually exclusive modes.

Directory arguments should use `_omztty_directories`, which filters out regular files without zsh's fallback to ordinary filename completion. Preserve quoted paths and non-ASCII characters. Avoid executing an application, reading credential files or making a network request to populate candidates.

Run `python3 tests/test_completion.py` after changes. Its private PTY sends real Tab keystrokes, captures the edited command buffer and traps execution of the native applications. It verifies lazy cache reuse, nested syntax, path handling, strict directory arguments, command boundaries and personal precedence. The normal `make check` gate includes these tests and syntax checks for every packaged completion.
