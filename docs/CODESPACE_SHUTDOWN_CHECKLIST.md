# Codespace shutdown checklist

## What is already safe on GitHub
- `README.md`
- `docs/FEATURES.md`
- `docs/FLASHING.md`
- `docs/BUILD_RESULT.md`
- `SHA256SUMS.txt`
- `artifacts/README.md`
- `patches/ksun-server-feature-pack.patch`

## What is NOT stored in this GitHub repo yet
The actual built binary artifacts are still local to the Codespace:
- `/workspaces/chickernel-full/chickernel-stable-7-ksun-server.zip`
- `/workspaces/chickernel-full/common/out/thin-build/arch/arm64/boot/Image`

## Must-do before deleting the Codespace
Download at least this file:
- `chickernel-stable-7-ksun-server.zip`

Recommended extra backups:
- `/workspaces/chickernel-note13-4g-ksun-server.bundle`
- `/workspaces/chickernel-note13-4g-ksun-server.tar.gz`

## Verification
Expected checksums are in `SHA256SUMS.txt`.
