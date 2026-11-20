# Source build and boot-chain acceptance

Validated on 2026-11-20 UTC. The candidate source is [d63e5e0eff46](https://github.com/LIghtJUNction/oh-my-ztty/commit/d63e5e0eff460851656419c23309f573f6e49098); it has the same complete source tree as the pre-cleanup tested commit 9cb751aa2853ca55d9c18c38d9543f6553c33dcc. The suite version remains 0.2.6. Existing published installation archives were not replaced.

## Result

The current six-component source lock built successfully. All 112 suite tests passed. The actual installed package passed repeat installation, doctor, zsh startup, component commands, both boot-chain entrypoints, configuration adoption and restoration, custom XDG paths, and uninstall. The Xvfb check opened the real terminal, executed keyboard input, returned from Tab completion, reused the prepared completion cache, and ran the boot-chain command.

The bundle verifier now checks every initialized nested repository directly. Its five added real-Git regressions cover clean nesting, hidden dirty leaves, uninitialized nested and leaf repositories, and a wrong leaf commit. Native completion cases cover zfetch --boot and both suite entrypoints.

## Inspect startup

Current source builds support:

    omztty info --boot
    omztty info --boot --json
    omztty zfetch --boot --format=json

The JSON schema is zfetch.boot.v1. Both installed entrypoints returned the same nine structural stages, from firmware and bootloader through the kernel, initramfs, system manager, system target, login, user session and desktop. The ordering describes the startup structure; it does not claim measured service timing. Observed runtime evidence, available configuration and unavailable information remain distinct.

## Sources

All observations below refer to each repository's default branch at the recorded time.

| Component | Commit | Observed UTC |
| --- | --- | --- |
| ztty | [a43aebb17a11](https://github.com/LIghtJUNction/ztty/commit/a43aebb17a11b8c25f2c970d0d36a43f67082f9f) | 2026-11-20T18:33:32+00:00 |
| ssmcp | [cace37c7f7c8](https://github.com/LIghtJUNction/ssmcp/commit/cace37c7f7c8c2ad60c9ec712d39f77bc172b88b) | 2026-11-20T18:33:33+00:00 |
| zshard | [f7842f70e439](https://github.com/LIghtJUNction/zshard/commit/f7842f70e439c4abda2a46698f0ebe067d38b297) | 2026-11-20T18:33:35+00:00 |
| zdot | [a3c6a75b1e66](https://github.com/LIghtJUNction/zdot/commit/a3c6a75b1e66747822b9b69d9e046d2aac249210) | 2026-11-20T18:33:36+00:00 |
| zrc | [2f10ea8dcfbe](https://github.com/LIghtJUNction/zrc/commit/2f10ea8dcfbef2db1204ed46dd21ff98c61ed8ee) | 2026-11-20T18:33:39+00:00 |
| zfetch | [f0614f3b76ec](https://github.com/LIghtJUNction/zfetch/commit/f0614f3b76eca222f4b3880f8dd1707d1308f098) | 2026-11-20T18:33:40+00:00 |

## Local verification

| Check | Result |
| --- | --- |
| Suite tests and script syntax | 112 passed |
| Native source bundle | Passed, 264.43 seconds |
| Actual installed-package smoke | Passed |
| Xvfb window, keyboard, completion and boot command | Passed |
| Historical-image archive coverage | 14 distinct blobs verified; none missing |
| History source-equivalence and topology comparison | 74 commits verified |

The candidate archive contains 7,992,238 bytes; its SHA-256 is 0c896068515104fc0f8045d150488845bfb29f52534ca5603f0622742de2b36c. Its component versions are ztty 0.5.2, ssmcp 0.10.21, zdot 0.2.0 and zfetch 0.1.1.

[Machine-readable results](source-acceptance-20261121.json) include exact timings, source pins and the complete graphical measurements. [Graphical evidence](https://github.com/LIghtJUNction/oh-my-ztty/releases/download/v0.2.6/oh-my-ztty-source-acceptance-20261121.tar.gz) contains both PNG screenshots and the original graphical JSON report; its SHA-256 is 038f6ba8b7e7588f215b86bf6e1676089723ffbc79ff072ac5fbf5f5e7bc2c23. Generated images and installation archives are stored outside Git.

## History cleanup

The cleanup rewrote 13 remote branches and 10 annotated tags. Every one of the 74 mapped commits retained all non-image paths, modes, blobs and gitlinks, and its parent order. Three local worktrees were retained, including the two uncommitted source files in the coordination worktree. Index locks covered the complete ref/index migration.

[The mapping](history-cleanup-20261121.json) records old and new commits, ref objects and peeled tag commits. Rewriting removed 44 commit signatures; the original signed objects are preserved in recovery bundles. No signed tag signatures were removed. The [artifact index](generated-artifacts.md) links the historical screenshots and their checksums.

Existing uploaded release assets keep their bytes. GitHub-generated tag source archives acquire new hashes after the tag rewrite. This cleanup covers the controlled branch/tag history; read-only pull refs, forks, caches, old clones and local recovery objects are outside that claim. Local reflogs were not expired and garbage collection was not forced.

## Scope of these results

This iteration built and executed Linux x86_64. ARM64 was not revalidated. The graphical run used Xvfb and an isolated temporary HOME, so unavailable desktop/session fields are expected. The warm shell-start sample contained ten observations per case: the suite median was 8.08 ms and the bare zsh median was 2.08 ms. These local measurements do not establish cold-start or cross-machine performance.
