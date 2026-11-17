#!/system/bin/sh
set -eu
B=/data/local/codex-native-docker
D=$B/rootfs/usr/local/bin/docker
test "$(id -u)" = 0 || { echo 'Run with root permission'; exit 1; }
test "$(cat "$B/.codex-owner")" = sapphire-native-docker-v1
case "${1:-status}" in
shell)
    shift
    pid=$(cat "$B/mount-namespace.pid")
    case "$pid" in ''|*[!0-9]*) exit 2;; esac
    test "$(cat /proc/$pid/comm)" = dockerd
    export HOME=/root TMPDIR=/tmp PATH=/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
    export DOCKER_HOST="unix://$B/run/docker.sock" DOCKER_CONFIG="$B/client-config"
    unset LD_PRELOAD LD_LIBRARY_PATH
    exec /system/bin/nsenter -t "$pid" -m -- /bin/sh -l "$@"
    ;;
docker)
    shift
    export DOCKER_CONFIG="$B/client-config"
    export DOCKER_HOST="unix://$B/run/docker.sock"
    exec "$D" -H "unix://$B/run/docker.sock" "$@"
    ;;
status)
    exec "$D" -H "unix://$B/run/docker.sock" info --format '{{.ServerVersion}} {{.Architecture}} {{.CgroupVersion}} {{.Driver}}'
    ;;
stop)
    pid=$(cat "$B/mount-namespace.pid")
    case "$pid" in ''|*[!0-9]*) exit 2;; esac
    test "$(cat /proc/$pid/comm)" = dockerd
    test "$(cat "$B/run/dockerd.pid")" = "$pid"
    kill -TERM "$pid"
    for n in $(seq 1 30); do
        if ! kill -0 "$pid" 2>/dev/null; then
            npid=$(cat "$B/network.pid" 2>/dev/null || true)
            case "$npid" in ''|*[!0-9]*) ;; *)
                if [ -r "/proc/$npid/cmdline" ] && tr '\000' ' ' < "/proc/$npid/cmdline" | grep -F "$B/network.sh" >/dev/null; then
                    kill -TERM "$npid" 2>/dev/null || true
                    for n in $(seq 1 8); do
                        kill -0 "$npid" 2>/dev/null || break
                        sleep 1
                    done
                    if kill -0 "$npid" 2>/dev/null; then echo 'Routing worker has not stopped yet'; exit 1; fi
                fi
                ;;
            esac
            [ ! -f "$B/network.sh" ] || /system/bin/sh "$B/network.sh" --cleanup
            echo stopped; exit 0
        fi
        sleep 1
    done
    echo 'Docker has not stopped yet; no forced kill performed'
    exit 1
    ;;
start)
    if "$D" -H "unix://$B/run/docker.sock" info >/dev/null 2>&1; then
        if [ -f "$B/network.sh" ]; then
            /system/bin/sh "$B/network.sh" --prepare
            nohup /system/bin/sh "$B/network.sh" < /dev/null > "$B/network.log" 2>&1 &
        fi
        echo running; exit 0
    fi
    test -z "$(pidof dockerd || true)" || { echo 'Another Docker daemon exists'; exit 1; }
    boot=$(cat /proc/sys/kernel/random/boot_id)
    previous=$(cat "$B/boot-id" 2>/dev/null || true)
    if [ "$boot" != "$previous" ]; then
        # Only ephemeral runtime state is cleared after a confirmed new boot.
        # Container images/data in rootfs/var/lib/docker are retained.
        test "$(readlink -f "$B")" = /data/local/codex-native-docker
        test ! -L "$B/run"
        rm -rf /data/local/codex-native-docker/run
        mkdir -p "$B/run"
        echo "$boot" > "$B/boot-id"
    fi
    readlink /proc/self/ns/mnt > "$B/launch-parent-mnt"
    [ ! -f "$B/network.sh" ] || /system/bin/sh "$B/network.sh" --prepare
    nohup unshare -m /system/bin/sh "$B/bootstrap.sh" < /dev/null > "$B/daemon.log" 2>&1 &
    if [ -f "$B/network.sh" ]; then
        nohup /system/bin/sh "$B/network.sh" < /dev/null > "$B/network.log" 2>&1 &
    fi
    echo 'Docker starting'
    ;;
*) echo 'Use start, stop, status, shell, or docker <arguments>'; exit 2;;
esac
