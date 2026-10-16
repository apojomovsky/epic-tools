# tool-gdb

Unofficial repackaging. We don't develop GDB; it is the work of the
Free Software Foundation
([sourceware.org/gdb](https://sourceware.org/gdb/)),
under GPL-3.0-or-later. Not affiliated with or endorsed by them.

An epic8 build of GDB, the GNU debugger client. Debug firmware compiled
by epic-cc with breakpoints on C lines, stepping, and typed `print`,
with no system gdb on your side.

## Try it in 60 seconds

Build your firmware, then start the epic-cc simulator adapter against
the ELF+DWARF sidecar the compiler emits alongside the HEX:

```bash
epic-cc-gdbserver firmware.hex firmware.elf --port 3333
```

Point this package's gdb at the same sidecar and connect:

```bash
gdb firmware.elf -ex "target remote :3333"
```

`break main.c:42`, `step`, and `print counter` resolve against the
sidecar's line table and DWARF, exactly as the
[debugger design](https://github.com/apojomovsky/epic-cc/blob/master/docs/34-debugger-design.md)
describes.

## What this package holds

A gdb-only build: no gdbserver, no binutils, no simulator, no Python
scripting, no TUI. The only runtime libraries past the toolchain base
are GMP and MPFR, shipped as shared libraries under `lib/`. The exact
source tarball the binary was built from travels in the package.

Linux only for now; the Windows build is tracked separately.

## Links

- [GDB](https://sourceware.org/gdb/), the upstream project
- [epic-tools](https://github.com/apojomovsky/epic-tools), where this build is packaged
- [epic-platformio](https://github.com/apojomovsky/epic-platformio), the PlatformIO glue

## Where to report problems

Report every problem with this package to
[epic-tools](https://github.com/apojomovsky/epic-tools/issues) first. We
triage it and forward only confirmed upstream bugs to the
[GDB bug tracker](https://sourceware.org/bugzilla/). The upstream authors
did not make this build and are not responsible for it,
so please don't file package issues on their tracker.
