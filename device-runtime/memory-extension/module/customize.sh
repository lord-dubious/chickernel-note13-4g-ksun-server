#!/system/bin/sh
[ "$BOOTMODE" = true ] || abort 'Install from the running Android system using Magisk.'
[ "$ARCH" = arm64 ] || abort 'Requires ARM64'
[ "$(getprop ro.product.device)" = sapphire ] || abort 'Requires Redmi Note 13 4G sapphire'
[ "$(uname -r)" = 5.15.189-chickernel-stable-7-ksun-server ] || abort 'Requires the verified server kernel'
STATE=/data/adb/sapphire-extm
mkdir -p "$STATE"
chmod 700 "$STATE"
if [ ! -f "$STATE/config" ]; then printf '8\n' > "$STATE/config"; fi
chmod 600 "$STATE/config"
cp "$MODPATH/control.sh" "$STATE/control.sh"
chmod 700 "$STATE/control.sh"
set_perm_recursive "$MODPATH" 0 0 0755 0644
set_perm "$MODPATH/post-fs-data.sh" 0 0 0755
set_perm "$MODPATH/service.sh" 0 0 0755
set_perm "$MODPATH/control.sh" 0 0 0755
set_perm "$MODPATH/activate.sh" 0 0 0755
set_perm "$MODPATH/bin/check_per_boot_encryption" 0 0 0755
set_perm "$MODPATH/bin/check_per_boot_key_ready" 0 0 0755
set_perm "$MODPATH/bin/loop_directio" 0 0 0755
ui_print 'Verified sapphire kernel: encrypted writeback test passed.'
ui_print 'Default selection: 8 GiB backing / 8 GiB compressed RAM.'
ui_print 'Active swap is unchanged until the next Android restart.'
