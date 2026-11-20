# Managed by oh-my-ztty and zdot. Personal settings: ~/.config/oh-my-ztty/local.zsh
if [[ -z ${OMZTTY_ROOT:-} ]]; then
    typeset -g OMZTTY_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/oh-my-ztty/current"
    if [[ ! -r "$OMZTTY_ROOT/config/zsh/.zshrc" && -n ${commands[omztty]:-} ]]; then
        OMZTTY_ROOT="${commands[omztty]:A:h:h}"
    fi
fi
if [[ -r "$OMZTTY_ROOT/config/zsh/.zshrc" ]]; then
    source "$OMZTTY_ROOT/config/zsh/.zshrc"
else
    print -ru2 -- 'oh-my-ztty: install the suite, or restore with omztty config remove'
    PROMPT='%F{#d4a373}❯%f '
fi
