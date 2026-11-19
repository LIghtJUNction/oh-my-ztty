# Loaded only by omztty shell; ordinary zsh configuration remains independent.
typeset -g ZSHARD_HOME="$OMZTTY_ROOT/components/zshard"
typeset -g ZSHARD_SHELL_INTEGRATION=1
fpath=("$OMZTTY_ROOT/packaging/completions" $fpath)
if [[ -r "${XDG_CONFIG_HOME:-$HOME/.config}/oh-my-ztty/options.zsh" ]]; then
    source "${XDG_CONFIG_HOME:-$HOME/.config}/oh-my-ztty/options.zsh"
fi
source "$ZSHARD_HOME/zshard.zsh"
if [[ ${OMZTTY_THEME:-ink} == ink && ${ZSHARD_PROMPT:-minimal} != off && -z ${ZSHARD_PROMPT_FUNCTION-} ]]; then
    source "$OMZTTY_ROOT/config/zsh/ink.zsh"
fi
if [[ -r "${XDG_CONFIG_HOME:-$HOME/.config}/oh-my-ztty/local.zsh" ]]; then
    source "${XDG_CONFIG_HOME:-$HOME/.config}/oh-my-ztty/local.zsh"
fi
