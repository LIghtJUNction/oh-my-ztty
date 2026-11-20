# Dotfiles

Use `omztty dot` to manage a dotfile repository of your own. It links selected files into your home directory, backs up existing files when requested and restores those originals when you remove the deployment.

For the suite's included shell and application settings, start with [configuration](configuration.md). This guide covers a separate repository that you control.

## Create a layout

```sh
omztty dot init --root "$HOME/dotfiles"
```

This creates the file layout and a profile. It does not initialize Git or choose a remote.

Copy the files you intend to manage into `files/`. For example, to manage an existing `.zshrc`:

```sh
cp "$HOME/.zshrc" "$HOME/dotfiles/files/zshrc"
printf 'files/zshrc\t.zshrc\n' > "$HOME/dotfiles/profile.zdot"
```

Each profile line has a source path, a tab, then a destination path. The source is relative to the repository; the destination is relative to the target. Blank lines and `#` comments are ignored. Spaces and Unicode names are supported.

## Preview and apply

For the `.zshrc` example, preview the replacement and apply it with a backup of the existing file:

```sh
omztty dot plan --root "$HOME/dotfiles" --target "$HOME" --backup --json
omztty dot apply --root "$HOME/dotfiles" --target "$HOME" --backup
omztty dot status --root "$HOME/dotfiles" --target "$HOME"
```

Plan only reads. Apply creates the managed link and records the saved original. Without `--backup`, an existing destination stops the operation. Repeating apply keeps matching links. Edits made through a managed symlink change the source file in the repository.

## Remove a deployment

```sh
omztty dot remove --root "$HOME/dotfiles" --target "$HOME"
```

Remove uses the saved deployment profile, checks link ownership and restores originals that were backed up. It refuses to remove a destination that you replaced.

To change a deployed profile, remove its previous deployment, edit it, then apply again. Keep the repository at its original path until removal.

For a per-user installation, `omztty uninstall` restores the adopted `omztty config` home profile before removing the runtime. Before removing the AUR package, run `omztty config remove` to restore that profile. Independent repositories deployed through `omztty dot` remain independently managed.

## Synchronize with Git

Initialize the repository, commit selected files and configure a remote through normal Git commands. Once that is in place:

```sh
omztty dot sync --root "$HOME/dotfiles" status
omztty dot sync --root "$HOME/dotfiles" pull
omztty dot sync --root "$HOME/dotfiles" push
```

Sync uses the installed Git at `/usr/bin/git` or `/bin/git`. Pull only fast-forwards. Commits, remote selection, credentials and merge resolution stay with Git. A pull does not automatically apply a changed profile.

No synchronization daemon or background network activity is started.

## Limits and recovery

| Boundary | Current behavior |
| --- | --- |
| Profile size | At most 64 KiB |
| Mappings per profile | At most 128 |
| Source and parent symlinks | Rejected |
| Traversal and overlapping destinations | Rejected |
| Ordinary apply failure | New links and moved originals are rolled back |
| Interrupted deployment | Journal is retained for remove recovery |

The suite profile uses `--state-dir` to keep metadata and backups under `~/.local/state/zdot/oh-my-ztty`. Direct zdot invocations without that option retain the target’s `.zdot-state` layout and `.zdot.lock` compatibility. zdot does not upload these files. Concurrent edits by unrelated programs are outside its transaction model.

The native tool requires Linux 4.11 or later and a mounted `/proc`. Its Rust library and CLI use `no_std`, Project Z's zclap and direct system calls, without an allocator or libc.

See [zdot's usage reference](https://github.com/LIghtJUNction/zdot/tree/v0.2.0) and [design and recovery details](https://github.com/LIghtJUNction/zdot/blob/v0.2.0/docs/design.md).
