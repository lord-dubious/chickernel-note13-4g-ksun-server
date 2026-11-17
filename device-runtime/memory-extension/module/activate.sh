#!/system/bin/sh
# Equivalent guarded setup sequence to Android fs_mgr's zRAM backing setup.
set -eu
MODDIR=${0%/*}
mode=${1:-}
case "$mode" in
    4) bytes=6442450944; backing_bytes=4294967296;;
    8) bytes=8589934592; backing_bytes=8589934592;;
    *) exit 2;;
esac
[ "$(uname -r)" = 5.15.189-chickernel-stable-7-ksun-server ]
[ "$(getprop ro.product.device)" = sapphire ]
"$MODDIR/bin/check_per_boot_encryption"
Z=/sys/block/zram0
BACKING=/data/per_boot/zram_swap
[ "$(cat "$Z/disksize")" = 0 ] || { echo 'Preserving already-initialized zRAM'; exit 1; }
! grep -q '^/dev/[^[:space:]]*zram0[[:space:]]' /proc/swaps
[ ! -L "$BACKING" ]
[ -z "$(/system/bin/losetup -j "$BACKING" 2>/dev/null)" ]
loop=
attached=0
active=0
cleanup() {
    rc=$?
    trap - EXIT HUP INT TERM
    if [ "$active" != 1 ]; then
        # This script started from an uninitialized, inactive zram0. Never
        # reset a device if another process has activated it in the meantime.
        if ! grep -q '^/dev/[^[:space:]]*zram0[[:space:]]' /proc/swaps; then
            [ "$attached" = 0 ] || echo 1 > "$Z/reset"
            if [ -n "$loop" ] && /system/bin/losetup -j "$BACKING" | grep -F "$loop:" >/dev/null; then
                /system/bin/losetup -d "$loop"
            fi
            rm -f "$BACKING"
        fi
    fi
    exit "$rc"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
umask 077
/system/bin/fallocate -l "$backing_bytes" "$BACKING"
chmod 600 "$BACKING"
loop=$(/system/bin/losetup -f -s "$BACKING")
case "$loop" in /dev/block/loop[0-9]*) ;; *) exit 3;; esac
"$MODDIR/bin/loop_directio" "$loop" "$BACKING"
echo "$loop" > "$Z/backing_dev"
attached=1
"$MODDIR/bin/loop_directio" "$loop" "$BACKING" --autoclear
echo lzo-rle > "$Z/comp_algorithm"
echo "$bytes" > "$Z/disksize"
echo 262144 > "$Z/writeback_limit"
echo 1 > "$Z/writeback_limit_enable"
/system/bin/mkswap /dev/block/zram0
/system/bin/swapon -p 32758 /dev/block/zram0
active=1
echo "Memory extension active: ${mode}GiB encrypted backing, $bytes bytes zRAM"
