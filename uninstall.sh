#!/bin/sh
set -eu
die() { printf 'oh-my-ztty: %s\n' "$*" >&2; exit 1; }
[ "$#" -eq 2 ] && [ "$1" = --root ] || die "use: omztty uninstall"
base=$2
case "$base" in /*/oh-my-ztty) ;; *) die "invalid installation root" ;; esac
exec 9<"${base%/*}"
flock -x 9 || die "cannot lock the installation"
[ ! -L "$base" ] && [ -f "$base/.owner" ] && [ "$(cat "$base/.owner")" = oh-my-ztty-v1 ] || die "installation ownership check failed"
bindir=$(cat "$base/.bin-dir")
case "$bindir" in /*) ;; *) die "invalid bin directory" ;; esac
# Restore an adopted home before removing the program that owns its entry point.
profile="${XDG_CONFIG_HOME:-$HOME/.config}/oh-my-ztty/profile"
state="${XDG_STATE_HOME:-$HOME/.local/state}/zdot/oh-my-ztty"
managed_shell=0
if [ -L "$HOME/.zshrc" ] && [ "$(readlink -- "$HOME/.zshrc")" = "$profile/files/.zshrc" ]; then
    managed_shell=1
fi
deployment=0
for owner in "$state"/*/owner; do
    [ ! -f "$owner" ] || deployment=1
done
if [ "$deployment" = 1 ]; then
    [ -d "$profile" ] && [ ! -L "$profile" ] &&
      [ "$(cat "$profile/.omztty-profile" 2>/dev/null)" = omztty-profile-v1 ] ||
        die "configuration profile ownership is damaged; installation was preserved"
    deployment_profile=profile.zdot
    if [ -e "$profile/.config-layout" ] || [ -L "$profile/.config-layout" ]; then
        [ -f "$profile/.config-layout" ] && [ ! -L "$profile/.config-layout" ] &&
          [ "$(cat "$profile/.config-layout")" = canonical-v1 ] ||
            die "configuration layout is damaged; installation was preserved"
        deployment_profile=.omztty-target.zdot
    fi
    "$base/current/bin/zdot" remove --root "$profile" --target "$HOME" --state-dir "$state" --profile "$deployment_profile" ||
        die "configuration restoration failed; installation was preserved"
    if [ -L "$HOME/.zshrc" ] && [ "$(readlink -- "$HOME/.zshrc")" = "$profile/files/.zshrc" ]; then
        die "the managed shell still depends on this installation; installation was preserved"
    fi
elif [ "$managed_shell" = 1 ]; then
    die "the managed shell has no recovery journal; installation was preserved"
fi
if [ -f "$base/current/bin/omztty-manage" ]; then
    "$base/current/bin/omztty" rc uninstall ||
        die "shell startup hook removal failed; installation was preserved"
fi
for exe in omztty ztty ssmcp zdot zshard zfetch zmem; do
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
