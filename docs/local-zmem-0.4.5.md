# Suite 0.2.15 local zmem update

Verified on 2026-11-23, Asia/Taipei. The installed Linux x86_64 suite is 0.2.15; both `omztty memory --version` and the default `zmem --version` return `zmem 0.4.5`. The bundled executable, system executable and running daemon image all match SHA-256 `76df9ad73e444464fd3559a3d44af7fae6f2aa595efbe926dc4bbc2e0cb8872f`. The service was active, with a fresh report, complete protection, zero automatic restarts and no reported diagnostics.

The [text evidence](evidence/zmem-0.4.5-local-package.json) records the package identities, verified artifact reuse, local test results and installed readback. The published-release download guides remain at 0.2.13. This record covers the locally packaged and installed x86_64 suite 0.2.15; formal release and other architectures require their own publication and validation.

## Source and runtime consistency

The zmem component gitlink and dependency lock both point to [ff07982d751f48cbf4c9fca554760c658d882d43](https://github.com/LIghtJUNction/zmem/commit/ff07982d751f48cbf4c9fca554760c658d882d43). A fresh default-branch query verified that source before the update. All seven gitlinks match the source lock, and the complete records for the other six components remain unchanged.

The 0.4.5 update preserves the original file-refault observation across repeated successful reclaim, requires both measured and averaged pressure windows before optional swap maintenance, and checks the actual writable swap tier before promoting compressed-swap preference. The upstream [acceptance record](https://github.com/LIghtJUNction/zmem/blob/ff07982d751f48cbf4c9fca554760c658d882d43/docs/acceptance-0.4.5.md) records its source validation, installed controls and natural-workload observations.

The suite's `memory` command executes its bundled zmem. Updating this bundle therefore keeps that command and future `memory setup` aligned with the installed 0.4.5 service. The normal installer switched to a separate 0.2.15 release directory after verifying the new package.

## Verified artifact reuse

The package reused six unchanged components from the installed 0.2.14 bundle. All 136 input manifest entries were verified, and every reused component's complete source record matched the new dependency lock. The procedure copied 73 listed component files, checked their copied hashes, and copied suite-owned runtime, configuration and packaging files from the updated source. The zmem executable came from its separately validated upstream build; the other component executables retained their verified hashes.

The new package received freshly generated `BUILD.json`, `MANIFEST.sha256`, platform metadata, archive and checksum. The prior installer's receipt and files outside its manifest were excluded. Before installation, the staged `omztty memory` command returned 0.4.5 and read a fresh 0.4.5 daemon report.

| Artifact | Verified identity |
| --- | --- |
| Local archive | `oh-my-ztty-0.2.15-linux-x86_64.tar.gz`, 9,127,525 bytes |
| Archive SHA-256 | `24a2a3212226c6dc68a3da19e2d1ba73607e464638fba2cdf71ca5c374f3bdf1` |
| Package manifest SHA-256 | `5ac53b9e4e4049f4b53e48ceaa7225a2ea43838114c3afc324927f5f6a826ab5` |
| Input 0.2.14 manifest SHA-256 | `f78ae32a082e32433a836ee8057ea7f0d1e6b84b920ed76a6f59c274220c31d7` |
| zmem executable SHA-256 | `76df9ad73e444464fd3559a3d44af7fae6f2aa595efbe926dc4bbc2e0cb8872f` |

## Installed readback and preservation

After installation, all 136 manifest entries matched the installed package. The 163 protected configuration entries remained unchanged, and the inventory of 17 active swap entries retained its recorded identity. The default and suite memory commands both reported 0.4.5; their underlying binaries and the running daemon had the same verified checksum.

The final daemon report showed complete protection for 20 critical scopes within a shared ceiling of 2,059,587,584 bytes. Reported diagnostics were empty, the service had zero automatic restarts, and its observed cgroup memory use was 1,208,320 bytes. These are installation-time readbacks; workload activity can change scope counts and memory use.

## Validation

The complete existing `make check` gate passed locally: **225 tests, zero failures, zero errors and zero skips**, followed by Python compilation checks. The unit tests took 144.315 seconds. The suite's zshard fixture was initialized at its recorded source, with no unrelated component upgrade. Gitlink/lock consistency and preservation of all six unrelated source records were checked after the scoped source update; `git diff --check` passed.

Upstream zmem separately passed 263 Rust tests, Clippy and the `no_std` policy check; three existing privileged fixtures remained ignored. Its release executable was built and verified on the development host before bundling. The suite checks establish package integrity, command routing and preservation of the existing setup. Performance observations and their workload limits remain documented in the upstream acceptance record; this package update adds no separate throughput measurement.
