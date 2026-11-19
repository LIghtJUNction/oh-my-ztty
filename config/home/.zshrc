# Managed by oh-my-ztty and zdot. Personal settings: ~/.config/oh-my-ztty/local.zsh
typeset -g OMZTTY_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/oh-my-ztty/current"
if [[ -r "$OMZTTY_ROOT/config/zsh/.zshrc" ]]; then
    source "$OMZTTY_ROOT/config/zsh/.zshrc"
else
    print -ru2 -- 'oh-my-ztty: install the suite, or restore with omztty config remove'
    PROMPT='%F{#d4a373}❯%f '
fi
