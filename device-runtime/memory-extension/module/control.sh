#!/system/bin/sh
set -eu
STATE=/data/adb/sapphire-extm
test "$(id -u)" = 0 || { echo 'Root permission required'; exit 1; }
mkdir -p "$STATE"
chmod 700 "$STATE"
case "${1:-status}" in
set)
    case "${2:-}" in 0|4|8) ;; *) echo 'Choose 0, 4 or 8 GiB'; exit 2;; esac
    printf '%s\n' "$2" > "$STATE/config.new"
    chmod 600 "$STATE/config.new"
    mv "$STATE/config.new" "$STATE/config"
    echo 'Saved. Restart the phone to apply; active swap was not changed.'
    ;;
status)
    configured=$(cat "$STATE/config" 2>/dev/null || echo 0)
    case "$configured" in 0|4|8) ;; *) configured=0;; esac
    physical=$(awk '/^MemTotal:/ {printf "%.0f", $2 * 1024}' /proc/meminfo)
    zram=$(cat /sys/block/zram0/disksize)
    backing=$(cat /sys/block/zram0/backing_dev)
    effective=0
    if [ "$backing" != none ] && [ -f /data/per_boot/zram_swap ]; then
        size=$(stat -c %s /data/per_boot/zram_swap)
        effective=$(awk -v bytes="$size" 'BEGIN {printf "%.0f", bytes / 1073741824}')
        case "$effective" in 4|8) ;; *) effective=0;; esac
    fi
    algorithm=$(cat /sys/block/zram0/comp_algorithm | sed -n 's/.*\[\([^]]*\)\].*/\1/p')
    budget=$(cat /sys/block/zram0/writeback_limit 2>/dev/null || echo 0)
    written=$(awk '{print $3}' /sys/block/zram0/bd_stat)
    printf '{"configured_gib":%s,"effective_gib":%s,"physical_bytes":%.0f,"zram_bytes":%s,"algorithm":"%s","remaining_write_pages":%s,"written_pages":%s}\n' "$configured" "$effective" "$physical" "$zram" "$algorithm" "$budget" "$written"
    ;;
*) echo 'Use status or set <0|4|8>'; exit 2;;
esac
