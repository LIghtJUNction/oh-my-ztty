# Architecture

oh-my-ztty assembles six independent projects into one versioned Linux environment. Git submodules record the source revisions; the release bundle contains the executables and shell files needed at runtime.

## Runtime

| Component | Work it owns | When it runs |
| --- | --- | --- |
| ztty | Terminal window, rendering and PTY | While its broker is running; detached sessions may outlive windows |
| System zsh | Parsing and executing shell commands | While the shell is open |
| zshard | Prompt, completion, editing hooks and plugin loading | Inside the existing zsh process |
| zrc | Native Neovim and terminal-tool configuration | Read by the corresponding application |
| zdot | Planning and managing dotfile links; explicit Git sync | For a requested command |
| zfetch | Native system overview | Only for `omztty info` or `omztty zfetch` |
| ssmcp | Authenticated MCP workspace connection | After an explicit connection command |

The shell startup path does not download plugins, run zfetch, call an AI provider or launch a suite daemon. Completion initialization is deferred; optional plugins declare how they load. The prompt uses shell state and local files.

## Native code and dependencies

The new zdot library and executable use Rust `no_std`, with Project Z's `zclap` parser configured without its default `std` feature. Its Linux backend uses direct system calls. Development scripts and tests run outside that production dependency graph.

zshard is written in zsh. The pinned ztty core and executable also use Rust `no_std`; its graphical front end retains its X11 and system-library dependencies. The included ssmcp release has its existing Rust standard-library and networking dependencies. These are separate processes; ssmcp's runtime is started on demand.

zrc supplies Lua for Neovim 0.11+ and each application's native configuration format. Its configuration is read inside those applications, with no separate configuration daemon. zfetch is a native Rust `no_std` utility with no crate dependencies; its system overview is an explicit command, not a shell-startup banner.

This boundary matters when measuring memory: report the terminal, shell and an active MCP client separately, then state which processes are included in any total.

## Installation

Each bundle installs to a version directory below the user's XDG data directory. A `current` link selects the active version. Launchers use the bundled executables, even when an unrelated tool with the same name is already installed.

The launcher supplies a separate `ZDOTDIR` for trying the shell. To adopt the defaults, `omztty config init` creates an editable zrc profile, `plan` previews its mappings, and `apply --backup` uses zdot to deploy them into HOME. The managed default `.zshrc` then reads the same suite configuration. Account login-shell records are not changed.

The profile and personal additions live under `${XDG_CONFIG_HOME:-$HOME/.config}/oh-my-ztty`. Personal completions use its `completions/` directory, outside the versioned runtime. HOME adoption supports an absolute `XDG_CONFIG_HOME` within HOME; configuration roots outside HOME are rejected. The journal and backups use `${XDG_STATE_HOME:-$HOME/.local/state}/zdot/oh-my-ztty`.

Uninstallation restores the adopted `omztty config` profile before removing the runtime. Failed restoration or inconsistent deployment records preserve the installation for recovery. Independent profiles deployed through `omztty dot` keep their separate lifecycle. See [configuration and recovery](configuration.md).

The installer checks the downloaded archive before activating it. The build tool verifies the locked upstream asset digests. Gitlinks and dependency asset locks must agree before a release.

## Extension points

**Shell plugins** are ordinary reviewed zsh files. zshard exposes immediate, deferred and first-use loading. Completion functions and editing hooks stay close to the shell's own interfaces. Remote plugin installation is an explicit Git operation pinned to a commit; sourcing a plugin executes its code.

**AI tools** use small, explicit context records and an on-demand MCP connection. A proposed command can be put into the editing buffer for review. It is not executed as a side effect of receiving a suggestion. API keys, environment values and the full command history are not a default context payload.

**Terminal and native extensions** remain in the upstream ztty and ssmcp projects, which use Project Z's plugin interfaces. The suite pins those implementations and keeps their own documentation authoritative.

**Application profiles** come from zrc. They share the Ink palette while keeping application-native files editable. Neovim uses native packages and explicit local extensions; the profile does not install applications or language servers.

**Dotfile profiles** are text manifests. A profile maps a repository-relative source to a target-relative destination. zdot computes the plan before making links, refuses conflicts by default, and supports an explicit backup option. Removing a profile checks link ownership.

## Versioning

The suite and the new components have independent semantic versions. A suite release is a tested combination, recorded by its Git commit and six gitlinks. Updating a shell plugin or a component is explicit; normal shell startup uses the installed versions.

Routine checks run locally. Manual validation workflows support another environment when needed. Tag workflows produce release artifacts, and the Pages workflow publishes the static website. Release installation and the installed configuration commands do not require Rust, Python, a build system or a JavaScript application runtime.
