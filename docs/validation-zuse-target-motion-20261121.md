# zuse target movement: consumer source acceptance

Recorded on 2026-11-21 (Asia/Taipei). This update propagates the verified zuse target-movement source through its direct consumers and the source installation bundle. It does not publish new registry packages, release binaries, or deploy an installed SSMCP service.

## Selected sources

| Repository | Selected default-branch source | Result |
| --- | --- | --- |
| zuse | [a1bb8fd2cbce0a9d85134999883c578358065242](https://github.com/LIghtJUNction/zuse/commit/a1bb8fd2cbce0a9d85134999883c578358065242) | Target movement implementation and acceptance record published on main |
| ztype | [da6feb1a3c5488f3854c63d5e5db173ca250dba4](https://github.com/LIghtJUNction/ztype/commit/da6feb1a3c5488f3854c63d5e5db173ca250dba4) | Cargo.lock selects the new zuse source |
| ssmcp | [4237eea2cab8253b8dff84d81861ba1e1adf4246](https://github.com/LIghtJUNction/ssmcp/commit/4237eea2cab8253b8dff84d81861ba1e1adf4246) | Cargo.lock and crates/zuse gitlink select the same zuse source |
| zrc | [2f10ea8dcfbef2db1204ed46dd21ff98c61ed8ee](https://github.com/LIghtJUNction/zrc/commit/2f10ea8dcfbef2db1204ed46dd21ff98c61ed8ee) | Existing runtime integration passed; it has no zuse or SSMCP source pin to edit |
| oh-my-ztty | This source update, based on d671295f63e5d72e8e8b683fd0c75dc0b1395072 | components/ssmcp and dependencies.lock.json were refreshed together by workspace.py sync ssmcp |

The manifests retain canonical Git URLs and default-branch selection. Locks record the actual source observation. zuse remains package version 0.2.2, so the source SHA, rather than the version string alone, identifies this change. Other suite component records were preserved.

## Local evidence

| Consumer | Check | Observed result |
| --- | --- | --- |
| zuse | Complete Rust suite, Clippy, no_std and cross-target checks | 189 Rust tests passed; 20 no_std core/trajectory tests passed; Windows, both macOS architectures and WebAssembly compiled |
| zuse | Private Xvfb/D-Bus/GTK target movement | Exact endpoints, current start, offsets, timing, callback preflight, target failures, CLI and zuse MCP passed |
| ztype | cargo test --locked --offline | 72 passed, 0 failed; one optional external-vocabulary test ignored |
| ssmcp | cargo test --locked --offline --lib computer::zuse_backend:: | 13 passed, 0 failed; two internal subprocess fixtures remain ignored as standalone tests |
| ssmcp | cargo build --locked --offline --bin ssmcp | Candidate built successfully |
| ssmcp | scripts/e2e_zuse_worker.py against that candidate | 27 native worker checks and 6 real X11 text cases passed |
| zrc | python3 scripts/check.py | Configuration and headless editor checks passed; 9 Python tests passed and 12 unrelated native zrc CLI cases were skipped without ZRC_TEST_BINARY |
| zrc | Isolated headless Neovim starts the candidate SSMCP CLI | A real terminal job ran the candidate with --version; the original window and unsaved buffer contents were preserved |
| oh-my-ztty | python3 scripts/workspace.py check --component suite | 112 Python tests passed, with shell/completion syntax and Python compile checks |

The tested SSMCP candidate reports 0.10.21 and has SHA-256 `79d6760214639f34aa87725bccfcd9897ba0e7f7f03ec68739a5b7cca584e00e`. It was a temporary local validation executable, not a distributed release artifact. Native worker fixtures used private X11 desktops. The zrc launch check used an isolated PATH shim to add --version; it did not establish a network session or touch the user's desktop. No compiled binaries or generated screenshots are included in this commit.

The SSMCP dependency update verifies its existing adapter. The new `mouse.move_to` language operation is exposed by zuse's CLI, Rust API and own MCP executor; this change does not add a new SSMCP facade operation. See the [zuse operation contract](https://github.com/LIghtJUNction/zuse/blob/a1bb8fd2cbce0a9d85134999883c578358065242/docs/target-motion.md) and [upstream validation](https://github.com/LIghtJUNction/zuse/blob/a1bb8fd2cbce0a9d85134999883c578358065242/docs/validation-target-motion.md).

## Remaining aggregate gate and owner

The published Project Z main was re-fetched at this acceptance point and remained [34dbf892a7088cbce32f6b9714eded0e772c49d7](https://github.com/LIghtJUNction/project-z/commit/34dbf892a7088cbce32f6b9714eded0e772c49d7). Its [coordinator](https://github.com/LIghtJUNction/project-z/blob/34dbf892a7088cbce32f6b9714eded0e772c49d7/scripts/project_z.py) rejects internal Git sources with:

> Git source bypasses the shared crates.io patch; use a registry version or canonical path

The generator only emits a crates.io patch table. This conflicts with the owner's newer default-branch Git-source policy and prevents accepting a snapshot containing the current consumer manifests. A minimal execution of that coordinator's validation function with ztype's real zuse Git declaration reproduces the rejection. The existing Git-source coordinator migration is separate work; it is not merged into the observed public main.

**Owner:** the existing Project Z root maintainer, responsible for that coordinator migration. The source commits and validation results have been sent to the active maintenance conversation. A delivered coordination message is not aggregate acceptance; no completed aggregate check or takeover acknowledgement is claimed here.

After the coordinator migration is accepted, select the published sources above and this suite commit, regenerate catalog.json, docs/PROJECTS.md and .cargo/project-z.toml, then run project_z.py check and resolve --all under the shared Cargo ownership lock. Commit and push the accepted aggregate snapshot. Until those gates pass, aggregate propagation remains open; the direct consumer and suite source updates above are complete.
