# Enabled feature summary

This custom build adds a new `KSUN + server` flavor on top of Chickernel stable-7.

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
