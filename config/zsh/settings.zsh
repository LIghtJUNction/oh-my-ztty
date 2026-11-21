# Source this file to reload managed values in the current zsh.
# The preset loads data before plugins and rc fragments after its own setup.
source "${${(%):-%N}:A:h}/settings-lib.zsh" || return

_omztty_load_settings() {
    emulate -L zsh
    local _omztty_mode=${1:-all}
    local _omztty_config=${XDG_CONFIG_HOME:-$HOME/.config}/oh-my-ztty
    local _omztty_shell=$_omztty_config/profile/shell
    local _omztty_key _omztty_value _omztty_file _omztty_directory _omztty_entry
    local -A _omztty_data _omztty_values
    local -a _omztty_paths _omztty_places _omztty_before _omztty_after _omztty_base _omztty_result _omztty_added
    local -i _omztty_i
    if [[ $_omztty_mode != --rc ]]; then
        _omztty_read_env "$_omztty_shell/env.tsv" || return
        _omztty_values=("${(@kv)_omztty_data}")
        _omztty_read_env "$_omztty_config/local/env.tsv" || return
        for _omztty_key _omztty_value in "${(@kv)_omztty_data}"; do
            _omztty_values[$_omztty_key]=$_omztty_value
        done
        _omztty_read_paths "$_omztty_shell/path.tsv" || return
        typeset -gA _OMZTTY_ENV_ORIGINAL _OMZTTY_ENV_PRESENT _OMZTTY_ENV_EXPORTED _OMZTTY_ENV_APPLIED
        # Restore inherited values when an applied rule is removed on reload.
        for _omztty_key in "${(@k)_OMZTTY_ENV_APPLIED}"; do
            if (( ! ${+_omztty_values[$_omztty_key]} )); then
                if [[ ${(P)_omztty_key} == ${_OMZTTY_ENV_APPLIED[$_omztty_key]} ]]; then
                    if [[ ${_OMZTTY_ENV_PRESENT[$_omztty_key]} == 1 ]]; then
                        typeset -g -- "$_omztty_key=${_OMZTTY_ENV_ORIGINAL[$_omztty_key]}"
                        [[ ${_OMZTTY_ENV_EXPORTED[$_omztty_key]} == 1 ]] || typeset -g +x "$_omztty_key"
                    else
                        unset "$_omztty_key"
                    fi
                fi
                unset "_OMZTTY_ENV_APPLIED[$_omztty_key]" "_OMZTTY_ENV_ORIGINAL[$_omztty_key]" \
                    "_OMZTTY_ENV_PRESENT[$_omztty_key]" "_OMZTTY_ENV_EXPORTED[$_omztty_key]"
            fi
        done
        for _omztty_key _omztty_value in "${(@kv)_omztty_values}"; do
            if (( ! ${+_OMZTTY_ENV_APPLIED[$_omztty_key]} )); then
                _OMZTTY_ENV_ORIGINAL[$_omztty_key]=${(P)_omztty_key}
                _OMZTTY_ENV_PRESENT[$_omztty_key]=${(P)+_omztty_key}
                _OMZTTY_ENV_EXPORTED[$_omztty_key]=0
                [[ ${(tP)_omztty_key} == *export* ]] && _OMZTTY_ENV_EXPORTED[$_omztty_key]=1
            fi
            typeset -gx -- "$_omztty_key=$_omztty_value"
            _OMZTTY_ENV_APPLIED[$_omztty_key]=$_omztty_value
        done

        typeset -ga _OMZTTY_PATH_BASE _OMZTTY_PATH_ADDED
        if (( ${+_OMZTTY_PATH_EFFECTIVE} )) && [[ $PATH == $_OMZTTY_PATH_EFFECTIVE ]]; then
            _omztty_base=("${_OMZTTY_PATH_BASE[@]}")
        else
            # A venv or another tool may have changed PATH since the last load.
            for _omztty_entry in "${path[@]}"; do
                (( ${_OMZTTY_PATH_ADDED[(Ie)$_omztty_entry]} )) || _omztty_base+=("$_omztty_entry")
            done
        fi
        _OMZTTY_PATH_BASE=("${_omztty_base[@]}")
        for (( _omztty_i=1; _omztty_i <= ${#_omztty_paths}; ++_omztty_i )); do
            _omztty_directory=${_omztty_paths[$_omztty_i]}
            [[ $_omztty_directory == '~' ]] && _omztty_directory=$HOME
            [[ $_omztty_directory == '~/'* ]] && _omztty_directory=$HOME/${_omztty_directory#'~/'}
            (( ${_omztty_base[(Ie)$_omztty_directory]} )) || _omztty_added+=("$_omztty_directory")
            if [[ ${_omztty_places[$_omztty_i]} == prepend ]]; then
                _omztty_before+=("$_omztty_directory")
            else
                _omztty_after+=("$_omztty_directory")
            fi
        done
        for _omztty_entry in "${_omztty_base[@]}"; do
            if (( ! ${_omztty_before[(Ie)$_omztty_entry]} && ! ${_omztty_after[(Ie)$_omztty_entry]} )); then
                _omztty_result+=("$_omztty_entry")
            fi
        done
        path=("${_omztty_before[@]}" "${_omztty_result[@]}" "${_omztty_after[@]}")
        export PATH
        typeset -g _OMZTTY_PATH_EFFECTIVE=$PATH
        _OMZTTY_PATH_ADDED=("${_omztty_added[@]}")
    fi
}

_omztty_load_settings "$@" || return
# Source user snippets at file scope so their shell options and declarations persist.
if [[ ${1:-all} != --env ]]; then
    typeset -g _OMZTTY_SETTINGS_LOADED=1
    for _omztty_rc_file in "${XDG_CONFIG_HOME:-$HOME/.config}/oh-my-ztty/profile/shell"/rc.d/*.zsh(N.); do
        source "$_omztty_rc_file" || return
    done
    unset _omztty_rc_file
fi
