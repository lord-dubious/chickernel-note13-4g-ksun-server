# Server build configuration

The supported build entry point is `../scripts/build.py`; see
[the build guide](../docs/REBUILD_WITH_AGENT.md). It uses the pinned upstream
`chickernel_defconfig` and KSUN fragment followed by `server.config`,
`native-sapphire.config` and `thin-lto.config`, without editing the source
`chickernel_defconfig` in place.

All fragment assignments must survive Kconfig resolution. The finished Image
must contain the same embedded configuration as the output `.config`; a ZIP
is verified again after packaging. A saved `.config`, checksum or filename
alone is insufficient evidence of enabled features.

The `BUILD.bazel.snippet.txt` and shell build-config file are retained as legacy
integration references. They are not the checked build/package path and are
not claimed to have passed a complete Bazel or manifest build.

See [intended features](../docs/FEATURES.md), [stock SPI IR](../docs/IR.md), and
[actual validation status](../docs/BUILD_RESULT.md). No current claim is made
that Moby's check-config script, Docker, KernelSU or hardware tests have passed
on a replacement artifact or on the phone.
