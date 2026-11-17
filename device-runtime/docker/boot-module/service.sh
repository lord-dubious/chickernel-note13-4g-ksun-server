#!/system/bin/sh
for n in $(seq 1 180); do
    [ "$(getprop sys.boot_completed)" = 1 ] && break
    sleep 1
done
[ "$(getprop sys.boot_completed)" = 1 ] || exit 0
sleep 3
/system/bin/sh /data/local/codex-native-docker/control.sh start
