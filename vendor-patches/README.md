# Pinned sapphire external-driver repairs

`vendor-source-lock.json` pins the external source and each applied patch. The
driver builder rejects other tracked source edits, except the upstream tree's
tracked compiler-generated `*.o.d` and `*.o.symversions` files. Before compiling,
the tracked CRC sidecars and their corresponding objects are removed so the
compiler must regenerate them. Stock export CRCs are not imported.

The patches correct C function prototypes/return types, make trace includes
independent of a developer's directory layout, guard the IPA hibernation callback
with the same condition as its definition, and make an existing QMI-to-IPA enum
conversion explicit. RMNET WLAN formatting preserves its C token sequence and
keeps compiler warnings enabled.

Build the common device modules and external providers against the same GKI
Image. `scripts/build_device_drivers.py` preserves kernel built-ins, checks
initial compiler-generated ABI signatures, links fresh external module ELFs
against the GKI's actual BTF, and checks all versioned imports and export owners.
These are build checks; they do not replace physical hardware validation.
