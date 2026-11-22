#!/bin/sh
# Per-user suite with a separately installed system zmem service.
set -eu
VERSION=0.2.9
die() { printf 'oh-my-ztty: %s\n' "$*" >&2; exit 1; }
usage() {
    cat <<'EOF'
Usage: sh install.sh [--version X.Y.Z] [--from ARCHIVE] [--sha256 HEX]
                     [--bin-dir DIR] [--desktop | --no-desktop]
                     [--memory-manager | --no-memory-manager]
Installs into $XDG_DATA_HOME/oh-my-ztty (default ~/.local/share).
Commands go in ~/.local/bin; existing ztty/ssmcp/zdot commands are preserved.
--from requires a .sha256 sidecar or an explicit --sha256.
Desktop entry preference is remembered; --desktop enables it, --no-desktop disables it.
zmem is the default system memory manager; its setup uses sudo and replaces old managers.
--no-memory-manager skips system setup and remembers that choice for later updates.
--memory-manager enables setup again. Existing /etc/zmem/zmem.conf edits are preserved.
Run omztty shell or omztty terminal. Your login shell and .zshrc stay yours.
EOF
}
archive= expected= desktop= memory_manager=
bindir=${OMZTTY_BIN_DIR:-"$HOME/.local/bin"}
while [ "$#" -gt 0 ]; do
    case "$1" in
        --version|--from|--sha256|--bin-dir)
            [ "$#" -ge 2 ] || die "missing value for $1"
            case "$1" in
                --version) VERSION=${2#v} ;;
                --from) archive=$2 ;;
                --sha256) expected=$2 ;;
                --bin-dir) bindir=$2 ;;
            esac
            shift 2 ;;
        --desktop) desktop=1; shift ;;
        --no-desktop) desktop=0; shift ;;
        --memory-manager) memory_manager=1; shift ;;
        --no-memory-manager) memory_manager=0; shift ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown option: $1" ;;
    esac
