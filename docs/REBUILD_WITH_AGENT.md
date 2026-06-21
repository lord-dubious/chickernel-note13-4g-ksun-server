# Rebuild instructions for a future agent

This document explains how to reproduce the **flashable KSUN server zip** from scratch.

## What this repo contains
This repo is a **reference/handoff repo**, not the full original kernel source tree. Use it together with the upstream kernel source repository:
- upstream source repo: `https://github.com/chickendrop89/device_xiaomi_gemstones-kernel`
- source branch base: `android13-5.15-lts`

Reference files in this repo:
- `reference-source/BUILD.bazel.snippet.txt`
- `reference-source/build.config.gki.aarch64.chickernel.ksun.server`
- `reference-source/server.config`
- `reference-source/README.server.md`
- `docs/FEATURES.md`
- `docs/FLASHING.md`
- `SHA256SUMS.txt`

## Goal
Rebuild these outputs:
- raw kernel image: `Image`
- flashable zip: `chickernel-stable-7-ksun-server.zip`

## High-level process
1. Sync/build a full kernel workspace with `chickernel.xml`
2. Ensure the real source tree under `common/` is based on `android13-5.15-lts`
3. Add the server flavor target and config files from `reference-source/`
4. Build the server flavor
5. Package the final `Image` into an AnyKernel3-style flashable zip using the official stable-7 KSUN zip as a template

## 1) Prepare workspace
Expected workspace layout used successfully in this session:
- workspace root: `/workspaces/chickernel-full`
- source tree: `/workspaces/chickernel-full/common`

The repo's manifest file was:
- `chickernel.xml`

## 2) Apply source modifications
In the `common/` source tree:

### Add BUILD target
Append the `reference-source/BUILD.bazel.snippet.txt` block to `BUILD.bazel`.

### Add build config
Create:
- `build.config.gki.aarch64.chickernel.ksun.server`

Use exactly:
- `reference-source/build.config.gki.aarch64.chickernel.ksun.server`

### Add Kconfig fragment
Create:
- `arch/arm64/configs/chickernel-variants/server.config`

Use exactly:
- `reference-source/server.config`

### Optional doc copy
You may also copy:
- `reference-source/README.server.md`

## 3) Important build note
The normal branch default used **full LTO**, which made final linking very slow in this session.

For practical completion, the successful artifact build used a temporary ThinLTO override:

```bash
cat > /tmp/lto-thin.config <<'EOF'
# Faster local build variant
# CONFIG_LTO_CLANG_FULL is not set
CONFIG_LTO_CLANG_THIN=y
EOF
```

## 4) Practical successful build path used in this session
From inside `common/`:

```bash
export PATH=/workspaces/chickernel-full/prebuilts/clang/host/linux-x86/clang-r522817/bin:/workspaces/chickernel-full/build/kernel/build-tools/path/linux-x86:$PATH
```

Then merge config and build:

```bash
KCONFIG_CONFIG=arch/arm64/configs/chickernel_defconfig scripts/kconfig/merge_config.sh -m -r \
  arch/arm64/configs/chickernel_defconfig \
  arch/arm64/configs/chickernel-variants/ksun.config \
  arch/arm64/configs/chickernel-variants/server.config \
  /tmp/lto-thin.config

make ARCH=arm64 LLVM=1 HOSTCC=gcc HOSTCXX=g++ HOSTLD=g++ O=out/thin-build chickernel_defconfig
make -j4 ARCH=arm64 LLVM=1 HOSTCC=gcc HOSTCXX=g++ HOSTLD=g++ O=out/thin-build Image
```

Successful output paths were:
- `out/thin-build/arch/arm64/boot/Image`
- `out/thin-build/vmlinux`

## 5) Packaging flashable zip
Official release format matched in this session:
- AnyKernel3-style flashable zip
- based on the official release asset `chickernel-stable-7-ksun.zip`

Packaging method used:
1. download/extract the official stable-7 KSUN zip
2. replace `Image.gz` with a gzip of the newly built `Image`
3. optionally adjust banner / kernel.string in `anykernel.sh`
4. re-zip the package

The exact local packaging pattern used was:

```bash
gzip -c /path/to/Image > Image.gz
zip -r9 chickernel-stable-7-ksun-server.zip .
```

## 6) Expected artifact names
The final artifact names used in this session were:
- `Image`
- `chickernel-stable-7-ksun-server.zip`

## 7) Verification expectations
After rebuild, verify:
- the build produces `Image`
- the resulting config includes server features from `reference-source/server.config`
- overlayfs, namespaces, AppArmor, SCTP, NFS/CIFS/9P/Btrfs/XFS, and Docker-related netfilter pieces are enabled
- if possible, compare SHA256 against this repo only when reproducing the exact same artifact inputs/toolchain; otherwise expect differences

## 8) Important caveat
This repo alone is not enough to rebuild unless the next agent also has:
- the upstream source tree
- the build workspace/prebuilts
- the official stable-7 KSUN zip used as packaging template

But with those pieces, the next agent should be able to reconstruct the flashable zip from the instructions and reference files here.
