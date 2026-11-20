# Completion reference

Oh My Ztty ships native zsh definitions for the suite, AI clients, developer tools and the author's public command-line applications. It preserves personal definitions and the system's completion functions.

## How it works

A completion function receives the words already typed and the position of the cursor. It chooses the next valid command, option, value or path. The bundled definitions use static command grammar and local filesystem entries, so pressing Tab does not launch those applications or request account data. A delegated command, such as Git after `ztty -e`, uses that command's normal completion.

The shell searches the personal completion directory, suite definitions and existing system paths in that order. zshard retains this order when initializing either lazily or eagerly. The per-user installer builds the audited cache before switching the active release.

## Native coverage and version targets

Suite component versions follow `dependencies.lock.json`. The ssmcp client definition follows the pinned 0.10.10 release, including its supported invite/join commands. It does not advertise later-only options. The separate ssmcpd definition targets the standalone daemon listed below.

| Commands | Verified grammar |
| --- | --- |
| omztty, ztty, zdot, zfetch, zshard, zai, ssmcp | This suite's component lock and public entrypoints |
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
