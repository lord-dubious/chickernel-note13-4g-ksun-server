#!/system/bin/sh
[ "$BOOTMODE" = true ] || abort 'Install from Android using Magisk.'
[ "$(getprop ro.product.device)" = sapphire ] || abort 'Requires sapphire'
[ -f /data/local/codex-native-docker/.codex-owner ] || abort 'Native Docker userspace is missing'
set_perm "$MODPATH/service.sh" 0 0 0755
set_perm "$MODPATH/system/bin/docker" 0 0 0755
ui_print 'Native ARM64 Docker tested. Boot service uses a private Unix socket.'
