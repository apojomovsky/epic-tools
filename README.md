# epic-tools

Programmer software for epic8, packaged for PlatformIO.

epic-tools turns three popular PIC programmers into PlatformIO tool packages.
Once they are in place, `pio run -t upload` finds the right programmer
software for your computer and writes your program to the chip, with nothing
to build or install by hand.

## What a tool package is

A PlatformIO tool package is a folder that PlatformIO downloads and keeps for
you. It holds a command line program that PlatformIO runs on your behalf, so
you never start it by hand.

Each package is built from the original upstream project, at one exact
release, with a few small changes the build needs. The download is checked
before it is unpacked. Each package carries its licence and a source
reference, and minipro also ships its exact source tarball.

## Which programmers

| Programmer | Package | Upstream project | Licence |
|---|---|---|---|
| XGecu TL866 series and T48 | `tool-minipro` | [minipro](https://gitlab.com/DavidGriffith/minipro) | GPL-3.0-or-later |
| PICkit2, PICkit3 and PKOB | `tool-pk2cmd` | [pk2cmd](https://github.com/jaka-fi/pk2cmd) (jaka-fi fork) | Microchip PK2CMD Software License |
| Kitsrus K150 and close relatives | `tool-picpro` | [picpro](https://github.com/Salamek/picpro) | GPL-2.0-only |

Each programmer needs its own wiring and driver setup. The guide for each one
is in the platform repository, linked below.

## How PlatformIO users get them

You normally do not install these packages by hand. The epic8 platform lists
each one as a dependency. When your project chooses a programmer with
`upload_protocol`, PlatformIO fetches the matching package the first time you
upload.

```ini
; platformio.ini
[env:blink]
platform = apojomovsky/epic8
board = pic16f877a
upload_protocol = minipro
```

The protocol names are `minipro`, `pk2cmd` and `picpro`. Pick the one that
matches the programmer on your desk, then run `pio run -t upload` as usual.

Programmer guides: [minipro](https://github.com/apojomovsky/epic-platformio/blob/master/docs/programmers/minipro.md),
[pk2cmd](https://github.com/apojomovsky/epic-platformio/blob/master/docs/programmers/pk2cmd.md) and
[picpro](https://github.com/apojomovsky/epic-platformio/blob/master/docs/programmers/picpro.md).

## Licences

The content of this repository is MIT licensed, see [LICENSE](LICENSE). The
tools it packages keep their own licences, and each package ships the licence
that applies to it.

- **minipro** is GPL-3.0-or-later. The package includes the exact source it
  was built from, so you can rebuild the program you flash with.
- **pk2cmd** is not open source. It is under Microchip's PK2CMD Software
  License, which allows redistribution for use with Microchip products when
  the copyright notice is shown. The package includes the licence and a
  `NOTICE.txt` file. This is the project's reading of that licence, not legal
  advice.
- **picpro** is GPL-2.0-only. Its bundled Python libraries keep their own
  licences inside the package.
- **libusb** is LGPL-2.1. On Linux it is shipped as a separate shared library,
  never linked into the program, so you can replace it with your own build.
  The Windows packages do not bundle libusb.

## Building the packages yourself

You need docker and python3. The compilers and libraries live in the build
images, so nothing else is installed on your computer.

```bash
make build                          # every tool for linux_x86_64 into dist/
make build-tool TOOL=tool-minipro   # one tool
make test                           # the test suite
```

Add `SYSTEM=windows_amd64` to build the Windows packages on Linux. Contributors
should read [AGENTS.md](AGENTS.md) first.

## Where this fits

epic-tools only supplies the programmers. The C compiler is
[epic-cc](https://github.com/apojomovsky/epic-cc), the hardware abstraction
layer is [epic-hal](https://github.com/apojomovsky/epic-hal), and the
PlatformIO platform that names these packages is
[epic-platformio](https://github.com/apojomovsky/epic-platformio). The
[epic8 hub](https://apojomovsky.github.io/epic-docs/) has the getting started
guides.

## Problems

Report a package that fails to install here. A bug in the upstream program
belongs to the upstream project, which is not responsible for these builds.
