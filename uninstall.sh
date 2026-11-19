#!/bin/sh
set -eu
die() { printf 'oh-my-ztty: %s\n' "$*" >&2; exit 1; }
[ "$#" -eq 2 ] && [ "$1" = --root ] || die "use: omztty uninstall"
base=$2
case "$base" in /*/oh-my-ztty) ;; *) die "invalid installation root" ;; esac
[ ! -L "$base" ] && [ -f "$base/.owner" ] && [ "$(cat "$base/.owner")" = oh-my-ztty-v1 ] || die "installation ownership check failed"
bindir=$(cat "$base/.bin-dir")
case "$bindir" in /*) ;; *) die "invalid bin directory" ;; esac
for exe in omztty ztty ssmcp zdot zshard; do
    link="$bindir/$exe"
    if [ -L "$link" ] && [ "$(readlink "$link")" = "$base/current/bin/$exe" ]; then rm -- "$link"; fi
done
if [ -f "$base/.desktop-path" ]; then
    desktop=$(cat "$base/.desktop-path")
    if [ -L "$desktop" ] && [ "$(readlink "$desktop")" = "$base/oh-my-ztty.desktop" ]; then rm -- "$desktop"; fi
fi
manpath="${base%/*}/man/man1/omztty.1"
if [ -L "$manpath" ] && [ "$(readlink "$manpath")" = "$base/current/packaging/omztty.1" ]; then rm -- "$manpath"; fi
rm -rf -- "$base"
printf 'Uninstalled oh-my-ztty. User configuration, history and dotfiles are preserved.\n'
