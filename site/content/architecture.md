# Architecture

oh-my-ztty assembles independent Project Z tools into a versioned Linux environment. The source repository records exact component commits; the release archive contains the executables, shell files and integration assets.

## Process boundaries

| Component | Responsibility | When it runs |
| --- | --- | --- |
| ztty | Terminal rendering, windows and PTY | While its broker is running |
| System zsh | Parse and execute commands | While the shell is open |
| zshard | Prompt, completion, editing and plugin loading | Inside the existing zsh process |
| zdot | Dotfile planning, links and explicit Git sync | For a requested command |
| ssmcp | Authenticated MCP workspace connection | After an explicit connection command |

The ztty broker supports detached sessions that can outlive a window. Opening `omztty shell` alone does not start that broker or an AI process.

Shell startup does not download plugins, call a provider or connect to MCP. Optional work is requested through commands or declared plugin loading modes.

## Native code

The new zdot library and Linux executable use Rust `no_std`. Their Project Z zclap dependency is configured without its default standard-library feature. The executable uses direct system calls with no allocator, libc or dynamic ELF interpreter.

zshard is written in zsh and adds no compiled helper. The pinned ztty core and executable also use Rust `no_std`; the graphical front end still depends on X11 and system libraries.

The bundled ssmcp retains its existing Rust standard-library and networking dependencies. These boundaries describe separate programs. They do not make the whole bundle free of all standard libraries or system libraries.

Development scripts and build tools are outside the installed native dependency graph.

## Source and artifact pins

The [Git submodules](https://github.com/LIghtJUNction/oh-my-ztty/blob/v0.1.1/.gitmodules) record the source revisions for ztty, zshard, zdot and ssmcp.

For ztty and ssmcp, `dependencies.lock.json` also records the published binary digests. Source gitlinks and upstream artifact locks must agree before building the bundle.

A release includes a build record and `MANIFEST.sha256`. The installer checks both the downloaded archive and its contents before activation. The [public 0.1.1 verification](https://github.com/LIghtJUNction/oh-my-ztty/blob/main/docs/reports/public-release-0.1.1.json) records the resulting assets and binary dependencies.

## Installation state

Releases live below the user's XDG data directory. A `current` link selects the active version. Launchers address bundled executables explicitly, even when another tool with the same name exists elsewhere.

The launcher supplies a separate `ZDOTDIR`, a suite history path and a cache path tied to the release directory. Personal `options.zsh` and `local.zsh` remain outside the release. See [configuration](configuration.md).

Before activation, the installer prepares the audited completion cache. Native zsh auditing and input validation remain part of reuse; it is not a bypass of completion security checks.

## Extension boundaries

Shell plugins use ordinary zsh files, hooks, standard completion functions and prompt callbacks. A pinned plugin installation and its explicit integrity verification are separate from loading it into a shell.

AI providers receive a bounded, explicit context through the [provider contract](ai.md). Proposed commands enter the editing buffer for review.

Dotfile profiles describe repository-relative sources and target-relative destinations. zdot computes the plan before applying it and records ownership for recovery and removal.

Terminal and MCP extensions remain the responsibility of their upstream Project Z projects. The suite pins those implementations and links to their documentation rather than defining a second incompatible interface.

## Versioned combinations

The suite and its components have independent semantic versions. A suite release is a validated combination, identified by its commit and four gitlinks.

Publish a component change first, then advance the suite pin and validate the assembled result. Normal shell startup uses the installed versions. [Development and release workflow](development.md)
