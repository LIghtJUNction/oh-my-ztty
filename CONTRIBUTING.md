# Development and releases

The suite develops against the latest default branch of seven independent repositories. Each synchronization records the observed source commits; a release builds that recorded combination.

## Start

```sh
git clone --recurse-submodules https://github.com/LIghtJUNction/oh-my-ztty.git
cd oh-my-ztty
python3 scripts/workspace.py status
python3 scripts/workspace.py sync
python3 scripts/workspace.py check
```

Development uses Git, Python 3, make, zsh and a current Rust toolchain. Installation from a release does not require Rust or Python. Run checks locally after changing the relevant component. Manual validation workflows are available; routine pushes do not run a duplicate test matrix.

`workspace.py check` runs the zshard, zdot, zrc, zfetch and zmem checks, followed by the suite's installer and integration tests. Use `--component suite` for the suite checks alone. Full ztty and ssmcp test suites remain in their component repositories; the bundle build compiles their actual programs for integration verification.

## Change one component

Submodules start at a detached commit. Create a branch before editing:

```sh
git -C components/zshard switch -c improve-completion
make -C components/zshard check
git -C components/zshard add zshard.zsh
git -C components/zshard commit -m "Improve completion initialization"
git -C components/zshard push -u origin improve-completion
```

Commit component changes and merge them into that repository's default branch before synchronizing the suite. Review the resulting gitlink and source lock together.

## Synchronize current sources

```sh
python3 scripts/workspace.py sync
python3 scripts/workspace.py check
git add components dependencies.lock.json
git commit -m "Synchronize suite component sources"
git push
```

With no component argument, `sync` fetches all seven repositories' current default-branch heads and updates their recursive submodules. `dependencies.lock.json` uses schema 2 and records each canonical GitHub URL, branch, commit and observation time. The lock is replaced after all selected source updates succeed.

To update one component after the source lock has been created:

```sh
python3 scripts/workspace.py sync zshard
```

The first migration from the old release-asset lock requires `sync` without a component. Subsequent synchronization fetches the live default branch again. The recorded commit preserves the selected build inputs; publication of a component or suite version remains a separate step.

Synchronization requires clean selected source checkouts and a committed dependency lock. It checks nested repositories and preserves nonempty uninitialized submodule directories. A failed update attempts to restore the previous source commits, branches and URL configuration, keeps the lock unchanged, and reports any remaining recovery work. See the [development guide](site/content/development.md#local-state-and-recovery) for the full scope.

Use `workspace.py status --json` when an agent or script needs machine-readable source state. No network request is made by `status`.

## Build and verify the bundle

```sh
python3 scripts/build_bundle.py
python3 scripts/smoke_bundle.py "dist/oh-my-ztty-$(cat VERSION)-linux-$(uname -m).tar.gz"
```

The build verifies all seven source checkouts and every nested submodule against their recorded commits. It rejects uninitialized submodules and uncommitted files even when nested Git ignore settings hide them from the parent repository. It then compiles ztty, ssmcp, zdot, zfetch and zmem with `cargo build --locked --release`. ztty enables its Wayland feature; ssmcp's JavaScript helper and all component licenses come from the same source checkouts. The build records source commits, default branches and the lock's synchronization time in `BUILD.json`.

Cargo uses the existing user configuration and `CARGO_TARGET_DIR`, including a shared target directory when configured. Native builds reuse Cargo's normal release outputs. `--arch aarch64` or `--arch x86_64` selects the bundle architecture; a different host architecture requires the corresponding Rust target, linker and system libraries. Each executable's ELF architecture is checked before packaging.

Source compilation needs the development packages listed in [the release workflow](.github/workflows/release.yml), including X11, Fontconfig, FreeType, HarfBuzz, EGL/GLES, Wayland and xkbcommon. The build uses the recorded source lock; run `workspace.py sync` when selecting newer inputs. Run the smoke and graphical checks on the assembled archive before a formal release.

## Bump and publish

Each new project provides the same interface:

```sh
python3 scripts/bump.py patch
```

This updates version files for review. Use `minor` or `major` for larger changes.

From a clean, validated `main` branch, the release form checks, commits, tags and pushes:

```sh
python3 scripts/bump.py patch --release
```

Tag workflows publish versioned artifacts. Synchronize component sources, validate the assembled bundle, then bump oh-my-ztty when preparing a release. The source update itself leaves published releases unchanged; [0.2.6's record](docs/reports/0.2.6/release.zh-CN.md) describes that already shipped combination.

## Release record

A release needs its exact source lock, seven gitlinks, successful local tests, archive checksums and an installation lifecycle check. Use `--no-memory-manager` for temporary-home bundle tests; system adoption has its own zmem acceptance gate. Exercise install twice, start the preset shell, run the native tools and both boot-report entrypoints, and uninstall in a temporary home. The graphical check also executes the boot report in the preset shell and captures its terminal output. Keep pre-existing commands and unrelated files in that test.

Record benchmarks with source revisions, OS and CPU, warm-up policy, samples and units. Report shell startup separately from first completion and terminal memory. Keep text measurements and artifact links in `docs/reports/`; store generated screenshots and release archives outside Git.

## Website

The documentation website is authored in `site/content/*.md`, with navigation in `site/nav.json`. A small Python build uses hash-locked Markdown dependencies and emits plain HTML, CSS and JavaScript in `_site`; the browser does not parse Markdown. See [the website build guide](site/README.md) for the isolated build and local preview commands.

The Pages workflow builds the site, validates local links and heading anchors, and deploys the static output. There are no tracking scripts, external fonts or browser framework. Check desktop and narrow layouts, keyboard navigation, search, code copying and both warm-neutral themes before publishing a design change.
