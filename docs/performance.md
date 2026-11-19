# Measured performance

The default path keeps work inside zsh, defers completion initialization and loads optional features on request. Measurements below distinguish framework initialization, a complete suite launch, first completion and live memory. The terminal uses ztty's resident broker; all suite terminal figures include that broker.

## Framework comparison

The framework experiment used an Intel Core i9-12900HX, Arch Linux, zsh 5.9.2 and zshard runtime commit `6d2ff96a593f9d34a53455fa12b64348be4d0cf5`, included in v0.1.1. Each case has 31 interleaved launches after three warmups. Times include process creation and initialization, with prompt rendering excluded for every case.

| Configuration | Median, ms | p95, ms | Idle PSS, KiB |
| --- | ---: | ---: | ---: |
| Plain zsh | 1.514 | 1.811 | 1,533 |
| zsh with audited completion | 12.098 | 14.869 | 3,324 |
| zshard, completion deferred | 3.427 | 4.306 | 2,171 |
| zshard, completion ready | 13.553 | 15.120 | 3,447 |
| Oh My Zsh, git + robbyrussell | 25.650 | 29.645 | 3,816 |

In this experiment, the Oh My Zsh initialization time was 7.48 times the deferred zshard time, or 1.89 times its completion-ready time. The configurations have different feature sets: the Oh My Zsh case uses its git plugin and robbyrussell theme without additional suggestion or highlighting plugins. It is pinned at `c0140703a53eb0d22be44f7bac318d0baacc927c`.

The first Tab took a median of **9.929 ms** with a warm completion dump. Creating a fresh dump took **147.113 ms**. Deferred initialization does not remove that work. The suite installer prepares the audited dump before activating a release, and the graphical verification checks that the installed dump's hash and modification time remain unchanged after a real first Tab. Changes to completion directories can require a new dump.

See the [component methodology](https://github.com/LIghtJUNction/zshard/blob/v0.1.1/docs/performance.md) and [individual samples](https://github.com/LIghtJUNction/zshard/blob/v0.1.1/docs/benchmarks/release-0.1.1.json). These are workstation observations, not a ranking of all shells or plugin combinations.

## Complete suite

The integration build used the pinned zshard v0.1.1 files and published x86_64 executables for ztty v0.4.1, zdot v0.1.1 and ssmcp v0.10.10. Its archive SHA-256 and all four source commits are in the [raw integration report](reports/linux-x86_64-suite.json). Official release archives are built separately on GitHub's native runners; their checksums identify those exact bytes.

The live test opened one 100 × 28 cell window on an isolated Xvfb display with `monospace:size=12`, typed commands into the actual preset shell, pressed Tab, and verified that the shell remained usable. No AI connection was active. The X server is excluded from application memory.

| Live process | Before first Tab, PSS KiB | After first Tab, PSS KiB |
| --- | ---: | ---: |
| ztty broker and renderer | 7,587 | 7,587 |
| Preset zsh | 2,804 | 3,754 |
| Waiting ztty launcher/client | 907 | 907 |
| **Total** | **11,298 (11.03 MiB)** | **12,248 (11.96 MiB)** |

These are resident-memory samples at the stated idle points, not peak allocations or an active MCP session. RSS includes shared mappings in every process; PSS divides shared pages among the processes mapping them. PSS is used for the totals to reduce double counting. Other running applications and library sharing can affect it.

A separate 40-sample interleaved test measured the complete `omztty shell -i -c exit` path at a median of **12.814 ms**, p95 **14.291 ms**. The plain zsh minimum-feature baseline in that same run was **3.350 ms**, p95 **3.689 ms**. This includes launcher and preset initialization but excludes prompt rendering and first Tab. Do not compare times across the framework and suite experiments as if they were one controlled run.

The window first became observable after **85.3 ms** in one launch. That is a diagnostic reading with a 20 ms polling interval, not a statistically measured rendering latency.

The [cache-reuse record](reports/linux-x86_64-completion-cache.json) contains the installed dump's before/after hash and timestamp. The [terminal screenshot](reports/linux-x86_64-terminal.png) records the tested environment.

## Native dotfile manager

zdot has no resident synchronization service. Its new Rust library and executable are `no_std`; the Linux executable uses direct system calls without libc or a dynamic interpreter. Git synchronization is an explicit command and Git's resources are outside the following measurements.

| Measurement | Result | Scope |
| --- | ---: | --- |
| Published v0.1.1 x86_64 executable | 53,848 bytes | Official release artifact |
| Published v0.1.1 ARM64 executable | 66,168 bytes | Official release artifact |
| Version command, median / p95 | 0.241 / 0.307 ms | 50 warm runs of the measured local build |
| 128-mapping JSON plan, median / p95 | 5.222 / 9.332 ms | 50 warm runs with long path names |
| Sampled plan PSS | 228 KiB | Process blocked at an output pipe; not peak memory |

The timing and memory experiment used a 53,776-byte local Rust 1.100.0 build. It differs slightly from the official binaries, so those timings are not attributed to the published executable's exact bytes. Apply, backup and rollback exercise different buffers and can have different peak memory. See [zdot's method and raw evidence](https://github.com/LIghtJUNction/zdot/blob/v0.1.1/docs/performance.md).

## Reproduce and interpret

Run framework and dotfile measurements in their own repositories:

```sh
python3 components/zshard/scripts/benchmark.py --samples 31 --output /tmp/zshard-benchmark.json
make -C components/zdot benchmark
```

The full-suite graphical check uses a release archive and its SHA-256 sidecar:

```sh
python3 scripts/verify_graphical.py dist/oh-my-ztty-0.1.0-linux-x86_64.tar.gz \
  --output /tmp/oh-my-ztty-evidence --samples 40
```

It requires Xvfb, xdotool, ImageMagick, zsh and the terminal's system libraries. It creates its own home, display and broker socket and checks cleanup of the processes it owns. Release-tag workflows run this gate on both native architectures.

Record source and binary hashes, configuration, machine, warmup policy, individual samples and units when comparing another setup. Use the same display backend, font, grid and shell workload for terminal comparisons. The results above support these configurations and scopes; a broader fastest-or-smallest claim requires broader controlled evidence.
