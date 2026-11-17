# Rebuild and verify on Linux / WSL

## Inputs

- Python 3.10+, Git, make, gcc/g++, flex, bison, bc, OpenSSL/ELF development
  headers, `pahole` (BTF generation), `kmod` (read-only module checks) and
  the matching AOSP LLVM toolchain.
- Kernel repository, exact commit and submodules from `../source-lock.json`.
- AOSP `clang-r547379` selected by the pinned source's `build.config.constants`.
  It is available from the official
  [AOSP compiler repository](https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86/+/refs/heads/main/clang-r547379/).
  Retain the downloaded archive's hash. A generic distro clang is adequate for
  configuration checks but may lack this kernel's Polly/release ML optimizer.
- Optional audited stable-7 AnyKernel3 ZIP, SHA256:
  `988ba55f5376b7197c66249229b662bdfceee899fd36012fd356c124df039049`.
  It is only an installer template; its old Image is always replaced.

Use a Linux filesystem for the source/build. Windows checkouts can fail on
Linux filenames such as `aux.c`. Run commands below from this reference repo.
BTF generation exceeded 8 GiB of combined RAM/swap in the local build; provide
sufficient memory/swap and disk space for the unstripped kernel and toolchain.

## Fetch the pinned full source

```bash
SRC="$HOME/chickernel-source"
git init "$SRC"
git -C "$SRC" remote add origin "$(python3 -c 'import json; print(json.load(open("source-lock.json"))["repository"])')"
git -C "$SRC" fetch --depth=1 origin "$(python3 -c 'import json; print(json.load(open("source-lock.json"))["commit"])')"
git -C "$SRC" checkout --detach FETCH_HEAD
git -C "$SRC" submodule update --init --depth=1
```

Start with a clean source checkout and empty separate distribution directory.
The script applies only the checksum-locked patches in `source-lock.json`;
later runs accept exactly that patch set and reject unrelated source changes.
It refuses another source commit or submodule revision. It never edits
`chickernel_defconfig`, installs modules, changes a DT or accesses a phone.
The pinned KSUN Makefile can apply compatibility changes during compilation;
retain any resulting source diff as part of the build evidence.

The real patch in `patches/0001-embed-the-actual-build-config.patch` changes the
upstream IKCONFIG rule from `khaje-stock_defconfig` to `$(KCONFIG_CONFIG)`.
This removes stock-config spoofing and makes `/proc/config.gz` report the
actual custom config. A stock embedded snapshot cannot establish which
features were compiled into an older binary.

## Check configuration only

```bash
python3 -m unittest discover -s tests -v
python3 scripts/build.py --source "$SRC" --out "$HOME/chickernel-config" --config-only
```

This merges upstream KSUN, server, native and ThinLTO fragments, resolves
Kconfig, and verifies every assignment. `ROOT_NFS` needs `IP_PNP`; the obsolete
`INET_XFRM_MODE_TRANSPORT` assignment is intentionally absent.

## Build and optionally package

```bash
python3 scripts/build.py   --source "$SRC"   --out "$HOME/chickernel-build"   --toolchain /path/to/clang-r547379   --dist "$HOME/chickernel-dist"   --template /path/to/chickernel-stable-7-ksun.zip   --jobs 4
```

Omit `--template` to build only the raw Image and evidence. The script probes
the compiler before building, stops if any requested setting is lost, checks
the generated IKCONFIG input before the expensive whole-kernel link, builds
`Image`, checks embedded IKCONFIG against the build `.config`, replaces only
`Image.gz` in the template, and verifies the packaged kernel again. It writes
`Image`, `kernel.config`, `vmlinux.symvers`, optional ZIP, `build-provenance.json` and fresh
`SHA256SUMS.txt`. A failed run is not a release; keep its logs and inspect it.

## Verify a transferred artifact

Use the exact pinned source/fragment inputs used by the build:

```bash
python3 scripts/verify_kernel.py /path/to/kernel.zip --kind zip   --fragment "$SRC/arch/arm64/configs/chickernel-variants/ksun.config"   --fragment reference-source/server.config   --fragment reference-source/native-sapphire.config   --fragment reference-source/thin-lto.config   --reference-config /path/to/kernel.config
```

Use `--kind image` for Image/Image.gz or `--kind config` for a saved config.
Use `--kind gzip-config` for generated `config_data.gz` or a copy of the
running phone's `/proc/config.gz`.
A checksum only identifies bytes. It does not replace feature verification,
module/KMI checks, backups or [device testing](FLASHING.md).

Compare copies of the phone's modules before installation (this does not load them):

```bash
python3 scripts/check_module_versions.py --symvers /path/to/vmlinux.symvers \
  /path/to/phone/spidev.ko /path/to/phone/spi-msm-geni.ko
```

Supply matching provider-module symbol tables with extra `--symvers` arguments
when needed. A mismatch exits 1; unresolved imports exit 2. Matching imported
CRCs is only one prerequisite, not a complete ABI, CFI, signature or boot check.

The old Bazel snippet and shell config are legacy integration references,
not the verified path described here. CI resolves configuration and tests the
artifact verifier; it does not claim a complete kernel build or a phone test.

## Matching device drivers

The server configuration changes kernel interfaces used by the phone's stock
drivers. Build the complete replacement set; do not install the Image alone.
The optional template ZIP is now explicitly named
`chickernel-stable-7-ksun-server-KERNEL_ONLY_DO_NOT_FLASH.zip` and includes a
warning file. It is an inspection artifact, not the complete phone update.

Check out the external sources at the revisions in `vendor-source-lock.json`,
including the small MMRM test source. Keep the completed GKI build directory,
with its actual `vmlinux`, `vmlinux.symvers`, Image and configuration:

```bash
python3 scripts/build_device_drivers.py \
  --source "$SRC" --vendor "$VENDOR" --mmrm-test "$MMRM_TEST" \
  --gki "$GKI_OUT" --out "$MODULE_OUT" --toolchain "$CLANG_DIR" \
  --dist "$DRIVER_DIST" --jobs 2
```

This verifies the locked common/vendor source edits, preserves GKI built-ins
while merging the device fragment, checks compiler-generated ABI signatures,
builds common and external providers, links fresh module ELFs against the real
GKI BTF, and verifies all imports and export owners. Historical tracked CRC
sidecars are regenerated by compiling their corresponding objects. Stock CRC
tables, forced loading and disabled version checks are not used.

`scripts/prepare_device_package.py` is an offline, device-specific packager.
It requires verified original boot/recovery/DLKM backups and driver coverage,
symbol and calibration evidence. It preserves the original device trees,
Magisk init_boot and partition sizes. The current sapphire layout needs matching
drivers in vendor_boot, vendor_dlkm and recovery, with built-in zRAM components
accounted for in system_dlkm. The package still requires recovery preflight and
physical hardware tests before it can be called working.

## Memory Extension

The native fragment enables zRAM writeback and the Xiaomi ExtM driver APIs.
The stock sapphire driver and official HyperOS userspace were inspected; this
is distinct from an ordinary swapfile added beside unchanged zRAM. The kernel
keeps Chickernel's existing ZSTD default. Stock HyperOS defaults to lzo-rle.
On a custom ROM, compatible initialization and writeback policy must be
validated separately; kernel support alone does not restore the HyperOS UI.
