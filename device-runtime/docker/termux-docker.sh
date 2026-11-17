#!/data/data/com.termux/files/usr/bin/sh
# Quote each argument separately before passing the fixed root client command.
quote_arg() {
    printf "'"
    printf '%s' "$1" | sed "s/'/'\\\\''/g"
    printf "'"
}
command='/system/bin/sh /data/local/codex-native-docker/control.sh docker'
for arg in "$@"; do command="$command $(quote_arg "$arg")"; done
exec su -c "$command"
