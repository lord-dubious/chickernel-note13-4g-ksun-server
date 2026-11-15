# Device inspection and installation gates

The repository and build tools do not automatically flash or reboot a phone.
A config-verified build is not yet proven compatible with the installed ROM.

## Before changing a partition

1. Read actual product/codename, ROM build, kernel release/config, bootloader
   lock state, current slot, battery level and available custom recovery.
   `sapphire` is non-NFC; `sapphiren` is NFC. Use live properties, not a guess.
2. Diagnose [the stock SPI IR path](IR.md), including vendor-module loading.
3. Back up the current boot image and relevant device-tree/vendor-boot images
   to the PC. Record the slot, partition sizes and hashes. Verify copied backup
   sizes/hashes and establish the exact restore procedure for this device.
4. Verify the replacement Image/ZIP against its generated `kernel.config`
   and fragments. Retain build provenance and compare required vendor-module
   symbols/KMI. Kernel release/vermagic alone is not an ABI check.
5. Confirm the actual recovery/install method supports the audited AnyKernel3
   package. This ZIP targets the active slot's boot image; it is not a raw
   image to pass to `fastboot flash boot`. Do not replace DTBO or vendor_boot
   merely to install the kernel.

The historical ZIP in root `SHA256SUMS.txt` failed the feature audit; do not use
it as the corrected installation. Bootloader unlocking/relocking, wiping data,
formatting and partition-layout changes are not part of this kernel update.

## Installation and verification

After the above evidence is available, use the device's confirmed custom
recovery path to install the verified replacement ZIP. Keep a working restore
route and the current boot backup accessible on the PC.

Check normal boot, touch/fingerprint, storage, Wi-Fi/mobile data, charging,
root manager compatibility, loaded vendor modules and kernel logs. Extract the
running `/proc/config.gz` when available and compare against the build config.
Test IR physically, then test container/network/filesystem workloads separately.
Any physical button presses or on-device approvals must be performed by the user.
