# tool-minipro

An epic8 build of minipro, the XGecu TL866 programmer software. Flash
8-bit PIC from `pio run -t upload`, with no build step on your side.

## Try it in 60 seconds

```ini
; platformio.ini
[env:epic8]
platform = apojomovsky/epic8
board = pic16f877a
upload_protocol = minipro
```

Seat the chip in the programmer's ZIF socket, then:

```bash
pio run -t upload
```

Selecting the protocol pulls this package automatically. The full guide,
including udev rules and wiring, is in
[`docs/programmers/minipro.md`](https://github.com/apojomovsky/epic-platformio/blob/master/docs/programmers/minipro.md).

## Supported parts and boards

Every beta board flashes through this package: `pic12f675`, `pic16f1937`,
`pic16f628a`, `pic16f877a`, `pic16f887` and `pic18f4550`. It drives the
T48, T56, TL866II Plus and TL866A/CS. The TL866CS has no ICSP header, so it
programs loose chips in the ZIF socket only.

## One example

```bash
pio run -t upload     # write firmware.hex to the chip
pio run -t erase      # bulk erase
pio run -t readback   # dump flash to .pio/build/<env>/readback.hex
```

## Links

- [minipro](https://gitlab.com/DavidGriffith/minipro), the upstream project
- [epic-tools](https://github.com/apojomovsky/epic-tools), where this build is packaged
- [epic-platformio](https://github.com/apojomovsky/epic-platformio), the PlatformIO glue

## Where to report problems

Packaging problems (wrong files in this package, install failures) belong
in [epic-tools](https://github.com/apojomovsky/epic-tools/issues).
Programmer or device-database bugs belong upstream, at
[DavidGriffith/minipro](https://gitlab.com/DavidGriffith/minipro).
Upstream did not make this build and is not responsible for it: check
with the epic-tools tracker first if you are unsure where a fault lies.
