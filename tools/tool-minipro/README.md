# tool-minipro

Unofficial repackaging. We don't develop minipro; it is the work of
Valentin Dudouyt, maintained today by David Griffith
([DavidGriffith/minipro](https://gitlab.com/DavidGriffith/minipro)),
under GPL-3.0-or-later. Not affiliated with or endorsed by them.

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
T48, TL866II Plus and TL866A/CS. The TL866CS has no ICSP header, so it
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

Report every problem with this package to
[epic-tools](https://github.com/apojomovsky/epic-tools/issues) first. We
triage it and forward only confirmed upstream bugs to
[DavidGriffith/minipro](https://gitlab.com/DavidGriffith/minipro). The
upstream authors did not make this build and are not responsible for it,
so please don't file package issues on their tracker.
