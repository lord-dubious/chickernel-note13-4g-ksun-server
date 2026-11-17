# Build and audit status

## Offline driver and ExtM work, 2026-11-17

A new Image was compiled with all **155** current fragment requirements verified
against its embedded configuration. It includes the actual Xiaomi ExtM zRAM
interfaces, confirmed in real ELF symbols, plus the container configuration.
Its SHA-256 is
`887c2e22c340b1d2c03f4d294578088a99558722ba04a213969e12d70e3a9864`.
All 16,027 core export CRCs remain unchanged from the earlier Docker candidate.

The complete device build now produces **338** modules with zero imported-symbol
mismatches or unresolved imports. Of the 316 unique module files found in the
phone and first-stage backup, 313 have rebuilt replacements and three are
built into the Image. The actual old GPU module remains a negative control with
122 mismatches. The battery thermistor tables match the original module bytes.

Offline boot, recovery and driver images have been assembled using the original
device trees and verified backups. These results establish build/configuration
and packaging checks only. The phone is still on its working old kernel: no
partition has been flashed, no permanent storage-backed memory extension has
been enabled, and Docker/GPU workloads have not yet run on this candidate.

The custom ROM needs a compatible ExtM userspace setup. The experimental
ordinary-swap addon was not a stock HyperOS implementation and was never
installed. It is excluded from the kernel project.

## Historical artifact audit, 2026-11-15

The downloaded `chickernel-stable-7-ksun-server.zip` matches the historical
ZIP hash in `../SHA256SUMS.txt`. Its decompressed Image also matches the
recorded `Image-server-ksun` hash. However, its embedded config:

- does not satisfy 73 of the 95 assignments in the original server fragment;
- does not enable `CONFIG_KSU`, PID/user namespaces, AppArmor or Btrfs;
- is identical to the embedded config in the downloaded stable-7 KSUN ZIP.

Thus the previous successful-server-build and root claims are withdrawn for
these artifacts. Hash identity does not establish their advertised features.
The binary filenames and checksums remain historical evidence only.

The upstream embedding rule used a stock defconfig, so missing settings in
that embedded snapshot do not prove the old binaries lacked compiled features.
The locked source patch restores the actual build config.

## Corrected repository and successful candidate build

On 2026-11-15 the pinned source `465df0508d2c6d987aa6ad59b8e3930023f5b944`
plus the checksum-locked IKCONFIG patch built `5.15.189-chickernel-stable-7-ksun-server` with AOSP `clang-r547379` (clang 20.0.0), ThinLTO,
and pahole 1.25. All 153 requested assignments passed resolution and checks
against the embedded configs in both the final Image and AnyKernel3 ZIP.
Both embedded configs match the final build `.config`.

- Image SHA256: `87f11b7f4e2ccdbdf0dc2983df84ad7f459be5994bb18257d410aa288b698f18`
- ZIP SHA256: `ffdf1f222f6065e492d783e7a006b9a0efb493f9c2693b562c4b9298ee0c665d`
- Builder reference commit: `328c133983e5951449ee01b93ed81854be3eb1c0`;
  worktree dirty: `true` (build-tool patch-format cleanup was pending; the
  applied kernel diff and exact patch identities are retained in provenance).

The distribution contains the Image, ZIP, actual config, exported symbol table,
build provenance (including compiler/tool hashes) and generated checksums.
Copies transferred to the Windows output directory passed checksum checks.
The binary files remain local; they are not a GitHub firmware release.

Six artifact-verifier regression tests pass. The old ZIP is rejected because
its stock embedded snapshot cannot substantiate the requested features. The module-version checker was exercised with a real module
against matching, mismatched and incomplete export tables (exit 0/1/2).
CI resolves the fragments and checks the Python tooling; it does not run a
complete kernel build or device test.

## Compatibility remains a device gate

The public reference SPI modules have 13 (`spidev.ko`) and 18
(`spi-msm-geni.ko`) imported CRC mismatches against this build, including
`module_layout`; the controller also has two imports outside the kernel export
table. This candidate is not established compatible with those modules.
The actual phone's ROM/modules still need collection and comparison.
No boot, root, Docker, complete KMI/CFI, or physical IR result is claimed.
See [IR evidence](IR.md) and [installation gates](FLASHING.md).

## Host issues retained for reproducibility

Ubuntu clang 18.1.3 could not supply the required release register-allocation
advisor. The first AOSP build was interrupted during BTF generation because
pahole had been installed after make computed its compatibility flags.
The build script now requires pahole before make starts. The final run used
the kernel's pahole compatibility flags and completed all artifact checks.
Affected objects were recompiled after BTF module metadata became available.
BTF generation required temporary disk/compressed swap on the 8 GiB WSL environment.
The first completed Image was rejected because upstream embedded the stock
defconfig. The locked patch fixes that rule, and the build now checks the
generated IKCONFIG input before linking as well as the final Image/ZIP.
