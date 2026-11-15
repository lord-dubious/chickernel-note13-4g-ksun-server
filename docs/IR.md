# Redmi Note 13 4G stock IR path

## Evidence inspected on 2026-11-15

A public stock firmware dump supplies the following linked components:

- `vendor/lib64/hw/consumerir.qcom.so` and `vendor/bin/consumerird` contain
  `/dev/spidev0.1` (the HAL also contains the property name `ro.lirc.dev`).
- The base DTB includes enabled `qcom,spi-geni` at
  `/soc/qcom,qupv3_0_geni_se@4ac0000/spi@4a80000`, with enabled child
  `device@1`, compatible `lc,ir-spi`, chip select 1 and 1 MHz maximum clock.
- `vendor_dlkm/lib/modules/modules.load` lists `spidev.ko` and
  `spi-msm-geni.ko`. Those dumped modules report vermagic `5.15.94`.
- Pinned upstream `drivers/spi/spidev.c` already matches `lc,ir-spi` and
  includes device-specific transmit handling. Replacing it with a generic
  mainline driver or adding an invented GPIO node would discard this evidence.

Sources:
- [Stock dump](https://github.com/xiaomi-sapphire/redmi_sapphiren_dump/tree/missi_phone_global-user-14-UKQ1.231207.002-V816.0.3.0.UNHMIXM-release-keys)
- [Pinned SPI driver](https://github.com/chickendrop89/device_xiaomi_gemstones-kernel/blob/465df0508d2c6d987aa6ad59b8e3930023f5b944/drivers/spi/spidev.c)
- [Device variant descriptions](https://github.com/crdroidandroid/android_device_xiaomi_sapphire)

This dump is reference evidence, not proof of the connected phone's firmware.
Its `sapphiren` overlay contains `st,st21nfc`; `sapphire` is the non-NFC variant.

A compile of the corrected server configuration produced symbol-version
mismatches against these reference modules (13 for `spidev.ko`, 18 for
`spi-msm-geni.ko`, including `module_layout`; the latter also had two imports
outside the kernel export table). This candidate must not be assumed compatible
with those reference modules. The connected phone's modules still need to be
collected and checked. Do not force-load a mismatched module or remove version
checks to conceal the problem. Use `scripts/check_module_versions.py` to compare
the actual module copies with the build's exported symbol table without loading.

## Integration choice

The native fragment preserves SPI and adds generic LIRC capabilities, but does
not force `SPI_SPIDEV` or `SPI_MSM_GENI` built-in over the supplied vendor
modules. Disabled built-in options do not imply a missing driver when a ROM
ships it as a module. GPIO/PWM TX drivers are not the stock IR restoration.
The build does not modify vendor modules, DTB/DTBO, permissions or SELinux.

Before selecting an IR fix, inspect the live phone's:

1. `/dev/spidev0.1`, `/sys/bus/spi/devices`, `/proc/modules`, and available
   `spidev.ko`/`spi-msm-geni.ko` files and module-load configuration.
2. Kernel module errors, symbol/version failures, SPI probe results and IR
   service logs. Root may be needed for kernel logs; a missing log is not a pass.
3. IR HAL/service registration, permissions, SELinux denials and any
   `ro.lirc.dev` override.
4. Actual boot DT/vendor modules and ROM/kernel/KMI identity.

Keep working vendor modules and device trees. If they fail to load with a
replacement kernel, resolve that compatibility issue explicitly rather than
blindly mixing modules or replacing DTBO. A successful API call does not prove
emission: use an appliance with known remote settings or a suitable IR camera
for a physical transmission check after boot.
