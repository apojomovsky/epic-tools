# Programmers

This reference lists every programmer the epic8 tool packages support. It is for you if you want to match the hardware on your desk to an `upload_protocol` value, a licence, and an upstream project.

| Hardware | Package | Select with | Licence | Upstream |
|---|---|---|---|---|
| XGecu TL866 programmers and the T48 | `tool-minipro` | `upload_protocol = minipro` | GPL-3.0-or-later | [minipro](https://gitlab.com/DavidGriffith/minipro) |
| PICkit2, PICkit3, and PKOB | `tool-pk2cmd` | `upload_protocol = pk2cmd` | Microchip PK2CMD Software License | [pk2cmd](https://github.com/jaka-fi/pk2cmd) |
| Kitsrus K150 and close relatives | `tool-picpro` | `upload_protocol = picpro` | GPL-2.0-only | [picpro](https://github.com/Salamek/picpro) |

## minipro

You use minipro with an XGecu TL866 universal programmer or a T48. You seat the part in the programmer socket or connect its programming header to your circuit, then select `upload_protocol = minipro`. The package sets up the part data files the program reads, so there is nothing for you to configure.

The program is GPL-3.0-or-later, and the package also carries the exact source it was built from, so you can rebuild the program you flash with.

## pk2cmd

You use pk2cmd with a PICkit2, a PICkit3, or a PKOB unit, then select `upload_protocol = pk2cmd`. The package ships the `PK2DeviceFile.dat` data file beside the program, so the program finds it without any path setup on your side.

pk2cmd is not open source. It is under Microchip's PK2CMD Software License, which permits redistribution for use with Microchip products when the copyright notice is shown. The package includes the licence and a `NOTICE.txt` file carrying that notice. This is the project's reading of that licence, not legal advice.

## picpro

You use picpro with a Kitsrus K150 or one of its close relatives. The adapter reaches your computer as a serial port, so besides `upload_protocol = picpro` you name the port with `upload_port`. Your unit must run firmware speaking protocol P18A. The package runs under PlatformIO's own interpreter and vendors its Python dependencies, so there is nothing for you to install.

The program is GPL-2.0-only, and its bundled Python libraries keep their own licences inside the package.

## Shared notes

On Linux, minipro and pk2cmd talk to USB through libusb, which ships as a separate shared library under `lib/`, never linked into the program, so you can replace it with your own build. The Windows packages do not bundle libusb.

Each programmer needs its own wiring and driver setup. The platform guides cover [minipro](https://github.com/apojomovsky/epic-platformio/blob/master/docs/programmers/minipro.md), [pk2cmd](https://github.com/apojomovsky/epic-platformio/blob/master/docs/programmers/pk2cmd.md), and [picpro](https://github.com/apojomovsky/epic-platformio/blob/master/docs/programmers/picpro.md).

If a programmer is missing here or marked experimental, see [What is in 1.0](https://apojomovsky.github.io/epic-docs/status/).
