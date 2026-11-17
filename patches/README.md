# Locked source patches

Every patch is checksummed in `source-lock.json`. The builder applies the exact set against the pinned kernel revision and rejects other source edits.

| Patch | Purpose |
| --- | --- |
| `0001` | Embed the actual build configuration instead of an unrelated static stock defconfig. |
| `0002` | Restore `msm_dirconn_cfg_reg`, which the Qualcomm pinctrl code calls but the base tree no longer defines. The implementation comes from the [device reference tree at a pinned revision](https://github.com/The-Angel-Place-Sapphire/kernel_xiaomi_sapphire/blob/3a2cfe72b3b05983f7b5594094f9572b38c36c04/drivers/pinctrl/qcom/pinctrl-msm.c). |
| `0003` | Remove the sole stale assignment to `ufs_qcom_host.spm_lvl_default`; the member is absent from the header and the [reference implementation](https://github.com/The-Angel-Place-Sapphire/kernel_xiaomi_sapphire/blob/3a2cfe72b3b05983f7b5594094f9572b38c36c04/drivers/scsi/ufs/ufs-qcom.c) retains the device-tree power level in `hba->spm_lvl` without that cache. |
| `0004` | Remove an unused remoteproc history counter and buffer. Neither has a reference outside its declaration. Active last-modem-reason and ramdump interfaces remain. |
| `0005` | Remove second, byte-identical definitions of the Bengal and QCS605 ADSP resource descriptors. Firmware names, IDs, clocks and other resource values remain unchanged. |
| `0006` | Remove a static CoreSight MHI event callback that is never registered or called. Other PCIe open, write and workqueue callbacks remain. |
| `0007` | Allow an explicit `VMLINUX_BTF_BASE` file for module BTF generation. This accepts exact BTF extracted from a verified prebuilt kernel Image; normal builds still default to the usual vmlinux ELF. BTF generation and symbol checks remain enabled. |
| `0008` | Restore the sapphire charger/gauge interfaces and IIO channel numbering required by the rebuilt touch, audio and charging-policy drivers. |
| `0009` | Restore Xiaomi panel client IDs and the sapphire thermal interface used by those device drivers. |
| `0010` | Restore the USB PD policy interfaces used by Xiaomi charging policy. |
| `0011` | Build the standalone PMIC voter once, instead of duplicating its exports inside the charger module. |
| `0012` | Provide Xiaomi UFS diagnostic data used by the rebuilt `mi_memory` module. |
| `0013` | Preserve the actual phone backup's battery-temperature calibration table. Its compiled bytes are checked against the original module. |
| `0014` | Build QRTR nameservice as `ns.ko`, matching the device's module load lists. |
| `0015` | Match the stock Khaje remote processors' XO-clock resource configuration. |
| `0016` | Restore Xiaomi ExtM zRAM aging, statistics and writeback interfaces confirmed in the official sapphire HyperOS module. This changes generic kernel code and requires a new Image and matching driver metadata. |
| `0017` | Declare the ExtM page-life initializer with `(void)` for modern Clang. No compiler warning is suppressed. |

Patches 2–6 repair compilation of device modules that the normal GKI image configuration does not compile. They do not make the existing vendor module binaries compatible with a changed kernel interface. Replacement modules must be built against the container-enabled kernel, with their dependencies, and checked before installation.

The device-module build work uses the kernel tree's mixed-build support. The device fragment must preserve GKI built-ins (`merge_config.sh -y`) so those components are not rebuilt as duplicate modules. Server, native-hardware, KernelSU and ThinLTO requirements still need to pass the configuration verifier.

These patches and successful compilation alone are not a flashability or hardware-validation result. Do not install a kernel/module combination until the complete driver dependency set and boot packaging have been validated together.

The device-specific reconstructions are pinned in `sapphire-reconstruction-provenance.json`.
Stock Memory Extension also needs compatible userspace initialization and policy. The
ExtM kernel interfaces alone do not restore HyperOS's Settings switch on crDroid.
