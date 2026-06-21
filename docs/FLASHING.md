# Flashing

## Main flashable file
- Local artifact built in this session: `chickernel-stable-7-ksun-server.zip`

## Intended flash method
- Copy zip to phone
- Boot custom recovery
- Backup current boot image first
- Flash the zip
- Reboot and test

## Immediate post-flash checks
- Device boots normally
- Touchscreen works
- Storage mounts normally
- Wi-Fi / mobile data work
- Charging works
- KernelSU still works

## Advanced checks later
- Verify `/proc/config.gz`
- Test overlayfs mounts
- Test namespaces / cgroups
- Test Docker/container runtime from Termux/rootfs
