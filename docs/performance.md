# Measured performance

The default path keeps work inside zsh, defers completion initialization and loads optional features on request. Measurements below distinguish framework initialization, a complete suite launch, first completion and live memory. The terminal uses ztty's resident broker; all suite terminal figures include that broker.

## Workstation migration (0.2.1)

The [workstation report](reports/workspace-0.2.1.md) records the actual HOME migration, recovery checks, screenshots and remaining desktop issue. [Raw startup samples](reports/workspace-0.2.1/startup.json) contain three snapshots from the same active developer workstation, each with three warmups and 31 samples per command. Command kinds were interleaved within each snapshot. Timing uses a blocking subprocess wait from process creation to exit; stdout/stderr were discarded, TERM was xterm-256color and the working directory was HOME.

**Wall time in milliseconds; lower values mean less elapsed time in this measurement.**

| Workload | Before, median | Initial adoption, median | Final snapshot, median | Final snapshot, p95 |
| --- | ---: | ---: | ---: | ---: |
| Interactive zsh | 125.227 | 23.133 | 10.411 | 16.958 |
| Login interactive zsh | 159.331 | 70.872 | 35.376 | 51.363 |
| Neovim headless startup and exit | 37.723 | 15.208 | 9.379 | 12.448 |

The commands were `zsh -i -c exit`, `zsh -l -i -c exit` and `nvim --headless -i NONE +qa!`. These measure startup and exit, not the first visible prompt, editor frame, project indexing or language-server readiness. The previous shell frameworks and LazyVim configuration have different feature sets from the adopted configuration.

The snapshots were taken sequentially and background load was not frozen. The final snapshot followed removal of one redundant personal GPG agent launch, but Neovim also became faster without that hook being part of its edit. The full initial-to-final difference therefore cannot be attributed to the GPG change. Both post-adoption snapshots are retained; these results describe one workstation rather than a general speed ranking.

Formal 0.2.1 archives and their source pins are recorded in the [public release audit](reports/workspace-0.2.1/release-audit.json). The [local graphical record](reports/workspace-0.2.1/local-graphical.json) belongs to a separately built candidate with a different archive hash. It verifies first-Tab cache reuse on isolated Xvfb. The real host initially failed because a private Xvfb occupied its display endpoints. After display-resource recovery, the unchanged official binary passed a fresh suite-window check, the actual default launch chain, program execution and broker reuse. Physical shortcut keypresses were not injected. The three appearance screenshots remain isolated-display evidence, and the SSMCP prevention change still awaits formal artifacts. See the separate [actual desktop record](reports/workspace-0.2.1/actual-desktop.json) and [acceptance summary](reports/workspace-0.2.1/workstation-acceptance.json).

## On-demand system overview (zfetch 0.1.0)

zfetch runs only when requested through `omztty info`, `omztty zfetch` or its standalone command. Its component experiment used 100 interleaved warm runs, including process creation and waiting for exit. JSON output took a median of **0.385 ms**, compared with **2.503 ms** for fastfetch 2.71.0 configured with a similar core module group. The fields are not identical, so the roughly 6.5 time ratio applies to that workload and does not establish a full-feature-equivalent comparison.

