# Chickernel Note 13 4G: KSUN + server

Build configuration and verification tools for Redmi Note 13 4G **sapphire
(non-NFC)** and **sapphiren (NFC)**, based on Chickernel stable-7.
This is a reference/build-tools repository, not a complete kernel source tree.

## Current status

The historical ZIP recorded in `SHA256SUMS.txt` is **not a verified server/root
build**. Its embedded configuration does not satisfy 73 of the 95 original
server-fragment assignments and does not enable `CONFIG_KSU`. Do not use its
name or checksum as proof of features or compatibility.

The audit found why embedded configs were misleading: upstream embeds
`khaje-stock_defconfig`, not the real build config. Missing settings in that
stock snapshot do **not** prove the old binaries lacked the compiled features.
The locked source patch restores truthful IKCONFIG/`/proc/config.gz`; the
build checks its generated input before linking and the final artifact afterward.

The corrected 155-setting build and its matching vendor-driver stack have now
been installed and tested on sapphire running crDroid 11.2 / Android 15.
The running config matches the compiled config. Native ARM64 Docker, resource
limits, networking, Compose, image builds, encrypted zRAM writeback, and an
Adreno 610 Vulkan compute workload inside a container have passed device checks.
This establishes the tested build/ROM combination, not universal compatibility.
Evidence and remaining gates are in [BUILD_RESULT](docs/BUILD_RESULT.md).

The [device runtime sources](device-runtime/README.md) contain the deployed
Docker launcher, memory-extension module and Settings app, and bounded GPU
probe. Recovery touch after screen-off remains an unresolved existing issue.

## Build and verify

Follow [the Linux/WSL build instructions](docs/REBUILD_WITH_AGENT.md).
`scripts/build.py` merges the pinned upstream KSUN fragment, server and native
fragments, and the explicit ThinLTO override into an output directory. It checks
every requested setting before compilation, then checks the actual Image and
packaged ZIP against the build config. It never flashes a phone.

- [Intended features](docs/FEATURES.md)
- [Stock IR path and diagnosis](docs/IR.md)
- [Device checks, backup and installation](docs/FLASHING.md)
- [Historical artifacts](artifacts/README.md)

## IR support

The inspected stock IR path is SPI: `lc,ir-spi` in the device tree,
`spidev.ko` + `spi-msm-geni.ko`, and `/dev/spidev0.1` in vendor userspace.
Generic GPIO/PWM LIRC drivers are optional capabilities; enabling them does
not restore this path. Preserve the phone's matching vendor modules and DT.
Actual module loading, IR transmission and kernel/vendor compatibility must
be checked on the connected device before installation.
