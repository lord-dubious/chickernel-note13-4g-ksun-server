# Intended feature configuration

These are build requirements, not claims about the old ZIP or a running phone.
Both Redmi Note 13 4G variants are covered by the shared hardware baseline:
`sapphire` is non-NFC; `sapphiren` has NFC.

- KernelSU-Next from the pinned upstream submodule and KSUN fragment.
- PID, NET, IPC, UTS and USER namespaces; container cgroup controls;
  seccomp, keys, file handles, POSIX queues and binfmt_misc.
- Bridge netfilter, macvlan, ipvlan, vxlan, nftables, iptables NAT/filter,
  IPVS and overlayfs redirect/index/metacopy.
- Btrfs, XFS, NFS, CIFS, 9p, FUSE/CUSE, SquashFS, ISO9660 and UDF.
- devtmpfs, autofs, fanotify, AppArmor and SCTP.
- Root over NFS with `IP_PNP` enabled to satisfy its Kconfig dependency.
  IPsec transport mode has no separate `INET_XFRM_MODE_TRANSPORT` symbol
  in this tree; the obsolete assignment has been removed.
- Input, USB role switch, MMC, GPIO/PWM, LEDs, RTC and IIO prerequisites.
- Generic LIRC GPIO/PWM TX and receiver/decoder capabilities. These do not
  replace the phone's stock SPI IR driver or HAL; see [IR](IR.md).
- Generic NFC and common USB NFC reader drivers for external adapters.
  Adapter, host-mode and userspace compatibility remain device checks.

ThinLTO is a separate explicit build override. The verifier checks all fragment
assignments, including disabled options, against the resolved and embedded
configs. End-to-end Docker, root and hardware tests remain runtime checks.

Android continues to use Android init. `systemctl` requires a suitable Linux
userspace/container; enabling kernel features does not turn Android into systemd.
