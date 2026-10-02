# tool-pk2cmd

An epic8 build of pk2cmd, the PICkit2 and PICkit3 command line
programmer. Flash 8-bit PIC from `pio run -t upload`, with no build
step on your side.

## Try it in 60 seconds

```ini
; platformio.ini
[env:epic8]
platform = apojomovsky/epic8
board = pic16f877a
upload_protocol = pk2cmd
```

Wire the PICkit ICSP header to the target (VPP/MCLR, VDD, GND, PGD,
PGC), then:

```bash
pio run -t upload
```

Selecting the protocol pulls this package automatically. The full guide,
including clone firmware and udev rules, is in
[`docs/programmers/pk2cmd.md`](https://github.com/apojomovsky/epic-platformio/blob/master/docs/programmers/pk2cmd.md).

## Supported parts and boards

The bundled `PK2DeviceFile.dat` (Microchip's own 1.62.14) covers every
board in `boards/`: `pic12f675`, `pic16f1937`, `pic16f628a`,
`pic16f877a`, `pic16f887` and `pic18f4550`. It drives a PICkit2, a
PICkit3, a PKOB, or a PICkit3-protocol clone. Newer MSB-first parts
(PIC16F18xxx, PIC18 Q families) are not in this device file.

## One example

```bash
pio run -t upload     # write firmware.hex to the chip
pio run -t erase      # bulk erase
pio run -t readback   # dump flash to .pio/build/<env>/readback.hex
```

## Links

- [jaka-fi/pk2cmd](https://github.com/jaka-fi/pk2cmd), the upstream project
- [epic-tools](https://github.com/apojomovsky/epic-tools), where this build is packaged
- [epic-platformio](https://github.com/apojomovsky/epic-platformio), the PlatformIO glue

## Where to report problems

Packaging problems (wrong files in this package, install failures) belong
in [epic-tools](https://github.com/apojomovsky/epic-tools/issues).
Programmer bugs belong upstream, at
[jaka-fi/pk2cmd](https://github.com/jaka-fi/pk2cmd).
Upstream did not make this build and is not responsible for it: check
with the epic-tools tracker first if you are unsure where a fault lies.

Note: pk2cmd is Microchip-licensed, not open source. Redistribution for
use with Microchip products is permitted with the notice the package
carries in `NOTICE.txt`.
