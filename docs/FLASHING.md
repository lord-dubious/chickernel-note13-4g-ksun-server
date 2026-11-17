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
5. Confirm the actual recovery/install method and restore route. The earlier
   AnyKernel3 recipe is a kernel-only path and does not install the replacement
   driver stack. Its output is now explicitly marked DO_NOT_FLASH. A complete
   sapphire package contains coupled boot, vendor_boot, recovery and logical
   driver-partition images; do not use a ZIP as a raw boot image.

The historical ZIP in root `SHA256SUMS.txt` failed the feature audit; do not use
it as the corrected installation. Bootloader unlocking/relocking, wiping data,
formatting and partition-layout changes are not part of this kernel update.

## Installation and verification

After the above evidence is available, first verify the existing recovery
without partition writes. Check logical-partition mappings, mount/read-only
state and the exact supported recovery or fastbootd write method. The prepared
image set preserves partition sizes, DTB/DTBO and Magisk init_boot. Recovery
needs matching modules because this device's recovery ramdisk shares the boot
kernel. Keep all five original coupled images and their hashes on the PC.

Do not use `fastboot boot` on this device. Do not change slot, wipe user data,
relock the bootloader or alter super metadata as a troubleshooting shortcut.
Kernel and driver updates are installed as a matched set, with read-back hash
verification. Boot the matching recovery first, then check Android and physical
hardware before starting container workloads or enabling ExtM backing storage.

Check normal boot, touch/fingerprint, storage, Wi-Fi/mobile data, charging,
root manager compatibility, loaded vendor modules and kernel logs. Extract the
running `/proc/config.gz` when available and compare against the build config.
Test IR physically, then test container/network/filesystem workloads separately.
Any physical button presses or on-device approvals must be performed by the user.
