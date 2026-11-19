# Development and releases

The suite pins independent repositories so a release can be reproduced and each component can improve on its own.

## Start

```sh
git clone --recurse-submodules https://github.com/LIghtJUNction/oh-my-ztty.git
cd oh-my-ztty
python3 scripts/workspace.py status
python3 scripts/workspace.py check
```

Development uses Git, Python 3, make, zsh and a current Rust toolchain. Installation from a release does not require Rust or Python. Run checks locally after changing the relevant component. Manual validation workflows are available; routine pushes do not run a duplicate test matrix.

`workspace.py check` validates zshard, zdot and the installer. It does not rebuild every upstream ztty or ssmcp dependency. Their published executables are checked during bundle verification.

## Change one component

Submodules start at a detached commit. Create a branch before editing:

```sh
git -C components/zshard switch -c improve-completion
make -C components/zshard check
git -C components/zshard add zshard.zsh
git -C components/zshard commit -m "Improve completion initialization"
git -C components/zshard push -u origin improve-completion
```

Commit and publish component changes before advancing the parent's gitlink. Keep unrelated upstream work out of a suite release.

## Pin a published version

```sh
python3 scripts/workspace.py pin zshard v0.1.1
python3 scripts/workspace.py check
git add components/zshard
git commit -m "Update zshard"
git push
```

For ztty and ssmcp, `pin` also obtains the release's binary digests and updates `dependencies.lock.json`. These updates require GitHub CLI access. All architectures must have the expected release asset before the pin changes. Review and commit the lock file with the gitlink.

Use `workspace.py status --json` when an agent or script needs machine-readable source state. No network request is made by `status`.

## Bump and publish

Each new project provides the same interface:

```sh
python3 scripts/bump.py patch
```

This updates version files for review. Use `minor` or `major` for larger changes.

From a clean, validated `main` branch (required by zdot), the release form checks, commits, tags and pushes:

```sh
python3 scripts/bump.py patch --release
```

Tag workflows publish versioned artifacts. Component releases stay independent. To ship a new combination, pin their released versions, validate the assembled bundle, then bump oh-my-ztty.

## Release record

A release needs its exact source pins, pinned upstream binary digests, successful local tests and an installation lifecycle check. Exercise install twice, start the preset shell, run the native tools and uninstall in a temporary home. Keep pre-existing commands and unrelated files in that test.

Record benchmarks with source revisions, OS and CPU, warm-up policy, samples and units. Report shell startup separately from first completion and terminal memory. Keep raw measurements in `docs/reports/`.

## Website

The website is plain HTML, CSS and JavaScript in `site/`. It has no build step, tracking scripts or external fonts. Check desktop and narrow mobile layouts, keyboard navigation and the copy button before publishing a design change. The Pages workflow deploys changes to these files.
