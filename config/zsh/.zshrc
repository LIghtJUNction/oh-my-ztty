# Shared entry for omztty shell and the zdot-managed default shell.
[[ -o interactive ]] || return 0
(( ${+_OMZTTY_INITIALIZED} )) && return 0
typeset -g _OMZTTY_INITIALIZED=1
source "$OMZTTY_ROOT/config/zsh/completion-paths.zsh" || return
typeset -g ZSHARD_HOME="$OMZTTY_ROOT/components/zshard"
typeset -g ZSHARD_SHELL_INTEGRATION=1
typeset -gU path
path=("$OMZTTY_ROOT/bin" "$HOME/.local/bin" "${path[@]}")
[[ ! -r "$OMZTTY_ROOT/config/zsh/settings.zsh" ]] || source "$OMZTTY_ROOT/config/zsh/settings.zsh" --env
typeset -g ZSHARD_CACHE_DIR=${ZSHARD_CACHE_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/oh-my-ztty/zshard/${OMZTTY_ROOT:t}}
typeset -g HISTFILE=${XDG_STATE_HOME:-$HOME/.local/state}/oh-my-ztty/history
[[ -d ${HISTFILE:h} ]] || (umask 077; command mkdir -p -- "${HISTFILE:h}")
# Keep the shell word intact while locating slashes in escaped or quoted paths.
_omztty_backward_kill_path() {
    emulate -L zsh
    setopt extendedglob
    local -a words=( "${(@Z:n:)LBUFFER}" )
    local word=$words[-1]
    if [[ $word != */* ]]; then
        zle .backward-kill-word
        return
    fi
    # Leave a closing quote to the right of the cursor for continued editing.
    if [[ $LBUFFER == *"$word" && (
          $word == \'*\' || ( $word == \"*\" && ${word[-2]} != \\ )
    ) ]]; then
        (( CURSOR-- ))
        word=${word[1,-2]}
    fi
    local prefix=${LBUFFER%${word}[[:space:]]#}
    local stem=${word%%/##}
    if [[ $stem == */* ]]; then
        prefix+=${stem%/*}/
    elif [[ ${word[1]} == \' || ${word[1]} == \" ]]; then
        prefix+=${word[1]}
    fi
    local MARK=${#prefix}
    zle .kill-region
}
zle -N omztty-backward-kill-path _omztty_backward_kill_path
bindkey -M emacs '^W' omztty-backward-kill-path
bindkey -M viins '^W' omztty-backward-kill-path
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
[[ ! -r "$OMZTTY_ROOT/config/zsh/settings.zsh" ]] || source "$OMZTTY_ROOT/config/zsh/settings.zsh" --rc
