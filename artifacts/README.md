# Artifact status

No replacement flashable binary is checked into this reference repository.
Root `SHA256SUMS.txt` records two **historical, unverified-for-features** artifacts:
`chickernel-stable-7-ksun-server.zip` and `Image-server-ksun`.
They failed the feature audit described in [BUILD_RESULT](../docs/BUILD_RESULT.md).
Do not relabel or reflash them as the corrected build.

`scripts/build.py` creates a separate distribution directory containing the
verified Image, actual config, exported-symbol table, provenance, generated checksums and, if an
audited AnyKernel3 template is supplied, a verified replacement ZIP.
Compilation/config verification does not establish boot or IR compatibility.
