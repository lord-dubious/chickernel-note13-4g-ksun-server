# Build and audit status

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

## Corrected repository

The pinned kernel source is `465df0508d2c6d987aa6ad59b8e3930023f5b944`.
The corrected fragments resolve with all 153 requested assignments satisfied,
including KSUN, server/native options and the ThinLTO override. Artifact-tool
regression tests cover missing features, stale embedded configs, ambiguous
images and truncated IKCONFIG. The old ZIP is rejected by the verifier.

A first compile using Ubuntu clang 18.1.3 stopped during kernel preparation:
its release register-allocation advisor is unavailable. That failure is not
kernel compilation success. Full builds require a compiler that passes the
optimizer probe in `scripts/build.py`; upstream selects AOSP `clang-r547379`.

No boot, root, module/KMI, Docker or physical IR result is established by these
repository checks. Any replacement build must retain its own generated
`build-provenance.json`, `kernel.config` and `SHA256SUMS.txt` and pass the
[device checks](FLASHING.md).
