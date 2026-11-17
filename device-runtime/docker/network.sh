#!/system/bin/sh
set -eu
B=/data/local/codex-native-docker
POOL=172.30.240.0/20
TABLE=45201
DEST_PRIO=12001
SOURCE_PRIO=13590
test "$(cat "$B/.codex-owner")" = sapphire-native-docker-v1
test "$(id -u)" = 0

cleanup() {
    test "$(cat "$B/network.owner" 2>/dev/null)" = sapphire-docker-network-v1 || return 0
    ip -4 rule del priority "$DEST_PRIO" to "$POOL" table main 2>/dev/null || true
    ip -4 rule del priority "$SOURCE_PRIO" from "$POOL" table "$TABLE" 2>/dev/null || true
    ip -4 route flush table "$TABLE" 2>/dev/null || true
}

prepare() {
    if [ ! -f "$B/network.owner" ]; then
        test -z "$(ip -4 route show table "$TABLE")" || { echo 'Routing table is already used'; return 1; }
        test -z "$(ip -4 rule show | grep -E "^($DEST_PRIO|$SOURCE_PRIO):")" || { echo 'Routing priorities are already used'; return 1; }
        echo sapphire-docker-network-v1 > "$B/network.owner"
        chmod 600 "$B/network.owner"
    fi
    test "$(cat "$B/network.owner")" = sapphire-docker-network-v1
    rules=$(ip -4 rule show)
    line=$(printf '%s\n' "$rules" | grep "^$DEST_PRIO:" || true)
    if [ -n "$line" ]; then
        printf '%s\n' "$line" | grep -F "to $POOL lookup main" >/dev/null || { echo 'Destination routing priority conflicts'; return 1; }
    else
        ip -4 rule add priority "$DEST_PRIO" to "$POOL" table main
    fi
    line=$(printf '%s\n' "$rules" | grep "^$SOURCE_PRIO:" || true)
    if [ -n "$line" ]; then
        printf '%s\n' "$line" | grep -F "from $POOL lookup $TABLE" >/dev/null || { echo 'Source routing priority conflicts'; return 1; }
    else
        ip -4 rule add priority "$SOURCE_PRIO" from "$POOL" table "$TABLE"
    fi
    uplink=$(ip -4 route get 1.1.1.1 2>/dev/null || true)
    iface=$(printf '%s\n' "$uplink" | awk '{for(i=1;i<NF;i++) if($i=="dev") {print $(i+1);exit}}')
    gateway=$(printf '%s\n' "$uplink" | awk '{for(i=1;i<NF;i++) if($i=="via") {print $(i+1);exit}}')
    case "$iface" in ''|lo|dummy0)
        ip -4 route del table "$TABLE" default 2>/dev/null || true
        return 0
        ;;
    esac
    if [ -n "$gateway" ]; then
        ip -4 route replace table "$TABLE" default via "$gateway" dev "$iface" onlink
    else
        ip -4 route replace table "$TABLE" default dev "$iface"
    fi
}

case "${1:-watch}" in
--prepare) prepare; exit;;
--cleanup) cleanup; exit;;
watch) ;;
*) exit 2;;
esac
old=$(cat "$B/network.pid" 2>/dev/null || true)
case "$old" in ''|*[!0-9]*) ;; *)
    if [ -r "/proc/$old/cmdline" ] && tr '\000' ' ' < "/proc/$old/cmdline" | grep -F "$B/network.sh" >/dev/null; then exit 0; fi
    ;;
esac
echo $$ > "$B/network.pid"
chmod 600 "$B/network.pid"
child=
trap 'cleanup; rm -f "$B/network.pid"' EXIT
trap '[ -z "$child" ] || kill "$child" 2>/dev/null || true; exit 143' TERM INT HUP
for n in $(seq 1 30); do
    pid=$(cat "$B/mount-namespace.pid" 2>/dev/null || true)
    case "$pid" in ''|*[!0-9]*) ;; *) [ "$(cat /proc/$pid/comm 2>/dev/null)" = dockerd ] && break;; esac
    sleep 1
done
while [ "$(cat /proc/$pid/comm 2>/dev/null)" = dockerd ]; do
    prepare
    sleep 30 &
    child=$!
    wait "$child" || true
    child=
done
