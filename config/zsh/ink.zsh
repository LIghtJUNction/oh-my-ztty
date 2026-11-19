# Ink preset: zsh builtins only; the framework owns Git refresh and timing.
_omztty_ink_prompt() {
  emulate -L zsh
  local exit_code=$1 elapsed=$2 details='' begin='' end='' indicator='❯'
  [[ ${ZSHARD_PROMPT:-minimal} == off ]] && return 0

  # This field is escaped by the pinned zshard version; do not escape it twice.
  [[ -n ${_ZSHARD_BRANCH-} ]] &&
    details+="  %F{8}on %F{6}${_ZSHARD_BRANCH}%f"
  (( exit_code )) && details+="  %F{1}exit $exit_code%f"
  (( elapsed >= 2 )) && details+="  %F{8}${elapsed}s%f"
  (( EUID == 0 )) && indicator='#'

  if [[ ${ZSHARD_SHELL_INTEGRATION:-0} == 1 && -t 1 ]]; then
    begin=$'%{\e]133;A\a%}'
    end=$'%{\e]133;B\a%}'
  fi
  PROMPT=$'\n'"${begin}%F{4}%B%~%b%f${details}"$'\n'"%F{6}${indicator}%f ${end}"
  RPROMPT=''
  return 0
}
zshard theme _omztty_ink_prompt
