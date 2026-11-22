# Memory and Swap

zmem is the suite's default system memory manager. The release installer sets it up with administrator privileges, enables `zmem.service`, and hands management of existing Swap to zmem. The terminal, shell and AI tools use the same system policy.

## See what the system is doing

```sh
omztty memory
omztty memory status --json --processes
omztty memory status --live --json
omztty memory plan --json
omztty memory doctor --json
```

`status` uses the report of the active zmem daemon after checking its process identity. The report retains that daemon's policy history, measured paging rates, worker state and errors. `--processes` adds a current process list. The `observation` fields identify the report source, sampling age and stale data; process measurements have their own timestamp. `omztty doctor` also shows whether the system memory service is active.

`status --live` and `plan` take an independent sample and show a proposed action without applying it. They begin with a new policy state, and paging rates are `null` until measurements are available. If the daemon report cannot be used, ordinary `status` labels its fallback as an independent snapshot and records the cache error. AI clients should check this provenance before interpreting a decision as a daemon report.

## Read pressure, controls and coverage

Memory pressure and IO congestion are separate signals. zmem observes available RAM, memory stalls, file-page refaults and swap activity to decide whether to adjust memory budgets or Swap capacity. Busy IO alone does not lower its swappiness preference. Measured disk-swap pressure can lower it; file pages being evicted and used again can favor retaining file cache when the paging evidence supports that choice.

The `controls` object reports requested and actual swappiness, its reason, the actual page-cluster value, the protection budget and the count of successfully protected scopes. `managed` reports background groups, populated groups, task counts, memory usage and eligible reclaim candidates. The `protection_complete` and `coverage_complete` flags expose incomplete control operations or observations. A plan's requested bytes describe an intended action; observed reclaim progress is reported separately.

The `background` object reports `requested_budget_bytes`, `actual_budget_bytes` and per-group limits. The actual aggregate comes from reading back the limits of populated groups; `plan_available`, `readback_complete` and `applied_complete` identify available plans, complete observations and successful application. With complete information, a `null` budget means no temporary requested ceiling or an unlimited observed group; otherwise it is unavailable. `plan.background_high_percent` remains a pressure-severity hint. Use the byte fields to inspect requested and actual quotas.

An empty background scope has no work to constrain or reclaim. zmem applies background budgets to jobs started in its managed class. Existing applications outside those groups keep their current placement. Interactive protection follows recognized desktop, terminal and remote-access processes into their nested cgroups and distributes a bounded budget through the hierarchy. Recursive kernel protection can pass an ancestor's budget to children even when a child's local `memory.low` is zero.

## Keep background jobs manageable

The suite's source-bundle builder, direct Cargo commands in its component checker, and Project Z's build coordinator automatically start new Cargo builds, checks, tests, benchmarks, Clippy, documentation and compiler jobs in zmem's background class when an active, identity-verified zmem 0.2 or newer is available. This gives the daemon a separate group to budget before the job allocates memory. The existing outer Cargo build lock still coordinates shared build files.

If the required Linux systemd manager or verified zmem daemon is unavailable, the build entry point reports the reason and runs the command normally. Set `ZMEM_BUILD_BACKGROUND=0` for a build batch to keep the caller's current classification. This automatic routing applies to those source entry points' direct Cargo invocations; other background commands can use the explicit form below.

Start a build or other background job through the managed scope:

```sh
omztty memory run --class background -- cargo build
```

Interactive work can use `--class interactive`. The `disposable` class is for work you explicitly allow to encounter a hard memory limit. Use the class before starting the process so the kernel accounts for its memory in the intended group.

Background jobs inherit the managed aggregate's dynamic budget. Starting a background job adds no fixed half-RAM limit to its child scope. During pressure, the daemon calculates the aggregate from current managed usage, available RAM and the configured reserve plus a safety margin. Populated groups share the budget; empty groups receive no share. Existing external limits remain in force.

Changes tighten groups before relaxing any limits. A failed tightening blocks that batch's relaxations, and a failed relaxation stops the remaining ones. Incomplete observations hold existing controls; only kernel readback confirms the resulting budget. Measured spare headroom allows gradual recovery even while the current `memory.high` limit produces PSI stalls, so work can regain capacity as room becomes available. Healthy policy removes the temporary restriction.

Proactive reclaim selects populated managed groups with eligible clean file pages. Empty groups and groups without suitable pages are skipped; requests that produce no observed progress trigger a retry backoff. The current coverage and progress reports show which work this policy can affect.

The default policy preserves processes. It does not discard application data, clear the entire page cache or provide application checkpoints. Applications remain responsible for saving their documents and progress.

## Default policy

The suite ships `config/zmem/zmem.conf`. On first setup, zmem copies this policy to `/etc/zmem/zmem.conf`. Later installs preserve the existing system configuration.

| Setting | Default |
| --- | --- |
| Observation interval | 2 seconds |
| Disk Swap growth step | 2 GiB |
| Maximum managed disk Swap | 32 GiB |
| Disk space kept available | 8 GiB |
| Target free Swap | 4 GiB |
| RAM reserve | Scaled to installed RAM |
| New zram capacity | 50% of RAM |
| Session protection | Enabled |
| Swappiness management | Enabled |
| Profile | Balanced |

Edit `/etc/zmem/zmem.conf` with administrator privileges, then restart `zmem.service`. Existing occupied Swap stays active during adoption; the configured zram layout applies when zmem initializes a device at boot. The [zmem documentation](https://github.com/LIghtJUNction/zmem) defines the configuration keys, policy limits and recovery behavior.

## Setup, updates and recovery

The normal release installation includes system memory setup. For a container, a non-systemd environment or a per-user-only installation, use:

```sh
sh install.sh --no-memory-manager
```

This skips system setup and records the choice for future updates. It does not stop an existing system manager. Enable zmem later with:

```sh
omztty memory setup
omztty update --memory-manager
```

`memory setup` installs the bundled version immediately. `update --memory-manager` also records that system memory management should be included in future suite updates. The setup command copies the executable to root-owned `/usr/local/bin/zmem`; the system service runs that copy, independently of the user-writable suite directory.

To restore the memory managers and configuration recorded before zmem took over:

```sh
omztty memory rollback
```

The system memory service has its own lifetime. Removing the per-user terminal suite keeps it available, along with `/etc/zmem/zmem.conf`. If the suite has already been removed, its recovery command is:

```sh
sudo /usr/local/bin/zmem rollback
```

Package-managed installations can use `omztty memory setup` when their bundle includes zmem. Their ordinary runtime updates continue through the distribution's package manager.
