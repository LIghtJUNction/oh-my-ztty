# Performance protocol

The suite is designed to minimize work at shell startup and avoid an additional resident process. Measurements separate the operations that users actually experience.

## What to measure

| Measurement | Included work | Unit |
| --- | --- | --- |
| Framework startup | Clean zsh startup and loading the default framework | ms |
| First completion | Initialization deferred to the first Tab | ms |
| Full launcher startup | Suite launcher, configuration and zsh startup | ms |
| Idle shell | A live interactive shell after initialization | KiB RSS |
| Idle terminal | ztty with its child shell, reported separately | KiB RSS/PSS |
| zdot plan | Native process creation, manifest read and path planning | ms |
| Native binary | Release executable on disk | bytes |

RSS counts resident pages mapped by a process, including shared pages. PSS apportions shared pages. Adding RSS values can count shared pages more than once; use a consistent process set and metric for totals.

## Comparison method

Use a clean temporary home and the same zsh executable. Compare plain zsh, zsh with the system completion setup, zshard and an explicitly identified Oh My Zsh revision. Record the exact enabled plugins and theme. Warm repeated startup and the first completion measure different costs, so publish both.

Interleave measured commands where practical, discard documented warm-up runs, retain individual samples and report the median and p95. State if first-use disk caches are warm. Include the suite launcher when discussing the whole setup.

For the terminal, use the same display backend, font, grid size and workload for all compared programs. Record whether an MCP connection is active. For zdot, use the same file count, path layout and storage for comparable tools.

## Reproduce

The component repositories contain their local regression gates and benchmark scripts. The suite's release verification record in `docs/reports/` identifies the measured revisions and commands. Run performance checks separately from correctness checks so background activity does not distort the measurements.

Broad claims about being fastest or smallest require a relevant, controlled comparison. We publish observed values with their scope and keep the design target separate from those values.
