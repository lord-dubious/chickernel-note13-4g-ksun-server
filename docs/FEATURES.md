# Enabled feature summary

This custom build adds a new `KSUN + server` flavor on top of Chickernel stable-7
for the non-NFC Redmi Note 13 4G `sapphiren` variant.

The build also carries a separate `native-sapphire.config` fragment. This
keeps the device hardware baseline explicit while the server fragment remains
focused on containers and Linux userspace.

## Root / base
- KernelSU-Next (KSUN)
- baseband-guard retained

## Container / Docker / namespace support
- PID / NET / IPC / UTS / USER namespaces
- cgroup device / pids / perf / net classid / bandwidth controls
- seccomp + seccomp filter
- keys + fhndle + POSIX mqueue + binfmt_misc
- bridge + bridge netfilter + veth + tun + macvlan + ipvlan + vxlan
- iptables NAT/filter + nftables + IPVS
- overlayfs with redirect/index/metacopy

## Filesystems / server use
- ext4 + f2fs
- btrfs + xfs
- nfs + cifs + 9p
- fuse + cuse
- squashfs + iso9660 + udf
- loop + dm-crypt + dm-snapshot + md + zram

## Linux-rootfs helpers
- devtmpfs
- autofs
- fanotify
- AppArmor
- SCTP

## Native sapphire hardware preservation
- LIRC and RC-core userspace interfaces
- Generic GPIO and PWM IR transmitter drivers
- GPIO IR receiver and common protocol decoders
- GPIO/PWM, input, fingerprint, USB role-switch, MMC, LED, RTC, and IIO prerequisites

The phone has no built-in NFC controller, but the generic NFC stack and common
USB reader drivers remain enabled so an external NFC-over-USB-C tool can still
work when the adapter, USB host mode, and userspace support are present.

The kernel source includes the generic IR transmit drivers, but the driver
alone is not sufficient to restore the phone's blaster. The final device
tree/DTBO must expose the actual IR GPIO or PWM node using the matching
`gpio-ir-tx` or `pwm-ir-tx` compatible. The Android/vendor userspace path must
also open the resulting LIRC device. This repository therefore restores the
kernel-side capability without inventing an unverified GPIO number or DT node.
