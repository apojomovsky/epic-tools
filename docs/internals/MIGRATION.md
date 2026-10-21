# Migration map: internal docs

This repository keeps its internal material next to the code it
describes: the agent file at the root, each tool's pin and patch
queue under `tools/<package>/`, and the user pages under
`docs/user/`. This file exists so the hub's aggregate map can state
that plainly, and so a move records itself here in the same table
shape as the other repositories.

| Old path | New path |
| --- | --- |
| `tools/tool-gdb/` | `tools/tool-epic-gdb/` |

The GDB package took the epic8 product name (epic-tools#64), so no
package claims the bare upstream name in the registry namespace. The
`tool-gdb-v17.2.0` tag and release stay as history.

Not moved, by design: `AGENTS.md` (the agent file stays at the root),
`README.md` and `docs/user/` (user documentation),
`tools/tool-minipro/README.md`, `tools/tool-pk2cmd/README.md`,
`tools/tool-picpro/README.md` and `tools/tool-epic-gdb/README.md`
(registry-rendered package pages the release build requires).
