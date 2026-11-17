# Verified sapphire runtime sources

These are the sources used with the installed server kernel and rebuilt
drivers on Redmi Note 13 4G non-NFC, crDroid 11.2 / Android 15 (2025-02-24).
They are a device-specific deployment reference, not a generic flashing ZIP.
See [validation.json](validation.json) for the checked scope.

## Native Docker

The service runs official Linux ARM64 Docker binaries in an Alpine 3.24.4
userspace with a private mount namespace. It shares Android's actual kernel;
there is no VM, proot or CPU emulation. CPU/memory/pids limits, seccomp and
separate container namespaces have passed real checks. The encrypted F2FS
backing uses the VFS storage driver.

Deployed root: `/data/local/codex-native-docker`. Root-only client configuration,
CLI plugins and the workspace are shared between Android terminals and the
native Alpine server shell. Termux is a convenient frontend, not a runtime
dependency. Another local terminal can reach the same server after its own
normal Magisk root authorization.

```sh
su
docker info
docker compose version
docker buildx version
sh /data/local/codex-native-docker/control.sh shell
```

The server shell opens in `/data/local/codex-native-docker/workspace`. Put
Compose projects and bind-mounted project data there. Its absolute path is
also bound at the same path inside the daemon's Linux filesystem view.

`bootstrap.sh` must be launched by `control.sh start`, which first creates the
private namespace. `src/nsroot_launch.c` moves the prepared Linux root over
that namespace's root and enters it. A subdirectory chroot was insufficient:
the Android kernel's mount-namespace `setns()` resets filesystem root, causing
container exec to see Android. The launcher rejects the caller and Android
init namespaces and never deletes old-root files. A container-only sentinel,
absence of Android/daemon root markers, dropped capabilities and seccomp were
checked after the fix.

The daemon uses the phone's own iptables binaries and original shared xtables
lock through read-only runtime mounts. The existing Android forwarding policy
is preserved with `ip-forward-no-drop`. Normal container networks use the
reserved `172.30.240.0/20` pool, with scoped routing rules managed by
`network.sh`; the current uplink is refreshed without changing Android's
default routing tables. Configuration reserves table 45201 and priorities
12001/13590 and refuses conflicting ownership. Custom subnets outside that
pool need corresponding routing configuration. IPv4 bridge networking and
published ports have been tested.

Compose and Buildx ARM64 assets and official checksums are pinned in
`docker/plugin-source-lock.json`. The standard Docker archive also contains
containerd, runc, docker-init and docker-proxy. Build `src/nsroot_launch.c` with
a native ARM64 or cross musl compiler, for example `cc -static -O2 -Wall
-Wextra -Werror`, and stage it as `rootfs/usr/local/bin/nsroot-launch`.

The boot module expects the verified userspace and ownership marker to exist;
it starts the existing `control.sh`. It is not a rootfs downloader/installer.

## Memory extension

`memory-extension/module` supplies Magisk boot scripts and a root-only control
interface. Its Settings app source is in `memory-extension/app`. The system app
registers under Settings' System category and also has a launcher entry.

Selections match the inspected stock policy for this RAM/storage variant:

| Selection | Compressed zRAM size | Encrypted storage backing |
| --- | --- | --- |
| Off | ROM default, 4 GiB | None |
| 4 GiB | 6 GiB | 4 GiB |
| 8 GiB | 8 GiB | 8 GiB |

Physical RAM is unchanged. Storage-backed pages are slower than physical RAM.
This restores the Xiaomi zRAM writeback mechanism with a custom crDroid
controller; it does not restore the complete HyperOS framework.

The early hook checks the exact kernel, ROM initializer hashes, space reserve
and flash lifetime, then defers the duplicate ROM initializer. The non-blocking
service waits until the directory's encryption policy matches the current
per-boot key reference and the kernel reports that key present. No secret key
material is read or stored. It then creates a 0600 backing file under
`/data/per_boot`, attaches a 4096-byte/direct-I/O loop, sets zRAM backing before
disksize, and enables swap. Autoclear is enabled after zRAM holds the loop open;
automatic detach after reset has been tested on an owned secondary device.

The controller caps writeback at 1 GiB per UTC day, records remaining quota,
and only flushes bounded idle pages under memory pressure while asleep and
below the thermal threshold. The running setup does not hot-reset or swap off
an active main zRAM device. Saved selections apply after restarting. Failure
to initialize retains/restores ROM-sized compressed swap.

Build the three native helpers in `memory-extension/src` for ARM64 and place
them in the module's `bin` directory. `check_per_boot_encryption.c` is a
freestanding AArch64 probe; the other two can be static Linux/musl binaries.
Build/sign the Java app with Android SDK 35, retain the signing key privately,
and stage the APK as `system/app/SapphireMemoryExtension/SapphireMemoryExtension.apk`.
Signing keys, passwords and generated binaries are deliberately excluded.

## GPU proof and recovery follow-up

`docker/gpu-probe` contains a bounded compute shader and Android-compatible
Vulkan program. The program rejects software fallback, selects Adreno 610,
dispatches a shader and checks all 256 results. It passed inside Docker with
explicit read-only Android runtime mounts and only the required device grants.
Binderfs nodes require their original inode, so the probe uses bind mounts plus
device-cgroup rules instead of recreating binder nodes with `--device`.

Build `probe.c` with an Android ARM64 Clang toolchain and the pinned Vulkan
headers; it loads Android's Vulkan library rather than a musl/glibc ICD. Compile
the shader with `glslangValidator -V --target-env vulkan1.0 -S comp probe.comp
-o probe.spv`. Stage the program, SPIR-V and `run-verified.sh` in the server
workspace's `gpu-probe` folder. A root-approved local terminal can repeat the
owned probe with:

```sh
sh /data/local/codex-native-docker/workspace/gpu-probe/run-verified.sh
```

This is compatible Android/Vulkan userspace, not a generic CUDA/NVIDIA runtime.
Other GPU images need appropriate userspace integration. The probe is not run
automatically and does not grant GPU/binder access to ordinary containers.

TWRP touch after screen-off remains unresolved. The recovery-only capture tool
in `diagnostics` takes read-only IRQ, power and driver snapshots. It does not
read touch coordinates, PINs, encrypted app contents or firmware-upgrade nodes.
The next test requires a physically assisted recovery session after phone work
and server workloads have been saved.