The timed local zfetch executable was **23,288 bytes**. Its separate official x86_64 0.1.0 executable is **22,808 bytes**; the timings must not be attributed to those different official bytes. See the pinned component [methodology](https://github.com/LIghtJUNction/zfetch/blob/8f8f6fd6f1f4894829aecab2e9d33d8e77a8fb92/docs/performance.md), [individual samples](https://github.com/LIghtJUNction/zfetch/blob/8f8f6fd6f1f4894829aecab2e9d33d8e77a8fb92/docs/benchmarks/linux-x86_64-0.1.0.json) and [release evidence](https://github.com/LIghtJUNction/zfetch/blob/8f8f6fd6f1f4894829aecab2e9d33d8e77a8fb92/docs/evidence/release-0.1.0.json).

## Historical framework comparison (v0.1.2)

The framework experiment used an Intel Core i9-12900HX, Arch Linux, zsh 5.9.2 and zshard runtime commit `3367c8dadef1a06a047ce9b47aa9446fe219550c`, included in v0.1.2. Each case has 31 interleaved launches after three warmups. Times include process creation and initialization, with prompt rendering excluded for every case.

| Configuration | Median, ms | p95, ms | Idle PSS, KiB |
| --- | ---: | ---: | ---: |
| Plain zsh | 1.679 | 2.005 | 767 |
| zsh with audited completion | 12.291 | 15.236 | 2,308 |
| zshard, completion deferred | 4.106 | 5.114 | 1,161 |
| zshard, completion ready | 19.185 | 24.213 | 2,500 |
| Oh My Zsh, git + robbyrussell | 28.403 | 33.335 | 2,824 |

In this experiment, the Oh My Zsh initialization time was 6.92 times the deferred zshard time, or 1.48 times its completion-ready time. The configurations have different feature sets: the Oh My Zsh case uses its git plugin and robbyrussell theme without additional suggestion or highlighting plugins. It is pinned at `c0140703a53eb0d22be44f7bac318d0baacc927c`.

The first Tab took a median of **15.848 ms** with a warm completion dump. Creating a fresh dump took **147.310 ms**. Deferred initialization does not remove that work. The suite installer prepares the audited dump before activating a release, and the graphical verification checks that the installed dump's hash and modification time remain unchanged after a real first Tab.

Version 0.1.2 checks the current file list and native audit exclusions before cache reuse. It detects ownership changes and same-count file replacement while keeping native `compinit -i` auditing. The extra validation is included in these figures. See the [cache compatibility record](https://github.com/LIghtJUNction/zshard/blob/v0.1.2/docs/completion-cache.md).

The [component methodology](https://github.com/LIghtJUNction/zshard/blob/v0.1.2/docs/performance.md) and [individual samples](https://github.com/LIghtJUNction/zshard/blob/v0.1.2/docs/benchmarks/release-0.1.2.json) identify the exact configuration. These are workstation observations, not a ranking of all shells or plugin combinations. PSS depends on other processes sharing mapped pages; compare values within one recorded run.

## Historical complete suite (v0.1.1)

The integration build contains zshard v0.1.2 and the published x86_64 executables for ztty v0.4.1, zdot v0.1.1 and ssmcp v0.10.10. It uses the Ink preset shipped in oh-my-ztty v0.1.1. Its archive SHA-256 is `6d4a608a037c625b76be3b2d19f269fef69046112868a732e9c8dbf7e69e7e6f`; the [raw integration report](reports/linux-x86_64-suite.json) records all four source commits. Official release archives are built separately on GitHub's native runners; their published checksums identify those exact bytes.

The live test opened one 100 × 28 cell window on an isolated Xvfb display, entered a temporary Git checkout, typed commands into the actual preset shell and pressed Tab. It used Ink's 24 px padding and 13 pt font request; Fontconfig resolved the fallback list to JetBrainsMono Nerd Font in that temporary home. Installed fonts and personal Fontconfig rules can produce a different family. No AI connection was active. The X server is excluded from application memory.

| Live process | Before first Tab, PSS KiB | After first Tab, PSS KiB |
| --- | ---: | ---: |
| ztty broker and renderer | 10,425 | 10,425 |
| Preset zsh | 2,718 | 3,746 |
| Waiting ztty launcher/client | 850 | 850 |
| **Total** | **13,993 (13.67 MiB)** | **15,021 (14.67 MiB)** |

These are resident-memory samples at the stated idle points, not peak allocations or an active MCP session. RSS includes shared mappings in every process; PSS divides shared pages among the processes mapping them. PSS is used for the totals to reduce double counting. Other running applications and library sharing can affect it.

A separate 40-sample interleaved test measured the complete `omztty shell -i -c exit` path at a median of **10.914 ms**, p95 **13.057 ms**. The plain zsh minimum-feature baseline in that same run was **2.700 ms**, p95 **3.893 ms**. This includes launcher and preset initialization but excludes prompt rendering and first Tab. Do not compare times across the framework and suite experiments as if they were one controlled run.

The window first became observable after **114.8 ms** in one launch. That is a diagnostic reading with a 20 ms polling interval, not a statistically measured rendering latency.

The [cache-reuse record](reports/linux-x86_64-completion-cache.json) contains the installed dump's before/after hash and timestamp. Both remained unchanged after the real first Tab. The [terminal screenshot](reports/linux-x86_64-terminal.png) records the tested preset.

### Virtual-display diagnostic

A separate [reproducible terminal diagnostic](reports/linux-x86_64-terminal-comparison.json) opened one window at a time, used the same installed preset shell with completion initialized, verified a 100 × 28 PTY, waited five seconds and sampled PSS ten times. It recorded a median **14,735 KiB** for the ztty application tree and **178,062 KiB** for kitty 0.50.0, including its direct helper and the shell.

This run forced software OpenGL on Xvfb. It excludes the display server and private D-Bus daemon, and cannot measure GPU allocations or represent a native GPU desktop. Both terminals requested the resolved font family at 13 pt, but the recorded padding settings differ in units: ztty uses 24 px and kitty uses 24 pt. There was one launch per terminal. These observations are a diagnostic record, not a controlled rendering-performance ranking or a general memory advantage claim.

## Historical native dotfile manager (v0.1.1)

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
python3 scripts/verify_graphical.py dist/oh-my-ztty-0.1.1-linux-x86_64.tar.gz \
  --output /tmp/oh-my-ztty-evidence --samples 40
```

It requires Xvfb, xdotool, ImageMagick, zsh and the terminal's system libraries. It creates its own home, display and broker socket and checks cleanup of the processes it owns. Release-tag workflows run this gate on both native architectures.

Record source and binary hashes, configuration, machine, warmup policy, individual samples and units when comparing another setup. Use the same display backend, font, grid and shell workload for terminal comparisons. The results above support these configurations and scopes; a broader fastest-or-smallest claim requires broader controlled evidence.
