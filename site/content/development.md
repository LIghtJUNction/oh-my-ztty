# Development

The suite pins independent repositories so each component can evolve while a released combination remains reproducible.

## Clone the workspace

```sh
git clone --recurse-submodules https://github.com/LIghtJUNction/oh-my-ztty.git
cd oh-my-ztty
python3 scripts/workspace.py status
```

Development uses Git, Python 3, make, zsh and the Rust toolchain required by the component you change. Installation from a release does not need Rust or Python.

Use a machine-readable view when integrating with another tool:

```sh
python3 scripts/workspace.py status --json
```

Status reads local repository state and makes no network request.

## Validate a change

```sh
python3 scripts/workspace.py check
```

This checks zshard, zdot and the installer. It does not rebuild every upstream ztty or ssmcp dependency; their published executables are checked during bundle verification.

Run the relevant checks locally after a change. Manual validation workflows are available. Routine code pushes and pull requests do not start a duplicate daily test matrix.

Keep [benchmark runs](performance.md#reproduce-a-result) separate from correctness checks, and record the source, binary, machine, configuration and workload behind each number.

## Work in a submodule

A freshly cloned submodule starts at a detached commit. Create a branch before editing:

```sh
git -C components/zshard switch -c improve-completion
make -C components/zshard check
```

Commit and publish component changes before advancing the parent gitlink. Keep unrelated upstream work outside the suite change.

## Pin a published component

The pin command accepts a component and a published version. For the framework version in suite 0.1.1:

```sh
python3 scripts/workspace.py pin zshard v0.1.2
python3 scripts/workspace.py check
```

Review and commit the changed gitlink when selecting a new version. Pinning ztty or ssmcp also obtains release asset digests and updates `dependencies.lock.json`; it requires GitHub CLI access and the expected assets for both architectures.

The component's release and the suite's selected pin are separate decisions.

## Bump and release

Each new project exposes the same version interface:

```sh
python3 scripts/bump.py patch
```

This updates version files for review. Use `minor` or `major` when appropriate.

From a clean, validated main branch, the release form checks, commits, tags and pushes:

```sh
python3 scripts/bump.py patch --release
```

Publish component versions, pin them in the suite, validate the assembled bundle, then bump oh-my-ztty. The suite's release-tag workflow builds and validates Linux x86_64 and ARM64 on native runners.

## Release evidence

A release record should identify source pins, upstream binary digests, local check results and a full installation lifecycle.

Install twice in an isolated home, exercise the actual shell and bundled programs, then uninstall. Include pre-existing files so preservation checks test real data. Keep startup, first completion, live memory and active AI sessions as distinct measurement scopes.

The [0.1.1 report](https://github.com/LIghtJUNction/oh-my-ztty/blob/main/docs/reports/release-0.1.1.md) shows the evidence format. The [formal workflow](https://github.com/LIghtJUNction/oh-my-ztty/actions/runs/44609624654) and [public download audit](https://github.com/LIghtJUNction/oh-my-ztty/blob/main/docs/reports/public-release-0.1.1.json) verify the published result.

## Edit this documentation

Pages are Markdown files in `site/content/`. Navigation is declared in `site/nav.json`. The build produces static HTML for GitHub Pages.

Create the isolated build environment and render the site:

```sh
python3 -m venv .cache/docs-venv
.cache/docs-venv/bin/python -m pip install --require-hashes -r site/requirements.txt
.cache/docs-venv/bin/python scripts/build_site.py
```

Preview the generated pages locally:

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory _site
```

Check desktop and narrow layouts, keyboard navigation, search, copy controls and links before publishing a site change. The Pages workflow handles website deployment independently of binary releases.

See [the site authoring guide](https://github.com/LIghtJUNction/oh-my-ztty/blob/main/site/README.md) and [repository contribution guide](https://github.com/LIghtJUNction/oh-my-ztty/blob/main/CONTRIBUTING.md).
