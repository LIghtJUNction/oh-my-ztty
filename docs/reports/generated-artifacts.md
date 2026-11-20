# Generated visual evidence

Screenshots from earlier validation reports are preserved in the [verified evidence archive](https://github.com/LIghtJUNction/oh-my-ztty/releases/download/v0.2.6/oh-my-ztty-generated-evidence-20261121.tar.gz). The archive retains the original paths and includes a manifest of every image.

Older JSON reports name archive members with their original relative filenames. The [artifact index](generated-artifacts.json) records their Git blob IDs, sizes and SHA-256 digests. Generated screenshots and build archives are stored outside Git history.

The [historical supplement](https://github.com/LIghtJUNction/oh-my-ztty/releases/download/v0.2.6/oh-my-ztty-generated-evidence-history-20261121.tar.gz) preserves the earlier version of `docs/reports/linux-x86_64-terminal.png`. Its original Git blob, archive member and checksum are listed under `historical_versions` in the artifact index. Together, the two archives cover all historical screenshot blobs in the cleanup scope.

## Completed history cleanup

The 13 branches and 10 tags were rewritten after every historical image blob had been verified in the archives. [Commit and tag mapping](history-cleanup-20261121.json) records the source-equivalence checks and preservation boundaries. [Source-build acceptance](source-acceptance-20261121.md) records the integrated boot-chain checks and the new graphical evidence. Original release records retain their original build hashes.
