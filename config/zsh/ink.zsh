# Ink uses only zsh builtins; zshard owns Git refresh and command timing.
_omztty_ink_prompt() {
  emulate -L zsh
  local exit_code=$1 elapsed=$2 details='' begin='' end='' indicator='❯'
  local text=${ZSHARD_COLOR_PATH:-'#e8ded2'}
  local accent=${ZSHARD_COLOR_ACCENT:-'#d4a373'}
  local muted=${ZSHARD_COLOR_MUTED:-'#a3978b'}
  local error=${ZSHARD_COLOR_ERROR:-'#e59a91'}
  [[ ${ZSHARD_PROMPT:-minimal} == off ]] && return 0

  # The branch is escaped once by zshard, and never passed through a shell.
  [[ -n ${_ZSHARD_BRANCH-} ]] &&
    details+="  %F{$muted}· %F{$accent}${_ZSHARD_BRANCH}%f"
  (( exit_code )) && details+="  %F{$error}exit $exit_code%f"
  (( elapsed >= 2 )) && details+="  %F{$muted}${elapsed}s%f"
  (( EUID == 0 )) && indicator='#'
  if [[ ${ZSHARD_SHELL_INTEGRATION:-0} == 1 && -t 1 ]]; then
    begin=$'%{\e]133;A\a%}'
    end=$'%{\e]133;B\a%}'
  fi
  PROMPT=$'\n'"${begin}%F{$text}%B%3~%b%f${details}"$'\n'"%F{$accent}${indicator}%f ${end}"
  RPROMPT=''
  return 0
}
zshard theme _omztty_ink_prompt
