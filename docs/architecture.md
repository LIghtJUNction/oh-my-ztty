# Architecture

oh-my-ztty assembles four independent projects into one versioned Linux environment. Git submodules record the source revisions; the release bundle contains the executables and shell files needed at runtime.

## Runtime

| Component | Work it owns | When it runs |
| --- | --- | --- |
| ztty | Terminal window, rendering and PTY | While its broker is running; detached sessions may outlive windows |
| System zsh | Parsing and executing shell commands | While the shell is open |
| zshard | Prompt, completion, editing hooks and plugin loading | Inside the existing zsh process |
| zdot | Planning and managing dotfile links; explicit Git sync | For a requested command |
| ssmcp | Authenticated MCP workspace connection | After an explicit connection command |

The shell startup path does not download plugins, call an AI provider or launch a suite daemon. Completion initialization is deferred; optional plugins declare how they load. The prompt uses shell state and local files.

## Native code and dependencies

The new zdot library and executable use Rust `no_std`, with Project Z's `zclap` parser configured without its default `std` feature. Its Linux backend uses direct system calls. Development scripts and tests run outside that production dependency graph.

zshard is written in zsh. ztty retains its own native terminal architecture and system graphics dependencies. The included ssmcp release has its existing Rust standard-library and networking dependencies. These are separate processes; ssmcp's runtime is started on demand.

This boundary matters when measuring memory: report the terminal, shell and an active MCP client separately, then state which processes are included in any total.

## Installation

Each bundle installs to a version directory below the user's XDG data directory. A `current` link selects the active version. Launchers use the bundled executables, even when an unrelated tool with the same name is already installed.

The suite supplies a separate `ZDOTDIR` for its zsh configuration. Starting it does not require changing the account's login shell. Installation and uninstallation manage only paths belonging to this suite.

The installer checks the downloaded archive before activating it. The build tool verifies the locked upstream asset digests. Gitlinks and dependency asset locks must agree before a release.

## Extension points

**Shell plugins** are ordinary reviewed zsh files. zshard exposes immediate, deferred and first-use loading. Completion functions and editing hooks stay close to the shell's own interfaces. Remote plugin installation is an explicit Git operation pinned to a commit; sourcing a plugin executes its code.

**AI tools** use small, explicit context records and an on-demand MCP connection. A proposed command can be put into the editing buffer for review. It is not executed as a side effect of receiving a suggestion. API keys, environment values and the full command history are not a default context payload.

**Terminal and native extensions** remain in the upstream ztty and ssmcp projects, which use Project Z's plugin interfaces. The suite pins those implementations and keeps their own documentation authoritative.

**Dotfile profiles** are text manifests. A profile maps a repository-relative source to a target-relative destination. zdot computes the plan before making links, refuses conflicts by default, and supports an explicit backup option. Removing a profile checks link ownership.

## Versioning

The suite and the new components have independent semantic versions. A suite release is a tested combination, recorded by its Git commit and four gitlinks. Updating a shell plugin or a component is explicit; normal shell startup uses the installed versions.

Routine checks run locally. Manual validation workflows support another environment when needed. Tag workflows produce release artifacts, and the Pages workflow publishes the static website. There is no build system or JavaScript application runtime in the installed shell.
