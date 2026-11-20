# oh-my-ztty 0.1.2 — release acceptance

Date: 2026-11-20 (Asia/Taipei).

**Status: released and verified.** Suite [v0.1.2](https://github.com/LIghtJUNction/oh-my-ztty/releases/tag/v0.1.2) is fixed at source commit [`0ad667661e26316851e3a90406c146ce98aa9663`](https://github.com/LIghtJUNction/oh-my-ztty/commit/0ad667661e26316851e3a90406c146ce98aa9663). The [formal release workflow](https://github.com/LIghtJUNction/oh-my-ztty/actions/runs/44623463767) succeeded for both Linux architectures, and the downloaded public installer passed the default-network lifecycle audit.

## Changes and resulting behavior

- **Deferred plugins:** zshard 0.1.3 attempts every plugin already in the deferred batch and retains the first failure status. One failing plugin no longer silently discards the later plugins. Successful plugins remain deduplicated; newly queued work waits for the next editor event. This does not introduce a background process.
- **Desktop preference:** the installer preserves an explicit desktop-entry choice across repeated installs and updates. `--desktop` and `--no-desktop` explicitly change the choice; `omztty update` inherits it by default. The installer migrates existing installations, preserves foreign files and links, and refuses an unreadable old desktop record before changing the active installation.
- **Recursive source pins:** `workspace.py pin` synchronizes nested submodules with the requested component commit, checks source/path conflicts and writes the lock only after the recursive update succeeds. A failed update attempts to restore old commits, branches and local submodule settings without deleting conflicting user work.
- **Release version consistency:** the bump command updates VERSION, the installer's default version, the current homepage release and current installation examples together. A mismatched document aborts before edits. Historical releases and benchmark references retain their original versions.

Implementation checkpoints: [installer](https://github.com/LIghtJUNction/oh-my-ztty/commit/5baa78aa81dd735209f572708c3c82d10850cbed), [recursive pins](https://github.com/LIghtJUNction/oh-my-ztty/commit/beb6997f764462ec00c72ed4befd7848c1d7fee0), [version synchronization](https://github.com/LIghtJUNction/oh-my-ztty/commit/622219e578d28aa3914fed6b17a0f56dc1e6b0d3), and [zshard failure isolation](https://github.com/LIghtJUNction/zshard/commit/bd31ede845649383f966fc83561c2e98902ec478).

## Published component inputs

Both archives' BUILD.json files match these gitlinks in the suite release commit.

| Component | Version | Immutable source |
| --- | --- | --- |
| zshard | 0.1.3 | [`a55c2d08b4299b25ec007b45641df87e8c0d0bbb`](https://github.com/LIghtJUNction/zshard/commit/a55c2d08b4299b25ec007b45641df87e8c0d0bbb) |
| zdot | 0.1.1 | [`43cc523c0fd4331402d2393280509ac2c672a262`](https://github.com/LIghtJUNction/zdot/commit/43cc523c0fd4331402d2393280509ac2c672a262) |
| ztty | 0.4.1 | [`6b91e29e923aaee0207953f2b04393087f19e0d8`](https://github.com/LIghtJUNction/ztty/commit/6b91e29e923aaee0207953f2b04393087f19e0d8) |
| ssmcp | 0.10.10 | [`52a531a59e9ec9236a76eafc0f4f068799e44b15`](https://github.com/LIghtJUNction/ssmcp/commit/52a531a59e9ec9236a76eafc0f4f068799e44b15) |

zshard [v0.1.3](https://github.com/LIghtJUNction/zshard/releases/tag/v0.1.3) passed its separate [formal release workflow](https://github.com/LIghtJUNction/zshard/actions/runs/44622440932). Its source archive SHA-256 is `038bccbc886a2024a211864e55fd71624258ce3de54c5a22ac82c15e6522aa12`.

## Verification

| Layer | Result and scope |
| --- | --- |
| Local suite gate | `make check`: 34 tests passed in 14.757 seconds, plus shell syntax and Python compilation checks. |
| zshard local gate | 29 passed, one ownership test skipped in the non-root local run; the formal release's isolated ownership regression also succeeded. |
| Formal x86_64 release | Ubuntu 24.04: locked build, installer lifecycle, bundled-program smoke test, actual terminal window, keyboard, completion and cleanup all passed. |
| Formal aarch64 release | Native Ubuntu 24.04 ARM runner: the same build and runtime gates passed. |
| Public assets | Six assets matched GitHub size/digest metadata; three checksum sidecars, two embedded manifests and both BUILD.json inputs matched. Each embedded manifest covered 45 payload files. |
| Actual public installation | Native x86_64 development host (glibc 2.44), isolated HOME paths containing spaces, unmodified downloaded installer, no local archive/version/download URL override and no PATH mocks. |
| Installed content | Six checkpoints each verified the installed 46 files, 16 directories, content hashes, modes and absence of extra release entries against the checked archive. |
| Repeat and update | Default installation repeated without changing the current-link inode; a separate `--no-desktop` installation remained disabled on repetition, then real `omztty update --desktop` and `--no-desktop` correctly toggled the exact owned entry and persisted 1/0. |
| Cleanup and preservation | Two uninstalls removed the entire owned install root and managed links. User configuration/history and fixture foreign command files/links survived; the foreign desktop-file case also survived. |
| Shell and AI context | The installed preset shell, doctor and explicit local context command passed. Context omitted history and environment. No AI connection was started. |

The public check ran from 2026-11-19 21:59:07 UTC to 21:59:31 UTC (2026-11-20 in Asia/Taipei). Its complete machine-readable result is [public-release-0.1.2.json](public-release-0.1.2.json).

The development-host installer audit executed x86_64 programs. The downloaded aarch64 archive received manifest, metadata and ELF inspection there; native ARM execution is evidenced separately by the formal ARM runner above.

ELF inspection found GLIBC_2.34 as the highest required glibc symbol version for ztty and ssmcp in both archives. zdot had no dynamic dependencies or interpreter. This is binary inspection, not a claim of testing every distribution with glibc 2.34.

## Documentation website

The [nine-page Markdown documentation site](https://lightjunction.github.io/oh-my-ztty/) uses warm neutral colors and restrained copper accents. It provides chapter navigation, an article outline, local search, code-copy controls, dark/light themes and narrow-screen navigation.

At release source `0ad667661e26316851e3a90406c146ce98aa9663`, `.cache/docs-venv/bin/python scripts/build_site.py` produced **9 pages, 17 files, 223,867 bytes**, with **453 local links checked**. Generated pages show suite 0.1.2 and zshard 0.1.3 and use the current 0.1.2 offline archive. Historical measurements and evidence retain their original source versions.

Visual and interaction evidence is in the [website redesign report](website-2026-11-20.md) and [screenshot (screenshot archive)](https://github.com/LIghtJUNction/oh-my-ztty/releases/download/v0.2.6/oh-my-ztty-generated-evidence-20261121.tar.gz). That screenshot was captured during the preceding 0.1.1 website checkpoint and records the layout and palette. The narrow layout was checked using desktop browser zoom; the clipboard round-trip was inconclusive in that browser and is not claimed as a complete clipboard verification.

## Audit reproduction

The exact executed verifier is archived as [verify-public-release-0.1.2.py](verify-public-release-0.1.2.py), SHA-256:

```text
1ecdb3de8307bbabf4f1fa63df0f57e470658a7db0cf3beeaf26b96213b1d98f
```

It requires Linux, Python 3, GitHub CLI access for public metadata, curl, readelf, zsh and the installed-program prerequisites. Run the copied script from the ignored cache so downloaded assets remain outside the source tree:

```sh
mkdir -p .cache/public-release-audit
cp docs/reports/verify-public-release-0.1.2.py .cache/public-release-audit/verify_suite_public_v0_1_2.py
python3 .cache/public-release-audit/verify_suite_public_v0_1_2.py v0.1.2 \
  --source-commit 0ad667661e26316851e3a90406c146ce98aa9663 \
  --workflow-run 44623463767
```

This version-specific audit requires v0.1.2 to remain the latest stable release before it exercises the real update command. A newer latest release intentionally stops that gate, so it cannot silently test a different version. It uses temporary HOME/XDG directories and does not install into the account's actual home.

## Asset digests

| Public asset | Bytes | SHA-256 |
| --- | ---: | --- |
| [install.sh](https://github.com/LIghtJUNction/oh-my-ztty/releases/download/v0.1.2/install.sh) | 10612 | `bdfa1c737eb133203b6c18f5e5a0680ca280e4515111441d4482c657ad3dbc54` |
| [oh-my-ztty-0.1.2-linux-aarch64.tar.gz](https://github.com/LIghtJUNction/oh-my-ztty/releases/download/v0.1.2/oh-my-ztty-0.1.2-linux-aarch64.tar.gz) | 5054872 | `7e8436deb8867d831ee6105bd2214e713f5c23a775f9b7791435d21fed06d7c6` |
| [oh-my-ztty-0.1.2-linux-x86_64.tar.gz](https://github.com/LIghtJUNction/oh-my-ztty/releases/download/v0.1.2/oh-my-ztty-0.1.2-linux-x86_64.tar.gz) | 5247940 | `6aaebcdd18851d3597f509cb442cbcbaa662575faf5538b9aab5561ab452ff04` |

## Boundaries and next integration

This release keeps the accepted ztty 0.4.1, ssmcp 0.10.10 and zdot 0.1.1 inputs. The ongoing zgpui/ztuio and shared-library migrations belong to their upstream maintainers and will require final published consumer commits and artifact acceptance before a suite pin changes.

Recursive pinning deliberately rejects ignored content inside an initialized nested repository; move such caches aside before pinning. Recovery retains newly created directories and reports conflicts rather than deleting work. Desktop-preference handling does not broaden the installer's existing whole-operation transaction boundary.

No new cross-project performance ranking or complete-suite benchmark was run for this patch. The [performance documentation](https://lightjunction.github.io/oh-my-ztty/performance/) continues to identify the measured zshard 0.1.2 and suite 0.1.1 experiments explicitly.
