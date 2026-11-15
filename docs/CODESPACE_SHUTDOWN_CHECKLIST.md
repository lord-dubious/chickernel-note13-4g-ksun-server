# Preserve a build before deleting a workspace

1. Commit source/config/build-tool changes and record the exact commit.
2. Copy the complete new distribution directory, including `Image`, optional
   ZIP, `kernel.config`, `vmlinux.symvers`, `build-provenance.json` and generated
   `SHA256SUMS.txt`.
3. Verify those generated hashes after transfer and rerun `verify_kernel.py`
   against the transferred Image or ZIP and the actual build config.
4. Preserve module/KMI and device-test logs separately when available.

The historical root checksum file does not validate a replacement build.
No previous Codespace's existence, retained binaries or shutdown state is
asserted by this repository. The old placeholder patch was not an applicable
patch and has been removed; the checked build tools and reference fragments
are the current source of build instructions.
