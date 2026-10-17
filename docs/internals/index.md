# Internals

This directory records where epic-tools keeps its internal material.
The repository has no separate design history: each tool is a pinned
upstream tag plus a numbered patch queue (`tools/<package>/pin.json`
and `tools/<package>/patches/`), and the packaging rules live in the
agent file at the root. User-facing material (the [README](../../README.md),
the [user pages](../user/index.md) and the per-tool `README.md` files,
which the release build requires and the registry renders) stays where
it is.

Paths that moved here, and the pages deliberately left in place, are
listed in [MIGRATION.md](MIGRATION.md).

## Agent file

- [AGENTS.md](../../AGENTS.md): the contributor workflow, the D-10
  pin-plus-patch-queue rule, and the takeoff ritual. It stays at the
  root because the tooling requires it there.
