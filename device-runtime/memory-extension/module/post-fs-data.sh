#!/system/bin/sh
set -eu
MODDIR=${0%/*}
STATE=/data/adb/sapphire-extm
mkdir -p "$STATE"
chmod 700 "$STATE"
exec > "$STATE/boot.log" 2>&1
echo 'Preparing encrypted zRAM writeback configuration'
rm -f "$STATE/prepared-boot"
# Only these two generated overlays are owned by this script.
rm -f "$MODDIR/system/vendor/bin/init.kernel.post_boot-bengal.sh" "$MODDIR/system/vendor/etc/fstab.zram"
mode=$(cat "$STATE/config" 2>/dev/null || echo 0)
case "$mode" in 0) echo disabled; exit 0;; 4|8) ;; *) echo 'Invalid configuration; using ROM default'; exit 0;; esac
[ "$(getprop ro.product.device)" = sapphire ] || exit 0
[ "$(uname -r)" = 5.15.189-chickernel-stable-7-ksun-server ] || exit 0
[ -w /sys/block/zram0/writeback ] && [ -r /sys/block/zram0/new_stat ] || exit 0
# Never reset or resize an active device. If the ROM initialized it already,
# retain the working ROM setup and report that initialization was too late.
[ "$(cat /sys/block/zram0/disksize)" = 0 ] || { echo 'ROM zRAM already initialized; preserving it'; exit 0; }
"$MODDIR/bin/check_per_boot_encryption" || { echo 'Required per-boot encryption unavailable'; exit 0; }
[ "$(sha256sum /vendor/bin/init.kernel.post_boot-bengal.sh | cut -d ' ' -f 1)" = 8656481392d0dd5577d2c86081daa48d66422e4629f20f33c836abbeb822c06d ] || exit 0
[ "$(sha256sum /vendor/etc/fstab.zram | cut -d ' ' -f 1)" = 872c7b08dcd8d27b65d95095aa0a6e1b46fb4618d16d686e62744d67cd6e7fb2 ] || exit 0
free_kb=$(df -Pk /data | tail -1 | awk '{print $4}')
[ "$free_kb" -ge $((mode * 1048576 + 16777216)) ] || { echo 'Insufficient free space while retaining 16 GiB reserve'; exit 0; }
for f in /sys/devices/platform/soc/4804000.ufshc/health_descriptor/life_time_estimation_a /sys/devices/platform/soc/4804000.ufshc/health_descriptor/life_time_estimation_b; do
    life=$(cat "$f")
    case "$life" in 0x0[1-6]) ;; *) echo 'Flash lifetime gate did not pass'; exit 0;; esac
done
case "$mode" in 4) zram_mb=6144;; 8) zram_mb=8192;; esac
# Per-boot keys are installed after this blocking Magisk stage. Prepare the
# ROM deferral here, then let the non-blocking service wait for the actual
# current boot key before allocating or initializing the backing device.
mkdir -p "$MODDIR/system/vendor/bin" "$MODDIR/system/vendor/etc"
prepared=0
trap 'if [ "$prepared" != 1 ]; then rm -f "$MODDIR/system/vendor/bin/init.kernel.post_boot-bengal.sh" "$MODDIR/system/vendor/etc/fstab.zram"; fi' EXIT
# Defer just the duplicate early initializer. All other Qualcomm tuning stays.
sed 's/^    configure_zram_parameters$/    : # Sapphire ExtM initializes after the current boot encryption key is available/' /vendor/bin/init.kernel.post_boot-bengal.sh > "$MODDIR/system/vendor/bin/init.kernel.post_boot-bengal.sh"
printf '# Sapphire Memory Extension initializes zram0 after per-boot key readiness.\n' > "$MODDIR/system/vendor/etc/fstab.zram"
chmod 755 "$MODDIR/system/vendor/bin/init.kernel.post_boot-bengal.sh"
chmod 644 "$MODDIR/system/vendor/etc/fstab.zram"
chcon u:object_r:vendor_file:s0 "$MODDIR/system/vendor/bin/init.kernel.post_boot-bengal.sh" "$MODDIR/system/vendor/etc/fstab.zram"
cat /proc/sys/kernel/random/boot_id > "$STATE/prepared-boot"
prepared=1
echo "Prepared deferred initialization: backing=${mode}GiB, zRAM=${zram_mb}MiB"
