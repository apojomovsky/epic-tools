<h1 align="center">epic8-tools</h1>

<p align="center"><em>PlatformIO tool packages for the programmers the epic8 platform flashes with.</em></p>

<p align="center">

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) [![CI](https://github.com/apojomovsky/epic8-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/apojomovsky/epic8-tools/actions/workflows/ci.yml) [![status: early](https://img.shields.io/badge/status-early-yellow.svg)](#status)

</p>

[platform-epic8](https://github.com/apojomovsky/epic-platformio) makes `pio run`
compile a PIC project with [epic-cc](https://github.com/apojomovsky/epic-cc).
Flashing it needs a programmer tool, and the tools hobbyists own (`minipro` for
the XGecu TL866 series, `pk2cmd` for the PICkit family, `picpro` for the
Kitsrus K150) are not in any distribution. This repository turns each of them
into a PlatformIO tool package, so `pio run -t upload` resolves the right
binary for the host without the user building anything.

## Pinned upstream plus a patch queue, not a fork

Every tool is one directory under `tools/` holding a `pin.json`: the upstream
tag, the commit it resolved to, the sha256 of the exact source archive, the
licence, and what a build should produce.

```json
{
  "package": "tool-minipro",
  "version": "0.7.4",
  "upstream": {
    "url": "https://gitlab.com/DavidGriffith/minipro/-/archive/0.7.4/minipro-0.7.4.tar.gz",
    "tag": "0.7.4",
    "commit": "3808aecb6a1dac9906a9691b93820ee1bd2b7a18",
    "sha256": "e41fb5a97c74a7e9c7d012e864a622096e819180bec504069e34664f6a360531"
  },
  "license": {"spdx": "GPL-3.0-or-later", "file": "LICENSE"},
  "build": {"kind": "make", "output": "minipro"},
  "systems": ["linux_x86_64"]
}
```

When a change is needed before it reaches upstream, it lands as a numbered
patch in that tool's `patches/` directory rather than as a long-lived fork.
The queue is meant to be short: each patch is sent upstream, and the pin moves
forward when it lands. An empty `patches/` is the goal state, not an
unfinished one.

The digest is checked before anything unpacks it. A silently re-cut upstream
tag fails the build instead of producing a package built from something other
than what the pin names.

## Building

Nothing but docker is needed on the host; the toolchain lives in the pinned
build image.

```bash
make build                              # every tool, linux_x86_64, into dist/
make build-tool TOOL=tool-minipro       # one tool
make test                               # the suite CI runs
```

Each build fetches the pinned archive, verifies its digest, applies the patch
queue, builds in a container, and writes a PlatformIO package. The C tools
build in `docker/build/Dockerfile`, pinned by digest to `ubuntu:22.04`: a
released binary inherits that image's glibc as its compatibility floor, which
is why the base is pinned rather than tracking a tag. `picpro` is pure Python
and needs 3.12, above that image's 3.10, so it builds in its own
`docker/build/python.Dockerfile`.

## What every package ships

D-10 of [docs/46](https://github.com/apojomovsky/epic-cc/blob/master/docs/46-public-beta-design.md)
requires each package to carry its licence and a source reference, and each
tool's licence adds its own obligations. All of it is in the package, so
nobody has to reconstruct it from a release page.

| Package | Upstream | Licence | What ships |
|---|---|---|---|
| `tool-minipro` | gitlab.com/DavidGriffith/minipro 0.7.4 | GPL-3.0-or-later | Binary, `LICENSE`, `SOURCE.txt`, the exact upstream source tarball, `infoic.xml`/`logicic.xml`, libusb as a shared library |
| `tool-pk2cmd` | github.com/jaka-fi/pk2cmd v1.27.01 | Microchip PK2CMD | Binary, `license.txt`, `NOTICE.txt`, `PATCHES.txt`, `PK2DeviceFile.dat`, libusb as a shared library |
| `tool-picpro` | github.com/Salamek/picpro 0.4.1 | GPL-2.0-only | Vendored Python with every dependency's `dist-info` (which carries its own licence), `LICENSE`, `SOURCE.txt` |

libusb (LGPL-2.1) is bundled as a shared library, never linked statically, so
a user can replace it with their own build. It is resolved through a relative
`RUNPATH` (`$ORIGIN/lib`), so the package works without `LD_LIBRARY_PATH` and
without a system-wide install.

`pk2cmd` is distributed under Microchip's licence, not an open-source one.
Clause 1(b) permits distributing a modified version for use with Microchip
products provided a fixed copyright and modified-by notice is posted where end
users will see it. Upstream's own `-?l` banner prints that notice with
Microchip's literal `[INSERT YOUR NAME...]` placeholder, which satisfies
nothing, so `patches/0001-fill-the-modified-by-notice.patch` names the
modifier and the build refuses to package a binary whose banner does not carry
the completed text. `NOTICE.txt` repeats it in the package itself.

## Releasing

A tag `<tool>-v<version>` runs `release.yml`, which builds the package,
verifies the licence and source reference are in the archive, attaches it to a
GitHub Release, and publishes it to the PlatformIO registry. A manual
`workflow_dispatch` does the same for one tool or all of them.

**Registry publication needs a secret no workflow can create for itself.**
Add `PLATFORMIO_AUTH_TOKEN` to this repository's Actions secrets, from
`pio account token`, with the account's own username as the registry owner.
Without it a run still builds the package and publishes the GitHub Release,
with a warning, so a missing secret degrades rather than blocks.

Once published, a package is installed by name:

```ini
; platformio.ini
[env:upload]
platform = apojomovsky/epic8
upload_protocol = minipro
```

## Status

Early. The repository skeleton, the patch-queue build and the per-host
publishing path are in place; the individual tool packages are tracked as
epic-platformio#41 (`tool-minipro`), #42 (`tool-pk2cmd`) and #43
(`tool-picpro`). Only `linux_x86_64` is built; the pins and the workflow
already carry the `system` field a Windows host needs.

## Licence

MIT for this repository's own content. The tools it packages keep their own
licences, listed above and carried inside each package.
