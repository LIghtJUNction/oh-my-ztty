# Shared entry for omztty shell and the zdot-managed default shell.
[[ -o interactive ]] || return 0
(( ${+_OMZTTY_INITIALIZED} )) && return 0
typeset -g _OMZTTY_INITIALIZED=1
typeset -g OMZTTY_ROOT=${OMZTTY_ROOT:A}
typeset -g ZSHARD_HOME="$OMZTTY_ROOT/components/zshard"
typeset -g ZSHARD_SHELL_INTEGRATION=1
typeset -gU path fpath
path=("$OMZTTY_ROOT/bin" "$HOME/.local/bin" "${path[@]}")
typeset -g ZSHARD_CACHE_DIR=${ZSHARD_CACHE_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/oh-my-ztty/zshard/${OMZTTY_ROOT:t}}
typeset -g HISTFILE=${XDG_STATE_HOME:-$HOME/.local/state}/oh-my-ztty/history
[[ -d ${HISTFILE:h} ]] || (umask 077; command mkdir -p -- "${HISTFILE:h}")
fpath=("${XDG_DATA_HOME:-$HOME/.local/share}/oh-my-ztty/completions" "$OMZTTY_ROOT/packaging/completions" "${fpath[@]}")
if [[ -r "${XDG_CONFIG_HOME:-$HOME/.config}/oh-my-ztty/options.zsh" ]]; then
    source "${XDG_CONFIG_HOME:-$HOME/.config}/oh-my-ztty/options.zsh"
fi
source "$ZSHARD_HOME/zshard.zsh"
if [[ ${OMZTTY_THEME:-ink} == ink && ${ZSHARD_PROMPT:-minimal} != off && -z ${ZSHARD_PROMPT_FUNCTION-} ]]; then
    source "$OMZTTY_ROOT/config/zsh/ink.zsh"
fi
# zrc's shell options are static assignments, with no process or network startup.
if [[ -r "${XDG_CONFIG_HOME:-$HOME/.config}/zrc/shell.zsh" ]]; then
    source "${XDG_CONFIG_HOME:-$HOME/.config}/zrc/shell.zsh"
fi
if [[ -r "${XDG_CONFIG_HOME:-$HOME/.config}/oh-my-ztty/local.zsh" ]]; then
    source "${XDG_CONFIG_HOME:-$HOME/.config}/oh-my-ztty/local.zsh"
fi
