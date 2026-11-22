# Share the exact ordered completion inputs with installer cache preparation.
typeset -g OMZTTY_ROOT=${OMZTTY_ROOT:A}
typeset -gU fpath

# Only read a private pointer. No generators, applications or network requests
# run during startup or Tab. A content-addressed directory also invalidates
# zshard's audited cache when a completion changes without changing its name.
_omztty_managed_completions() {
    emulate -L zsh
    setopt extendedglob
    REPLY=''
    local base=${XDG_CACHE_HOME:-$HOME/.cache}/oh-my-ztty/completions/${OMZTTY_ROOT:t}
    local generation candidate
    local -A metadata
    [[ -f $base/current && ! -L $base/current ]] || return 0
    zmodload -F zsh/stat b:zstat || return 0
    generation=$(<"$base/current")
    [[ ${#generation} == 64 && $generation == [0-9a-f]## ]] || return 0
    for candidate in "$base" "$base/generations" "$base/current" "$base/generations/$generation"; do
        [[ -O $candidate && ! -L $candidate ]] || return 0
        zstat -H metadata -- "$candidate" 2>/dev/null || return 0
        (( (metadata[mode] & 8#22) == 0 )) || return 0
    done
    [[ -d $base/generations/$generation ]] && REPLY=$base/generations/$generation
    return 0
}
_omztty_managed_completions
fpath=("${XDG_CONFIG_HOME:-$HOME/.config}/oh-my-ztty/completions" ${REPLY:+"$REPLY"} "$OMZTTY_ROOT/packaging/completions" "${fpath[@]}")
unfunction _omztty_managed_completions
