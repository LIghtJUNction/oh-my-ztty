# Architecture

oh-my-ztty assembles six independent Project Z tools into a versioned Linux environment. The source repository records exact component commits; the release archive contains the executables, shell files and integration assets.

## Process boundaries

| Component | Responsibility | When it runs |
| --- | --- | --- |
| ztty | Terminal rendering, windows and PTY | While its broker is running |
| System zsh | Parse and execute commands | While the shell is open |
| zshard | Prompt, completion, editing and plugin loading | Inside the existing zsh process |
| zrc | Native editor and terminal-tool profiles | Read by the corresponding application |
| zdot | Dotfile planning, links and explicit Git sync | For a requested command |
| zfetch | Native system overview | Only for `omztty info` or `omztty zfetch` |
| ssmcp | Authenticated MCP workspace connection | After an explicit connection command |

The ztty broker supports detached sessions that can outlive a window. Opening `omztty shell` alone does not start that broker or an AI process.

Shell startup does not download plugins, run zfetch, call a provider or connect to MCP. Optional work is requested through commands or declared plugin loading modes.

## Native code

The new zdot library and Linux executable use Rust `no_std`. Their Project Z zclap dependency is configured without its default standard-library feature. The executable uses direct system calls with no allocator, libc or dynamic ELF interpreter.

zshard is written in zsh and adds no compiled helper. The pinned ztty core and executable also use Rust `no_std`; the graphical front end still depends on X11 and system libraries.

The bundled ssmcp retains its existing Rust standard-library and networking dependencies. These boundaries describe separate programs. They do not make the whole bundle free of all standard libraries or system libraries.

zrc supplies Lua for Neovim 0.11+ and each application's native configuration files. Applications load those files directly; no separate configuration process runs. zfetch is a native Rust `no_std` utility without crate dependencies and runs only when requested.

Development scripts and build tools are outside the installed native dependency graph. Installing a release and using its configuration commands require neither Rust nor Python.

## Source and artifact pins

The [Git submodules](https://github.com/LIghtJUNction/oh-my-ztty/blob/main/.gitmodules) record the source revisions for ztty, zshard, zrc, zdot, zfetch and ssmcp.

For ztty and ssmcp, `dependencies.lock.json` also records the published binary digests. Source gitlinks and upstream artifact locks must agree before building the bundle.

A release includes a build record and `MANIFEST.sha256`. The installer checks both the downloaded archive and its contents before activation. The [earlier 0.1.1 verification](https://github.com/LIghtJUNction/oh-my-ztty/blob/main/docs/reports/public-release-0.1.1.json) records that release’s assets and binary dependencies; it predates the unified application profile.

## Installation state

Releases live below the user's XDG data directory. A `current` link selects the active version. Launchers address bundled executables explicitly, even when another tool with the same name exists elsewhere.

The launcher supplies a separate `ZDOTDIR` for trying the shell, a suite history path and a cache path tied to the release directory. Adopting `omztty config` creates an editable profile and deploys it through zdot; the managed default `.zshrc` reads the same suite entry point.

Personal `options.zsh`, `local.zsh` and completion files live under `${XDG_CONFIG_HOME:-$HOME/.config}/oh-my-ztty`. Personal completions use its `completions/` directory, outside the runtime. HOME adoption requires an absolute `XDG_CONFIG_HOME` within HOME. Its journal and backups live under `${XDG_STATE_HOME:-$HOME/.local/state}/zdot/oh-my-ztty`.

Uninstallation restores this adopted profile first. A restoration failure or inconsistent deployment record preserves the runtime for recovery. Independent `omztty dot` deployments remain separate. See [configuration](configuration.md).

Before activation, the installer prepares the audited completion cache. Native zsh auditing and input validation remain part of reuse; it is not a bypass of completion security checks.

## Extension boundaries

Shell plugins use ordinary zsh files, hooks, standard completion functions and prompt callbacks. A pinned plugin installation and its explicit integrity verification are separate from loading it into a shell.

AI providers receive a bounded, explicit context through the [provider contract](ai.md). Proposed commands enter the editing buffer for review.

zrc profiles share the Ink palette through native application files. Neovim supports native packages and explicit local extensions; application and language-server installation remain separate.

Dotfile profiles describe repository-relative sources and target-relative destinations. zdot computes the plan before applying it and records ownership for recovery and removal.

Terminal and MCP extensions remain the responsibility of their upstream Project Z projects. The suite pins those implementations and links to their documentation rather than defining a second incompatible interface.

## Versioned combinations

The suite and its components have independent semantic versions. A suite release is a validated combination, identified by its commit and six gitlinks.

Publish a component change first, then advance the suite pin and validate the assembled result. Normal shell startup uses the installed versions. [Development and release workflow](development.md)
