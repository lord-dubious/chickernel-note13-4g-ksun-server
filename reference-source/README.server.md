# Chickernel KernelSU Server Variant

This tree now includes a new root-enabled build flavor intended for Redmi Note 13 4G / related SDM685 devices that need stronger Linux server and container support while preserving the normal Android device stack.

## New target
- Bazel target: `//common:chickernel_ksun_server`
- Build config: `build.config.gki.aarch64.chickernel.ksun.server`
- Variant fragments:
  - `arch/arm64/configs/chickernel-variants/ksun.config`
  - `arch/arm64/configs/chickernel-variants/server.config`

## What it enables
The server fragment turns on the missing pieces needed for rootful container workloads and more Linux-like administration, including:
- full namespace set (`PID_NS`, `NET_NS`, `IPC_NS`, `UTS_NS`, `USER_NS`)
- container cgroup features (`CGROUP_DEVICE`, `CGROUP_PIDS`, `CGROUP_PERF`, `NET_CLS_CGROUP`, `CFS_BANDWIDTH`)
- Docker/runtime primitives (`POSIX_MQUEUE`, `FHANDLE`, `KEYS`, `SECCOMP`, `BINFMT_MISC`)
- container networking (`BRIDGE_NETFILTER`, `MACVLAN`, `IPVLAN`, `VXLAN`, nftables support, iptables NAT/filter support, `NETFILTER_XT_MATCH_IPVS`)
- broader Linux filesystem coverage (`btrfs`, `xfs`, `nfs`, `cifs`, `9p`, `fuse`, `squashfs`, `iso9660`, `udf`)
- overlayfs enhancements (`OVERLAY_FS_REDIRECT_DIR`, `OVERLAY_FS_INDEX`, `OVERLAY_FS_METACOPY`)

## Validation status
A generated `.config` from this variant passes Docker/Moby's `check-config.sh` for all **Generally Necessary** kernel items.

Remaining optional items that still show as missing in the script output are:
- `CONFIG_CGROUP_HUGETLB` (blocked by `HUGETLB_PAGE` support in this tree/arch combination)

Additional optional server features now enabled in the server variant:
- `CONFIG_IP_SCTP`
- `CONFIG_SECURITY_APPARMOR`

## Native hardware and IR

The server target also merges `native-sapphire.config`. For the non-NFC
`sapphiren` variant, this preserves device-oriented input, USB role-switch,
MMC, LED, RTC, IIO, GPIO/PWM, and LIRC support without adding an internal NFC
controller. The generic NFC stack plus common USB reader drivers are retained
for external NFC-over-USB-C tools.

Both generic IR transmit implementations are enabled:
- `CONFIG_IR_GPIO_TX`
- `CONFIG_IR_PWM_TX`

These options make the kernel drivers available, but they do not identify the
phone's physical IR pin automatically. The sapphire DT/DTBO and Android/vendor
userspace must still describe and use the correct transmitter node. A build
with these symbols enabled is therefore a necessary kernel-side restoration,
not proof that the device-specific blaster wiring is complete.

The exact `sapphiren`-compatible public kernel artifacts were checked during
the audit. Their extracted configuration had `CONFIG_RC_CORE`, `CONFIG_LIRC`,
`CONFIG_RC_DECODERS`, and `CONFIG_RC_DEVICES`, but had both transmitter options
disabled. Their published DTB/DTBO artifacts did not expose an identifiable
`gpio-ir-tx`, `pwm-ir-tx`, or Xiaomi-specific IR node. This repository enables
the missing kernel options, but does not fabricate a GPIO/PWM assignment that
has not been verified against the phone's stock DT.

Reference sources checked:
- `https://github.com/chickendrop89/device_xiaomi_gemstones-kernel` (`android13-5.15-lts`)
- `https://github.com/sm6225-sapphire/device_xiaomi_sapphire-kernel` (`15`)
- `https://github.com/xiaomi-6225-AD/android_device_xiaomi_sapphire-kernel` (`lineage-21`)

## Build guidance
Use the full manifest workspace from `chickernel.xml`, not the lightweight `readme` checkout.

Typical build entry points from the synced workspace root:
```bash
bazel build //common:chickernel_ksun_server
```

or

```bash
BUILD_CONFIG=common/build.config.gki.aarch64.chickernel.ksun.server \
  build/build.sh
```

## Note on host toolchains
A quick local `make ARCH=arm64 LLVM=1 ... Image` sanity attempt in a generic host environment may fail when using distro clang instead of the AOSP/prebuilt toolchain expected by this kernel tree. Prefer the manifest workspace and its intended prebuilts for real release builds.

## Runtime note
For bridge/NAT based container networking, IPv6 forwarding still needs to be enabled in userspace/sysctl on the running device if you want IPv6 container forwarding.

### About systemctl and Termux
This kernel can provide the Linux kernel features needed by a full Linux rootfs/container, but Android itself still uses Android init rather than systemd. So `systemctl` will work only **inside a systemd-based Linux rootfs/container/VM**, not as Android's native service manager. Termux can be the launcher/admin environment, but it does not replace Android userspace by itself.
