# Share the exact ordered completion inputs with installer cache preparation.
typeset -g OMZTTY_ROOT=${OMZTTY_ROOT:A}
typeset -gU fpath
fpath=("${XDG_CONFIG_HOME:-$HOME/.config}/oh-my-ztty/completions" "$OMZTTY_ROOT/packaging/completions" "${fpath[@]}")