done
[ "$(uname -s)" = Linux ] || die "this release supports Linux"
case "$(uname -m)" in x86_64|amd64) arch=x86_64 ;; aarch64|arm64) arch=aarch64 ;; *) die "unsupported architecture" ;; esac
for tool in tar sha256sum awk sed grep tr readlink mktemp; do command -v "$tool" >/dev/null 2>&1 || die "required command not found: $tool"; done
command -v zsh >/dev/null 2>&1 || die "install zsh with your distribution package manager first"
zsh -dfc 'autoload -Uz is-at-least; is-at-least 5.9 "$ZSH_VERSION"' || die "zsh 5.9 or newer is required"
datahome=${XDG_DATA_HOME:-"$HOME/.local/share"}
case "$datahome:$bindir" in *'
'*) die "installation paths must not contain a newline" ;; esac
case "$datahome" in /*) ;; *) die "XDG_DATA_HOME must be absolute" ;; esac
case "$bindir" in /*) ;; *) die "--bin-dir must be absolute" ;; esac
base="$datahome/oh-my-ztty"
[ ! -L "$base" ] || die "installation root must not be a symlink"
if [ -e "$base" ]; then
    [ -f "$base/.owner" ] && [ "$(cat "$base/.owner")" = oh-my-ztty-v1 ] || die "unowned installation directory: $base"
    [ ! -L "$base/releases" ] || die "releases directory must not be a symlink"
    [ "$(cat "$base/.bin-dir")" = "$bindir" ] || die "existing install uses another bin directory"
fi
if [ -e "$bindir/omztty" ] || [ -L "$bindir/omztty" ]; then
    [ -L "$bindir/omztty" ] && [ "$(readlink "$bindir/omztty")" = "$base/current/bin/omztty" ] || die "command path already exists: $bindir/omztty"
fi
desktop_preference="$base/.desktop-enabled"
saved_desktop=
if [ -e "$desktop_preference" ] || [ -L "$desktop_preference" ]; then
    [ -f "$desktop_preference" ] && [ ! -L "$desktop_preference" ] || die "desktop preference is not a regular file"
    saved_desktop=$(cat "$desktop_preference")
    case "$saved_desktop" in 0|1) ;; *) die "desktop preference must be 0 or 1" ;; esac
fi
if [ -z "$desktop" ]; then
    if [ -n "$saved_desktop" ]; then
        desktop=$saved_desktop
    elif [ -L "$base/current" ]; then
        # Releases before this preference file recorded only enabled desktop entries.
        if [ -f "$base/.desktop-path" ]; then desktop=1; else desktop=0; fi
    else
        # A failed first preparation may leave an owned root without an active release.
        desktop=1
    fi
fi
memory_preference="$base/.memory-manager-enabled"
saved_memory=
if [ -e "$memory_preference" ] || [ -L "$memory_preference" ]; then
    [ -f "$memory_preference" ] && [ ! -L "$memory_preference" ] || die "memory preference is not a regular file"
    saved_memory=$(cat "$memory_preference")
    case "$saved_memory" in 0|1) ;; *) die "memory preference must be 0 or 1" ;; esac
fi
if [ -z "$memory_manager" ]; then memory_manager=${saved_memory:-1}; fi
if [ "$memory_manager" = 1 ] && [ "$(id -u)" -ne 0 ]; then
    command -v sudo >/dev/null 2>&1 || die "sudo is required for zmem setup; use --no-memory-manager for a per-user-only install"
fi
desktop_path="$datahome/applications/oh-my-ztty.desktop"
recorded_desktop=
if [ "$desktop" = 0 ] && [ -f "$base/.desktop-path" ]; then
    recorded_desktop=$(cat "$base/.desktop-path") || die "cannot read recorded desktop entry path"
fi
remove_desktop_link() {
    if [ -L "$1" ] && [ "$(readlink -- "$1")" = "$base/oh-my-ztty.desktop" ]; then
        rm -- "$1"
    fi
}
if [ "$desktop" = 1 ] && { [ -e "$desktop_path" ] || [ -L "$desktop_path" ]; }; then
    [ -L "$desktop_path" ] && [ "$(readlink "$desktop_path")" = "$base/oh-my-ztty.desktop" ] || die "desktop entry already exists: $desktop_path"
fi
tmp=$(mktemp -d "${TMPDIR:-/tmp}/oh-my-ztty.XXXXXXXX")
stage=
preference_tmp=
memory_preference_tmp=
cleanup() {
    rm -rf -- "$tmp"
    [ -z "$stage" ] || rm -rf -- "$stage"
    [ -z "$preference_tmp" ] || rm -f -- "$preference_tmp"
    [ -z "$memory_preference_tmp" ] || rm -f -- "$memory_preference_tmp"
    [ ! -d "$base" ] || rm -f -- "$base/.current.$$"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' HUP TERM
fetch() {
    if command -v curl >/dev/null 2>&1; then
        curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 "$1" -o "$2"
    elif command -v wget >/dev/null 2>&1; then
        wget -q --https-only -O "$2" "$1"
    else die "curl or wget is required for downloading"; fi
}
valid_version() { printf '%s\n' "$1" | LC_ALL=C grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$'; }
valid_version "$VERSION" || die "invalid version"
if [ -z "$archive" ]; then
    name="oh-my-ztty-$VERSION-linux-$arch.tar.gz"
    url="https://github.com/LIghtJUNction/oh-my-ztty/releases/download/v$VERSION"
    archive="$tmp/$name"
    fetch "$url/$name" "$archive"
    fetch "$url/$name.sha256" "$archive.sha256"
fi
[ -f "$archive" ] || die "archive does not exist: $archive"
if [ -z "$expected" ]; then
    [ -f "$archive.sha256" ] || die "missing checksum: $archive.sha256"
    expected=$(awk 'NR == 1 {print $1}' "$archive.sha256")
fi
[ "${#expected}" = 64 ] || die "invalid SHA-256 digest"
case "$expected" in *[!0-9a-fA-F]*) die "invalid SHA-256 digest" ;; esac
actual=$(sha256sum "$archive" | awk '{print $1}')
[ "$actual" = "$(printf '%s' "$expected" | tr A-F a-f)" ] || die "archive checksum mismatch"
tar -tzf "$archive" > "$tmp/entries"
awk '!/^oh-my-ztty\// {bad=1} /(^|\/)\.\.(\/|$)/ {bad=1} END {exit bad}' "$tmp/entries" || die "unsafe archive path"
tar -tvzf "$archive" | awk 'substr($0,1,1) != "-" && substr($0,1,1) != "d" {bad=1} END {exit bad}' || die "unexpected archive link or special file"
tar --no-same-owner --no-same-permissions -xzf "$archive" -C "$tmp"
payload="$tmp/oh-my-ztty"
[ -f "$payload/MANIFEST.sha256" ] || die "archive is missing its file manifest"
(cd "$payload" && sha256sum --quiet -c MANIFEST.sha256) || die "bundle content verification failed"
installed_version=$(cat "$payload/VERSION")
valid_version "$installed_version" || die "bundle version is invalid"
[ "$(cat "$payload/PLATFORM")" = "linux-$arch" ] || die "bundle architecture does not match this machine"
for exe in omztty ztty ssmcp zdot zshard zfetch zmem; do [ -x "$payload/bin/$exe" ] || die "bundle missing executable: $exe"; done
[ -f "$payload/components/zshard/zshard.zsh" ] || die "bundle missing zshard"
[ -f "$payload/config/zmem/zmem.conf" ] || die "bundle missing zmem configuration"
release_id="$installed_version-linux-$arch"
release="$base/releases/$release_id"
mkdir -p -- "$base/releases" "$bindir"
chmod 700 "$base"
if [ ! -f "$base/.owner" ]; then
    printf '%s\n' oh-my-ztty-v1 > "$base/.owner"
    printf '%s\n' "$bindir" > "$base/.bin-dir"
fi
if [ -e "$release" ] || [ -L "$release" ]; then
    [ -d "$release" ] && [ ! -L "$release" ] || die "release path is not an owned directory"
    [ -f "$release/.archive-sha256" ] && [ "$(cat "$release/.archive-sha256")" = "$actual" ] || die "this version is installed with different contents"
    (cd "$release" && sha256sum --quiet -c MANIFEST.sha256) || die "installed release was modified; preserving it"
else
    stage="$base/releases/.stage-$$"
    [ ! -e "$stage" ] || die "staging directory already exists"
    mkdir -- "$stage"
    cp -R "$payload/." "$stage/"
    printf '%s\n' "$actual" > "$stage/.archive-sha256"
    mv -T -- "$stage" "$release"
    stage=
fi
# Share the default fpath without running personal startup hooks during installation.
# Keep preparation before the active-version switch so a failure preserves it.
OMZTTY_ROOT="$release" ZDOTDIR="$release/config/zsh" \
ZSHARD_CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/oh-my-ztty/zshard/$release_id" \
    HISTFILE=/dev/null ZSHARD_PROMPT=off zsh -d -f -i -c '
        source "$OMZTTY_ROOT/config/zsh/completion-paths.zsh" || exit
        typeset -g ZSHARD_HOME="$OMZTTY_ROOT/components/zshard"
        source "$ZSHARD_HOME/zshard.zsh" && zshard complete
    ' || die "completion cache preparation failed; active version was not changed"
if [ "$memory_manager" = 1 ]; then
    printf 'Setting up zmem as the system memory manager.\n'
    if [ "$(id -u)" -eq 0 ]; then
        "$release/bin/zmem" install --replace --config "$release/config/zmem/zmem.conf" ||
            die "zmem setup failed; active suite version was not changed"
    else
        sudo -- "$release/bin/zmem" install --replace --config "$release/config/zmem/zmem.conf" ||
            die "zmem setup failed; active suite version was not changed"
    fi
fi
if [ ! -L "$base/current" ] || [ "$(readlink "$base/current")" != "releases/$release_id" ]; then
    [ ! -e "$base/current" ] || [ -L "$base/current" ] || die "current path is not a managed link"
    ln -s "releases/$release_id" "$base/.current.$$"
    mv -Tf -- "$base/.current.$$" "$base/current"
fi
for exe in omztty ztty ssmcp zdot zshard zfetch zmem; do
    target="$base/current/bin/$exe"
    if [ -e "$bindir/$exe" ] || [ -L "$bindir/$exe" ]; then
        if [ -L "$bindir/$exe" ] && [ "$(readlink "$bindir/$exe")" = "$target" ]; then :; else
            printf 'Preserved existing command: %s; bundled version is available through omztty.\n' "$bindir/$exe"
        fi
    else ln -s "$target" "$bindir/$exe"; fi
done
manpath="$datahome/man/man1/omztty.1"
if [ ! -e "$manpath" ] && [ ! -L "$manpath" ]; then
    mkdir -p -- "$datahome/man/man1"
    ln -s "$base/current/packaging/omztty.1" "$manpath"
fi
if [ "$desktop" = 1 ]; then
    mkdir -p -- "$datahome/applications"
    execpath=$(printf '%s' "$base/current/bin/omztty" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\$/\\$/g; s/%/%%/g')
    cat > "$tmp/oh-my-ztty.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Oh My Ztty
Comment=A lean terminal workspace built on Project Z
Exec="$execpath" terminal
Icon=$base/current/packaging/oh-my-ztty.svg
Terminal=false
X-TerminalArgExec=-e
Categories=System;TerminalEmulator;
Keywords=terminal;shell;zsh;AI;
StartupNotify=false
EOF
    if ! cmp -s "$tmp/oh-my-ztty.desktop" "$base/oh-my-ztty.desktop"; then cp "$tmp/oh-my-ztty.desktop" "$base/oh-my-ztty.desktop"; fi
    [ -L "$desktop_path" ] || ln -s "$base/oh-my-ztty.desktop" "$desktop_path"
    if [ ! -f "$base/.desktop-path" ] || [ "$(cat "$base/.desktop-path")" != "$desktop_path" ]; then printf '%s\n' "$desktop_path" > "$base/.desktop-path"; fi
else
    # Only suite-owned links are removed; a replacement file or foreign link stays.
    remove_desktop_link "$desktop_path"
    [ -z "$recorded_desktop" ] || remove_desktop_link "$recorded_desktop"
    rm -f -- "$base/.desktop-path"
fi
# Publish the preference only after preparation and installation have succeeded.
if [ "$saved_desktop" != "$desktop" ]; then
    preference_tmp=$(mktemp "$base/.desktop-enabled.XXXXXXXX")
    printf '%s\n' "$desktop" > "$preference_tmp"
    mv -Tf -- "$preference_tmp" "$desktop_preference"
    preference_tmp=
fi
if [ "$saved_memory" != "$memory_manager" ]; then
    memory_preference_tmp=$(mktemp "$base/.memory-manager-enabled.XXXXXXXX")
    printf '%s\n' "$memory_manager" > "$memory_preference_tmp"
    mv -Tf -- "$memory_preference_tmp" "$memory_preference"
    memory_preference_tmp=
fi
printf 'Installed oh-my-ztty %s\nRun: %s shell\nOpen a window: %s terminal\nUninstall: %s uninstall\n' "$installed_version" "$bindir/omztty" "$bindir/omztty" "$bindir/omztty"
if [ "$memory_manager" = 1 ]; then
    printf 'Memory: %s memory status\nRestore previous managers: %s memory rollback\n' "$bindir/omztty" "$bindir/omztty"
fi
case ":$PATH:" in *":$bindir:"*) ;; *) printf 'Add %s to PATH to use the short command names.\n' "$bindir" ;; esac
