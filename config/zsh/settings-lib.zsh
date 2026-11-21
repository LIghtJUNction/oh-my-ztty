# Data readers shared by the shell and management commands. Never evaluate data.
_omztty_valid_env_name() {
    emulate -L zsh
    setopt extendedglob
    local _omztty_name=$1 _omztty_type
    [[ $_omztty_name == [A-Za-z_][A-Za-z0-9_]# ]] || return 1
    case $_omztty_name in
        PATH|HOME|ZDOTDIR|XDG_CONFIG_HOME|XDG_STATE_HOME|OMZTTY_ROOT|OMZTTY_USER_ZDOTDIR|_OMZTTY_*|_omztty_*) return 1 ;;
    esac
    _omztty_type=${(tP)_omztty_name}
    [[ -z $_omztty_type || ( $_omztty_type == scalar* && $_omztty_type != *special* && $_omztty_type != *readonly* ) ]]
}

_omztty_read_env() {
    emulate -L zsh
    local _omztty_file=$1 _omztty_line _omztty_key _omztty_value
    local -i _omztty_number=0
    _omztty_data=()
    [[ -e $_omztty_file || -L $_omztty_file ]] || return 0
    [[ -f $_omztty_file && ! -L $_omztty_file ]] || {
        print -ru2 -- "oh-my-ztty: expected a regular environment file: $_omztty_file"; return 1
    }
    while IFS= read -r _omztty_line || [[ -n $_omztty_line ]]; do
        (( ++_omztty_number ))
        [[ -z $_omztty_line || $_omztty_line == \#* ]] && continue
        _omztty_key=${_omztty_line%%$'\t'*}
        _omztty_value=${_omztty_line#*$'\t'}
        if [[ $_omztty_line != *$'\t'* || $_omztty_value == *[$'\t\r']* ]] ||
                ! _omztty_valid_env_name "$_omztty_key" || (( ${+_omztty_data[$_omztty_key]} )); then
            print -ru2 -- "oh-my-ztty: invalid or duplicate variable at $_omztty_file:$_omztty_number"; return 1
        fi
        _omztty_data[$_omztty_key]=$_omztty_value
    done < "$_omztty_file"
}

_omztty_valid_path() {
    [[ $1 == /* || $1 == '~' || $1 == '~/'* ]] && [[ $1 != *[$':\t\r\n']* ]]
}

_omztty_read_paths() {
    emulate -L zsh
    local _omztty_file=$1 _omztty_line _omztty_place _omztty_directory
    local -A _omztty_seen
    local -i _omztty_number=0
    _omztty_paths=() _omztty_places=()
    [[ -e $_omztty_file || -L $_omztty_file ]] || return 0
    [[ -f $_omztty_file && ! -L $_omztty_file ]] || {
        print -ru2 -- "oh-my-ztty: expected a regular PATH file: $_omztty_file"; return 1
    }
    while IFS= read -r _omztty_line || [[ -n $_omztty_line ]]; do
        (( ++_omztty_number ))
        [[ -z $_omztty_line || $_omztty_line == \#* ]] && continue
        _omztty_place=${_omztty_line%%$'\t'*}
        _omztty_directory=${_omztty_line#*$'\t'}
        if [[ $_omztty_line != *$'\t'* || ( $_omztty_place != prepend && $_omztty_place != append ) ]] ||
                ! _omztty_valid_path "$_omztty_directory" || (( ${+_omztty_seen[$_omztty_directory]} )); then
            print -ru2 -- "oh-my-ztty: invalid or duplicate PATH rule at $_omztty_file:$_omztty_number"; return 1
        fi
        _omztty_seen[$_omztty_directory]=1
        _omztty_places+=("$_omztty_place") _omztty_paths+=("$_omztty_directory")
    done < "$_omztty_file"
}
