# Migration map: internal docs

No paths moved (epic-tools#60). This repository keeps its internal
material next to the code it describes: the agent file at the root,
each tool's pin and patch queue under `tools/<package>/`, and the
user pages under `docs/user/`. This file exists so the hub's
aggregate map can state that plainly, and so a future move records
itself here in the same table shape as the other repositories.

Not moved, by design: `AGENTS.md` (the agent file stays at the root),
`README.md` and `docs/user/` (user documentation),
`tools/tool-minipro/README.md`, `tools/tool-pk2cmd/README.md`,
`tools/tool-picpro/README.md` and `tools/tool-gdb/README.md`
(registry-rendered package pages the release build requires).
