# Rebuild and verify on Linux / WSL

## Inputs

- Python 3.10+, Git, make, gcc/g++, flex, bison, bc, OpenSSL/ELF development
  headers and the matching AOSP LLVM toolchain.
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

## Fetch the pinned full source

```bash
SRC="$HOME/chickernel-source"
git init "$SRC"
git -C "$SRC" remote add origin "$(python3 -c 'import json; print(json.load(open("source-lock.json"))["repository"])')"
git -C "$SRC" fetch --depth=1 origin "$(python3 -c 'import json; print(json.load(open("source-lock.json"))["commit"])')"
git -C "$SRC" checkout --detach FETCH_HEAD
git -C "$SRC" submodule update --init --depth=1
```

Use a clean source checkout and empty separate distribution directory. The
script refuses another source commit or submodule revision. It never edits
`chickernel_defconfig`, installs modules, changes a DT or accesses a phone.
The pinned KSUN Makefile can apply compatibility changes during compilation;
retain any resulting source diff as part of the build evidence.

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
the compiler before building, stops if any requested setting is lost, builds
`Image`, checks embedded IKCONFIG against the build `.config`, replaces only
`Image.gz` in the template, and verifies the packaged kernel again. It writes
`Image`, `kernel.config`, optional ZIP, `build-provenance.json` and fresh
`SHA256SUMS.txt`. A failed run is not a release; keep its logs and inspect it.

## Verify a transferred artifact

Use the exact pinned source/fragment inputs used by the build:

```bash
python3 scripts/verify_kernel.py /path/to/kernel.zip --kind zip   --fragment "$SRC/arch/arm64/configs/chickernel-variants/ksun.config"   --fragment reference-source/server.config   --fragment reference-source/native-sapphire.config   --fragment reference-source/thin-lto.config   --reference-config /path/to/kernel.config
```

Use `--kind image` for Image/Image.gz or `--kind config` for a saved config.
A checksum only identifies bytes. It does not replace feature verification,
module/KMI checks, backups or [device testing](FLASHING.md).

The old Bazel snippet and shell config are legacy integration references,
not the verified path described here. CI resolves configuration and tests the
artifact verifier; it does not claim a complete kernel build or a phone test.
