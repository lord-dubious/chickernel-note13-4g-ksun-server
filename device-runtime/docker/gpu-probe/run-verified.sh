#!/system/bin/sh
set -eu
[ "$(id -u)" = 0 ] || { echo 'Root permission is required'; exit 1; }
W=/data/local/codex-native-docker/workspace/gpu-probe
set -- docker run --rm --network none --memory 256m --pids-limit 128 --cap-drop ALL
for path in /system /apex /linkerconfig /vendor /system_ext /odm /dev/__properties__; do
    set -- "$@" --mount "type=bind,src=$path,dst=$path,readonly"
done
set -- "$@" --mount "type=bind,src=$W,dst=/data/local/tmp/gpu-probe,readonly"
for device in /dev/kgsl-3d0 /dev/binder /dev/hwbinder /dev/vndbinder; do
    if [ -e "$device" ]; then
        numbers=$(stat -L -c '%t %T' "$device")
        major=${numbers% *}
        minor=${numbers#* }
        set -- "$@" --device-cgroup-rule "c $((0x$major)):$((0x$minor)) rw" --mount "type=bind,src=$device,dst=$device"
    fi
done
exec "$@" codex/alpine:3.24.4-arm64 /data/local/tmp/gpu-probe/probe /data/local/tmp/gpu-probe/probe.spv
