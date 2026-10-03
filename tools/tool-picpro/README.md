# tool-picpro

Unofficial repackaging. We don't develop picpro; it is the work of Adam
Schubert (Salamek) ([Salamek/picpro](https://github.com/Salamek/picpro)),
under GPL-2.0-only. Not affiliated with or endorsed by them.

An epic8 build of picpro, the Kitsrus K150 programmer software. Flash
8-bit PIC from `pio run -t upload`, with no build step on your side.

## Try it in 60 seconds

```ini
; platformio.ini
[env:epic8]
platform = apojomovsky/epic8
board = pic16f877a
upload_protocol = picpro
upload_port = /dev/ttyUSB0
```

Seat the chip in the K150 ZIF socket, then:

```bash
pio run -t upload
```

Selecting the protocol will pull this package automatically once the
platform declares it; until then put it on `PATH` or point
`EPIC8_PICPRO_PATH` at it. The K150 must
run P18A firmware; older firmware is not supported. The full guide is in
[`docs/programmers/picpro.md`](https://github.com/apojomovsky/epic-platformio/blob/master/docs/programmers/picpro.md).

## Supported parts and boards

Four beta parts: `pic16f877a`, `pic16f628a`, `pic12f675` and
`pic18f4550`. The `pic16f887` and `pic16f1937` have no picpro entry, so
those boards refuse this protocol and name the tools that work. It
drives a K150, K128, K149 or K182.

## One example

```bash
pio run -t upload     # write firmware.hex to the chip
pio run -t erase      # bulk erase
pio run -t readback   # dump flash to .pio/build/<env>/readback.hex
```

## Links

- [picpro](https://github.com/Salamek/picpro), the upstream project
- [epic-tools](https://github.com/apojomovsky/epic-tools), where this build is packaged
- [epic-platformio](https://github.com/apojomovsky/epic-platformio), the PlatformIO glue

## Where to report problems

Report every problem with this package to
[epic-tools](https://github.com/apojomovsky/epic-tools/issues) first. We
triage it and forward only confirmed upstream bugs to
[Salamek/picpro](https://github.com/Salamek/picpro). The upstream authors
did not make this build and are not responsible for it, so please don't
file package issues on their tracker.
