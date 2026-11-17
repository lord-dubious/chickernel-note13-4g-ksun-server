#!/system/bin/sh
MODDIR=${0%/*}
STATE=/data/adb/sapphire-extm
mkdir -p "$STATE"
chmod 700 "$STATE"
exec > "$STATE/controller.log" 2>&1
[ "$(cat "$STATE/prepared-boot" 2>/dev/null)" = "$(cat /proc/sys/kernel/random/boot_id)" ] || { echo 'ROM default initialization retained'; exit 0; }
mode=$(cat "$STATE/config" 2>/dev/null)
case "$mode" in 4|8) ;; *) exit 0;; esac
if [ "$(cat /sys/block/zram0/disksize)" = 0 ]; then
    ready=0
    for n in $(seq 1 60); do
        if "$MODDIR/bin/check_per_boot_key_ready" >/dev/null 2>&1; then ready=1; break; fi
        sleep 1
    done
    if [ "$ready" = 1 ] && /system/bin/sh "$MODDIR/activate.sh" "$mode"; then
        echo "Initialized ${mode}GiB after the current boot encryption key became available"
    else
        echo 'Extension unavailable; restoring the ROM-sized compressed swap without resetting an active device'
        if [ "$(cat /sys/block/zram0/disksize)" = 0 ]; then
            echo zstd > /sys/block/zram0/comp_algorithm
            echo 4294967296 > /sys/block/zram0/disksize
            /system/bin/mkswap /dev/block/zram0
            /system/bin/swapon -p 32758 /dev/block/zram0
        fi
        exit 0
    fi
fi
for n in $(seq 1 180); do
    [ "$(getprop sys.boot_completed)" = 1 ] && break
    sleep 1
done
# Confirm backing before starting the bounded writeback controller.
for n in $(seq 1 30); do
    [ "$(cat /sys/block/zram0/backing_dev)" != none ] && break
    sleep 1
done
[ "$(cat /sys/block/zram0/backing_dev)" != none ] || { echo 'No backing active; controller not started'; exit 0; }
"$MODDIR/bin/check_per_boot_encryption" || exit 1
day=-1
while [ ! -e "$MODDIR/disable" ] && [ ! -e "$MODDIR/remove" ]; do
    today=$(($(date +%s) / 86400))
    if [ "$today" != "$day" ]; then
        remaining=262144 # 1 GiB per UTC day, in 4 KiB pages.
        if [ -f "$STATE/quota" ]; then
            read -r saved_day saved_remaining < "$STATE/quota"
            case "$saved_remaining" in ''|*[!0-9]*) saved_remaining=0;; esac
            if [ "$saved_day" = "$today" ] && [ "$saved_remaining" -le 262144 ]; then remaining=$saved_remaining; fi
        fi
        echo "$remaining" > /sys/block/zram0/writeback_limit
        echo 1 > /sys/block/zram0/writeback_limit_enable
        day=$today
    fi
    remaining=$(cat /sys/block/zram0/writeback_limit)
    available=$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)
    total=$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)
    temp=$(cat /sys/class/power_supply/battery/temp)
    if [ "$remaining" -gt 0 ] && [ "$available" -lt $((total / 5)) ] && [ "$temp" -lt 400 ] && dumpsys power | grep -q 'mWakefulness=Asleep'; then
        echo all > /sys/block/zram0/idle
        pages=16384 # At most 64 MiB per pass; at least three idle marks.
        [ "$remaining" -lt "$pages" ] && pages=$remaining
        echo "idle $pages 3" > /sys/block/zram0/writeback
        remaining=$(cat /sys/block/zram0/writeback_limit)
    fi
    printf '%s %s\n' "$today" "$remaining" > "$STATE/quota.new"
    chmod 600 "$STATE/quota.new"
    mv "$STATE/quota.new" "$STATE/quota"
    sleep 300
done
