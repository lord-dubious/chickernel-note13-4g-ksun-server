#!/system/bin/sh
set -eu
B=/data/local/codex-native-docker
R=$B/rootfs
BB=/data/adb/magisk/busybox
test "$(cat "$B/.codex-owner")" = sapphire-native-docker-v1
test "$(uname -r)" = 5.15.189-chickernel-stable-7-ksun-server
test "$(id -u)" = 0
# This script must be entered after unshare -m. Never alter host propagation.
test "$(readlink /proc/self/ns/mnt)" != "$(cat "$B/launch-parent-mnt")"
$BB mount --make-rprivate /
echo $$ > "$B/mount-namespace.pid"
# Docker's extraction and runc helpers change propagation on their root.
# A chroot directory must therefore be an actual private mount point.
$BB mount --bind "$R" "$R"
$BB mount --make-rprivate "$R"
mkdir -p "$R/proc" "$R/sys" "$R/dev" "$R/run" "$B/run"
$BB mount -t proc proc "$R/proc"
$BB mount --rbind /dev "$R/dev"
$BB mount --rbind /sys "$R/sys"
$BB mount --bind "$B/run" "$R/run"
for share in workspace cli-plugins client-config run; do
    mkdir -p "$B/$share" "$R$B/$share"
    $BB mount --bind "$B/$share" "$R$B/$share"
done
# Use the phone's exact iptables binaries and shared xtables lock. These
# read-only Android runtime mounts are for the daemon, not default containers.
for part in system apex linkerconfig vendor system_ext odm; do
    mkdir -p "$R/$part"
    $BB mount --rbind "/$part" "$R/$part"
done
$BB mount -t tmpfs -o mode=755,nosuid,nodev tmpfs "$R/sys/fs/cgroup"
for spec in cpu:/dev/cpuctl memory:/dev/memcg cpuset:/dev/cpuset blkio:/dev/blkio; do
    name=${spec%%:*}; source=${spec#*:}
    mkdir -p "$R/sys/fs/cgroup/$name"
    $BB mount --bind "$source" "$R/sys/fs/cgroup/$name"
done
for name in cpuacct devices freezer pids; do
    # Existing Android pids limits must not be displaced.
    if [ "$name" = pids ]; then
        test -z "$(find /sys/fs/cgroup -maxdepth 3 -name pids.max -print -quit)"
    fi
    mkdir -p "$R/sys/fs/cgroup/$name"
    $BB mount -t cgroup -o "$name" cgroup "$R/sys/fs/cgroup/$name"
done
mkdir -p "$R/etc/docker"
printf 'nameserver 1.1.1.1\nnameserver 1.0.0.1\n' > "$R/etc/resolv.conf"
export PATH=/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export TMPDIR=/tmp HOME=/root
unset LD_PRELOAD LD_LIBRARY_PATH DOCKER_RAMDISK DOCKER_TMPDIR
export SAPPHIRE_SERVER_PARENT_MNT="$(cat "$B/launch-parent-mnt")"
exec "$R/usr/local/bin/nsroot-launch" "$R"
