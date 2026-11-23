# Suite 0.2.14 local zmem update

Verified on 2026-11-23, Asia/Taipei. The installed Linux x86_64 suite is 0.2.14; both `omztty memory --version` and the default `zmem --version` return `zmem 0.4.4`. The running system service is active with a fresh daemon report, complete protection and no reported errors. Its executable, the installed system CLI and the bundled CLI all match SHA-256 `22222087799eb545299b25ca8854cf2e329cf22b12983758fa4d3495b8c7d346`.

The [text evidence](evidence/zmem-0.4.4-local-package.json) records component identities, reused artifact hashes, package integrity, validation and installed readback. The published-release download guides remain at 0.2.13. This record covers the locally packaged and installed x86_64 update; it does not establish a published multi-architecture 0.2.14 release.

## Source and runtime consistency

The zmem component and dependency lock now point to [c1892c6193762ae478a383366178937bfdbbbff6](https://github.com/LIghtJUNction/zmem/commit/c1892c6193762ae478a383366178937bfdbbbff6). The other six component records and gitlinks retain their preceding identities. The actual zmem package metadata reports 0.4.4 with the same dependency and feature surface.

The existing installed 0.2.13 bundle still supplied zmem 0.4.1 even after the system service was updated. `omztty memory` deliberately executes its bundled CLI, and `memory setup` installs that executable. Updating the source lock alone could therefore leave the suite's command and future setup on the older version. The new installed bundle closes that mismatch.

The zmem update retains bounded terminal and remote-control demand after eviction, pauses optional reclaim when a managed group quickly reuses file pages, and avoids dedup process discovery while the complete managed inventory is empty. See the upstream [0.4.4 acceptance record](https://github.com/LIghtJUNction/zmem/blob/c1892c6193762ae478a383366178937bfdbbbff6/docs/acceptance-0.4.4.md) for policy limits and the natural-workload observations.

## Verified artifact reuse

The local package reuses the unchanged components from the installed 0.2.13 bundle. The procedure verified every input manifest entry and compared all six reused component source identities with the new dependency lock. It copied only listed component files, checked their hashes again, and copied suite-owned runtime, configuration and packaging files from the updated source. The new zmem binary came from the separately validated upstream build; unchanged components were not recompiled.

The package has newly generated `BUILD.json`, `MANIFEST.sha256`, platform metadata, archive and checksum. The old installer's `.archive-sha256` and files outside its manifest were excluded. Staged `omztty memory --version` and live `status --json` checks passed before installation. The unchanged installer then switched to a separate 0.2.14 release directory and validated the complete new manifest.

| Artifact | Verified identity |
| --- | --- |
| Local archive | `oh-my-ztty-0.2.14-linux-x86_64.tar.gz`, 9,122,513 bytes |
| Archive SHA-256 | `e9ef0a7ceecb783b0c1b8271ed48ed8091539836c3ca68c4047164a53c155690` |
| Package manifest SHA-256 | `f78ae32a082e32433a836ee8057ea7f0d1e6b84b920ed76a6f59c274220c31d7` |
| zmem executable SHA-256 | `22222087799eb545299b25ca8854cf2e329cf22b12983758fa4d3495b8c7d346` |

The installer retained active swap and preserved the existing system configuration. A final hash comparison confirmed that `/etc/zmem/zmem.conf` still matched the immediate pre-update 0.4.3 backup. The previous suite release remains available for existing processes and local recovery.

## Validation and version tooling

The complete existing `make check` gate passed: **225 tests, zero failures, zero errors and zero skips**, followed by Python compilation checks. The suite's pinned zshard fixture was initialized at its recorded source for the test run; no unrelated component source was upgraded. Upstream zmem validation separately passed 250 Rust tests, with three existing privileged fixtures ignored.

Version tooling now accepts `python3 scripts/bump.py patch --source-only` to advance `VERSION` and the installer without changing published-download guidance. It is mutually exclusive with `--release`. A later ordinary bump derives the published version from the current overview, so an intervening source-only update does not break release-guide synchronization. The six version-tool tests cover these transitions and the existing publication safeguards. No release tag or formal publication workflow was invoked for this local package.
