# AGENTS.md

`epic-tools` builds the programmer tools the epic8 platform flashes with as
PlatformIO tool packages: `minipro` (XGecu TL866 series), `pk2cmd` (PICkit2,
PICkit3, PKOB) and `picpro` (Kitsrus K150 and siblings). One directory per
tool under `tools/`, each a pinned upstream tag plus a small patch queue, and a
CI path that builds per host and publishes on a tag.

This repository packages other people's tools. It is not the compiler (that is
epic-cc), not the HAL (epic-hal), and not the PlatformIO platform
(epic-platformio).

## The decomposition of record

[`epic-cc/docs/46-public-beta-design.md`](https://github.com/apojomovsky/epic-cc/blob/master/docs/46-public-beta-design.md)
is the plan this repository exists to serve; **D-10** is the decision that
scopes it. Read it before touching a pin. The ticket that created this
repository is epic-platformio#40, and `tool-minipro`, `tool-pk2cmd` and
`tool-picpro` are epic-platformio#41, #42 and #43.

The D-10 rule that shapes everything here: **a pinned upstream tag plus a
patch directory, never a long-lived fork.** If a change is needed, it lands as
a numbered patch, gets sent upstream, and the pin moves when it lands. A patch
queue that keeps growing is the failure mode this design exists to avoid.

## Picking up work

Work across epic-cc, epic-hal, epic-platformio and epic-tools is coordinated
by [epic-tasks](https://github.com/apojomovsky/epic-tasks). Several agents,
from different providers and on different machines, share one GitHub account,
so the board is the only place that knows what is already taken. **Do not
choose a ticket by reading the issue list.** Every issue filed in this repo
must be on the epic8 board from the moment it is created (the canonical rule
lives in `epic-tasks`' `AGENTS.md`, "Board tracking" section).

Run once per machine (and after any env change):

0. `epic-tasks doctor`: checks `EPIC_AGENT_ID`, `EPIC_TASKS_PROJECT`, `gh` auth
   with `project` scope, and board reachability. Fix what it reports before
   claiming.

For every ticket:

1. `epic-tasks next` to see what you may take, `epic-tasks claim <repo>#<n>` to
   take it. Exit 2 means another agent won the race, so go back to `next`.
   Exit 3 means the board is unreachable: do the work and say so in the pull
   request. Exit 4 means stop and ask.
2. Create a worktree under `.worktrees/` and branch as
   `<type>/<issue>-<slug>`, for example `feat/40-repo-bootstrap` (see
   Worktrees below, never work on `master`).
3. Develop the fix or feature, then dispatch a separate reviewer for the code
   and address its findings (the Review gate, canonical in epic-tasks'
   `AGENTS.md`). Only then run the takeoff ritual (`epic-tasks takeoff`).
4. Open the pull request with `Closes #N`, then
   `epic-tasks review <repo>#<n> --pr <url>`. The body must use real newlines:
   copy-paste-safe ``gh pr create --body-file - <<'EOF'`` (or
   ``cat <<'EOF' > /tmp/pr_body.md`` + ``gh pr create --body-file /tmp/pr_body.md``),
   NEVER ``gh pr create --body "a\nb"``, the shell never expands ``\n`` so GitHub
   renders literal ``\n`` as text and the bullets collapse to one line
   (epic-cc#129).
5. After the PR merges, remove the worktree:
   `git worktree remove .worktrees/<name>`. Never remove a worktree before
   merge, the branch must stay reachable for review.

Set `EPIC_AGENT_ID` (`<runtime>@<host>`) and `EPIC_TASKS_PROJECT` once per
runtime and machine. `claim` refuses to act without an identity, because an
anonymous claim tells the other agents nothing.

Most tickets here live in epic-platformio, since that is the repository whose
upload layer consumes these packages. The PR says which issue it closes, and
that is what the board tracks.

## Worktrees

**All feature work happens in a worktree under `.worktrees/`**, never on
`master`, and worktrees are removed only after the PR merges:

```bash
git fetch origin master
git worktree add .worktrees/<name> -b <branch> origin/master
# ... work, PR, merge ...
git worktree remove .worktrees/<name>
```

Branch names are conventional: `feat/<description>`, `fix/<description>`,
`chore/<description>`, `docs/<description>`. The worktree keeps your master
checkout clean and lets several tasks run in parallel without touching each
other's trees. Squash merging keeps master plan-free. The default base is the
latest `origin/master`.

Worktree discipline is enforced by the takeoff ritual (`epic-tasks takeoff`
checks you are in a `.worktrees/` worktree and not on `master`).

## Takeoff ritual (before every PR)

Run `epic-tasks takeoff` before opening a PR. It is the shared skeleton used by
every epic repository (canonical checks live in
`epic-tasks/epic_tasks/takeoff.py`). It checks:

1. Working tree clean, branch not behind `origin/master` (or `$BASE_REF`).
2. **You are in a `.worktrees/` worktree**, not on `master`.
3. No plan files in the PR's final diff.
4. Commit hygiene: conventional single-line subjects, no trailers, no
   em-dashes, no whitespace errors.
5. **Comment and doc prose review.** `epic-tasks prose --verify` (part of this
   ritual) fails it on the mechanical rules: the 8-line block cap, no
   `@file`/`@brief` decoration, no iteration or verification narrative, no
   em-dashes. Content judgment stays the agent's.
6. **PR body hygiene: real newlines only.** Never an inline ``"a\n\n- b"`` that
   renders literally as ``\n`` on GitHub (epic-cc#129). Heal with
   ``gh pr edit --body-file``.

The ritual exits 1 with the exact fix list while blocking items are
outstanding. Don't skip it.

## Commit hygiene

- **Conventional Commits, single line.** `feat(scope): summary`, `fix(...)`,
  `chore(...)`, `docs(...)`, `build(...)`, `ci(...)`, `test(...)`. Scope is the
  tool (`minipro`, `pk2cmd`, `picpro`), `build`, or `ci`.
- **Never `Co-Authored-By:` or any other trailer, and no em-dashes.** The
  commit-msg hook rejects both. Use a comma, a colon, or a period instead.
- **PR bodies use real newlines.** ``gh pr create --body-file`` or a heredoc,
  never ``--body "line\nnext"``.
- Commit whenever a piece of work is finished; don't batch unrelated changes.
- Update the docs a change touches before calling it done.

## Ground rules

- **Approval gates are real.** Brainstorm, design, approve, implement. Present
  a design and stop until you get a yes, even for work that looks small.
- **No force pushes.** Rewriting a branch that already exists on the remote
  drops it for every other agent and clone; the pre-push hook refuses it. If
  the guard is triggered, rebase onto master and get the human's explicit
  go-ahead before re-running with `EPIC_FORCE_PUSH_APPROVED=1 git push
  --force-with-lease`.
- **A pin is a redistribution statement.** Every package ships its licence and
  a source reference (D-10), and each tool's licence adds its own terms. Never
  ship a package built from an archive whose digest does not match the pin, and
  never widen a licence's terms to make a build pass.
- **Never bundle a library statically.** Minipro and pk2cmd ship libusb
  (LGPL-2.1) as a shared library so a user can replace it. A static link would
  remove that right.
- **`pk2cmd` is not free software.** It is distributed under Microchip's
  PK2CMD licence, which permits redistribution for use with Microchip products
  with the notice shown. Its upstream is
  [jaka-fi/pk2cmd](https://github.com/jaka-fi/pk2cmd) (kair.us), the maintained
  fork, not `cjacker/pk2cmd-minus`. The reading of the licence here is the
  project's, not legal advice; the notice is the mitigation.
- **Upstreams are pinned by tag and commit, with the archive digest checked
  before extraction.** A pin that cannot be rebuilt byte-for-byte is not a pin.
- **Nothing but docker runs on the host.** Same rule as the rest of the
  ecosystem: no compiler, no PlatformIO, no Python packages installed to build
  a package. `scripts/build_tool.py` drives the container.

## Expression conventions (comments and docs)

1. **Why, not what.** Code says what it does; comments carry the non-obvious
   reason, the licence clause, the upstream quirk. A comment that restates the
   line below it is deleted.
2. **A comment must earn its lines.** More comment lines than code is a smell.
   The block ladder is 1 to 8 lines: 2 to 3 lines for a compact reason, 4 to 8
   only when the reason genuinely needs the room, over 8 is a hard failure of
   the prose gate.
3. **No decoration.** No `/* --- name --- */` separators, no `@file`/`@brief`
   boilerplate repeating the filename.
4. **No narrative.** No "fixed X by doing Y", no iteration or session prose.
   Verification claims about a change belong in the PR and commit.
5. `TODO`/`FIXME` carry a concrete reason or do not exist.
6. **No em-dashes in prose.** Not in comments, docs, or commit messages: use a
   comma, a colon, or a period and a new sentence. The takeoff ritual and the
   commit-msg hook enforce this.

## CI

`.github/workflows/ci.yml` runs on every push and PR: it validates every pin
and runs the suite, so a broken pin fails the pull request rather than the
release. It does not build packages: a build fetches upstream sources, which a
gate on every push should not depend on.

`.github/workflows/release.yml` runs on a `<tool>-v<version>` tag or a manual
dispatch. It builds the package, checks the licence and source reference are in
the archive, attaches it to a GitHub Release, and publishes it to the
PlatformIO registry. Publication is skipped with a warning when
`PLATFORMIO_AUTH_TOKEN` is absent, since no workflow can create that secret for
itself.

## Adding a tool

1. `tools/<package>/pin.json`: upstream url, page, tag, commit and the archive
   sha256; the licence and the file it ships; the build kind and its output;
   the systems.
2. Any patch the pinned tag needs goes in `tools/<package>/patches/`, numbered
   and sent upstream.
3. If the licence requires a visible notice, set `build.verify` with the
   argument that prints it and `banner_must_match`, so the build refuses to
   package a binary that does not carry it.
4. `make build-tool TOOL=<package>` builds it; `make test` covers the pin
   rules.
5. A new tool is a new ticket on the board, filed in epic-platformio, before
   the PR that adds it.
