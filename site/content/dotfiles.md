# Dotfiles

zdot links selected files from a repository into a target directory. Plan the changes first, apply them explicitly, and remove the deployment when you want to restore the originals.

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

```sh
omztty dot plan --root "$HOME/dotfiles" --target "$HOME" --json
omztty dot apply --root "$HOME/dotfiles" --target "$HOME"
omztty dot status --root "$HOME/dotfiles" --target "$HOME"
```

Plan only reads. Apply refuses an existing destination by default. For the existing `.zshrc` example, explicitly request a backup if the plan matches what you intend:

```sh
omztty dot apply --root "$HOME/dotfiles" --target "$HOME" --backup
```

Repeated apply keeps matching links. Edits made through a managed symlink change the source file in the repository.

## Remove a deployment

```sh
omztty dot remove --root "$HOME/dotfiles" --target "$HOME"
```

Remove uses the saved deployment profile, checks link ownership and restores originals that were backed up. It refuses to remove a destination that you replaced.

To change a deployed profile, remove its previous deployment, edit it, then apply again. Keep the repository at its original path until removal.

Uninstalling oh-my-ztty does not remove dotfile repositories or their managed links. Remove deployments separately when that is your intent.

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

Metadata remains in the target's `.zdot-state` directory, and `.zdot.lock` serializes cooperating zdot processes. zdot does not upload these files. Concurrent edits by unrelated programs are outside its transaction model.

The native tool requires Linux 4.11 or later and a mounted `/proc`. Its Rust library and CLI use `no_std`, Project Z's zclap and direct system calls, without an allocator or libc.

See [zdot's usage reference](https://github.com/LIghtJUNction/zdot/tree/v0.1.1) and [design and recovery details](https://github.com/LIghtJUNction/zdot/blob/v0.1.1/docs/design.md).
