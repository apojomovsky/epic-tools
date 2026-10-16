# Tools

This page explains what the epic8 programmer packages are and how they reach your computer. It is for you if you are choosing a programmer or tracing an upload problem.

## What a package is

A PlatformIO tool package is a folder that PlatformIO downloads and keeps for you. It holds a command line program that PlatformIO runs on your behalf, so you never start it by hand.

Each package is built from the original upstream project at one exact release. The download is checked before it is unpacked. Each package carries its licence and a source reference, so you can see where the program came from and under which terms you may use it.

There is a package for each supported host, so the same project uploads from Linux and from Windows without any change on your side.

## How the packages reach you

You normally do not install these packages by hand. The epic8 platform lists each one as a dependency. Your project names its programmer with `upload_protocol`, and PlatformIO fetches the matching package the first time you upload. You pick the name that matches the programmer on your desk: `minipro`, `pk2cmd`, or `picpro`.

If an upload fails because the programmer software is missing or wrong, check that `upload_protocol` names the programmer you actually connected, then run the upload again and watch which package PlatformIO fetches.

## Where next

- [Programmers](programmers.md) lists every supported programmer with its package, its licence, and its upstream project.
- The platform guides cover wiring and drivers for [minipro](https://github.com/apojomovsky/epic-platformio/blob/master/docs/programmers/minipro.md), [pk2cmd](https://github.com/apojomovsky/epic-platformio/blob/master/docs/programmers/pk2cmd.md), and [picpro](https://github.com/apojomovsky/epic-platformio/blob/master/docs/programmers/picpro.md).
- [What is in 1.0](https://apojomovsky.github.io/epic-docs/status/) tracks which programmers are supported, experimental, or planned.
