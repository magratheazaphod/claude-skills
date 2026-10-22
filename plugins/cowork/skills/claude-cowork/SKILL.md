---
name: claude-cowork
description: How Claude Cowork (the desktop app's agentic mode, now "just Claude") works on macOS beyond the help center - where scheduled tasks live, local vs cloud vs device-bound runs, what a session can reach (incl. GitHub), scheduler behaviour, editing traps, production patterns. Use before building, editing or debugging a Cowork/Claude scheduled task or routine, or connecting it to local files, apps or a repo.
---

# Claude Cowork: how it actually works

Covers what the help center leaves out: where things live, what reaches what,
how scheduled work really runs. Verified on macOS against Claude Desktop
2.19675.1 and **3.1623.4** (2026-10-22) from the app bundle, on-disk state, run
logs and live sessions. Check the installed version first; well past 3.1623,
treat paths and field names as leads, not facts:

```bash
defaults read /Applications/Claude.app/Contents/Info.plist CFBundleShortVersionString
```

Docs now call routines **cloud scheduled tasks**; this skill says "routine", as
the app code and Claude Code's `RemoteTrigger` do. Official docs win on
behaviour (append `.md` for raw text): [scheduled tasks](https://support.claude.com/en/articles/13854387),
[surfaces](https://support.claude.com/en/articles/15520349),
[getting started](https://support.claude.com/en/articles/13345190),
[architecture](https://support.claude.com/en/articles/14479288), and for
scheduler mechanics [Claude Code Desktop scheduled tasks](https://code.claude.com/docs/en/desktop-scheduled-tasks)
(same scheduler, different paths). No official doc says where anything is on disk.

Also in this folder: `production-patterns.md` (running unattended work) and
`changelog.md` (what changed July-October 2026).

## 1. Where work runs

| | Local session | Cloud session | Device-bound routine |
|---|---|---|---|
| Agent | your Mac | Anthropic's cloud | Anthropic's cloud |
| Shell | Cowork's Linux VM on the Mac | cloud VM, **plus** `device_bash` in the Mac's VM for connected folders | the Mac's VM |
| Local folders | mounted | via `device_bash`, only while the app is open | via the bound device |
| Needs Mac awake + app open | yes | no (yes for local files, browser, computer use, local connectors) | **yes** |
| Prompt lives | file on the Mac | server | server |

Since **2026-10-06** new Pro/Max sessions and tasks run in the cloud; "Only on
your computer" is gone; older tasks stay on the device. Cloud sessions reach
local folders only if started on desktop or scheduled, and lose them if the app
closes (the session keeps running). Per-file copies fetched to the cloud are
deleted with the session. For local-only work Anthropic points to Claude Code
Desktop: "Download task data", then `/port-task-data`. In the unified
experience, **Auto** approval is the default on Pro/Max/Team, and cloud
scheduled tasks run in auto mode.

**Silent migration.** A background sweep (`[RemoteMigrationSweep]`, timer,
server flag, enabled tasks only) converts local tasks into routines. **It asks
nobody**; its ~16 `declined_*` outcomes are system decisions. It waits for the
Mac to be awake and online, then converts tasks seconds apart, logging
`Remote migration completed; local copy disabled: <task>` in
`~/Library/Logs/Claude/main*.log`. The local entry gets `enabled: false` and
`migratedToRemote: {triggerId: "trig_…", via: "sweep"}` (`"manual"` if moved by
hand); its `SKILL.md` stays but **nothing reads it**. Edited a prompt file and
nothing changed? Check for that stamp.

## 2. Cowork vs Claude Code Desktop (CCD)

One scheduler, different storage, so CCD's scheduling docs mostly apply
(catch-up, self-modification, sticky approvals) but **paths don't**:

| | Cowork | CCD |
|---|---|---|
| Prompt | `<cowork-data>/Scheduled/<task-id>/SKILL.md` | `~/.claude/scheduled-tasks/<name>/SKILL.md` |
| Settings | `<session-dir>/scheduled-tasks.json` | app userData |
| Runs | VM, folder grants | host, full user permissions, optional per-run worktree |
| Flag | `coworkScheduledTasksEnabled` | `ccdScheduledTasksEnabled` |

## 3. On disk

- **App config** `~/Library/Application Support/Claude/claude_desktop_config.json`:
  `coworkUserFilesPath` = "Claude's app data folder" (`<cowork-data>`), movable
  in Settings → Cowork; old default `~/Documents/Claude/` (claude-code#54859).
  `routineFolderGrants`, keyed by trigger id (seen populated on 2.x only).
- **Per-account** `<session-dir>` =
  `~/Library/Application Support/Claude/local-agent-mode-sessions/<account>/<org>/`:
  `scheduled-tasks.json`, `spaces.json`, `local_<uuid>.json` per session,
  `spaces/<id>/memory/`. Several account/org folders may exist; edit the one
  with data.
- **VM image** `…/Claude/vm_bundles/`. **Routines** are server-side: app,
  claude.ai, or `RemoteTrigger` (`get`, `list_runs`, `get_run_log`).

A local task = prompt file (`Scheduled/<id>/SKILL.md`, YAML frontmatter) +
settings entry. Entry fields: `id`, `cronExpression` or `fireAt` (one-off,
epoch ms), `enabled`, `filePath`, `userSelectedFolders`, `userSelectedFiles`,
`userSelectedProjectUuids`, `chromeAllowedDomains`, `chromePermissionMode`,
`approvedPermissions`, `permissionMode`, `model`, `lastRunAt`,
`lastScheduledFor`, `missedRunScanFloor`, `disableJitter`, `notifySessionId`,
`observedToolUse`, `createdAt`, `migratedToRemote(At)`, `migratedFromSpaceId`.
**No field holds the prompt**: the file sets *what*, the JSON/UI sets *when*,
*whether* and *with what access*. A task's folders = its own plus its
project's (projects bind folders by absolute path, anywhere on disk).

## 4. What a session can reach

**Local split sessions** (`hostLoopMode: true`): Read/Write/Edit/Grep/Glob hit
the real host (`/Users/you/...`); the shell runs in the VM
(`/sessions/<vm>/mnt/<folder>/...`). Shell writes outside that mount, incl.
`/tmp`, are invisible to you and the file tools. `device_bash` runs in the same
VM as a per-run user, folders at `$HOME/mnt/<folder>`.

From the Mac's VM shell (verified on 2.x): **no route to the Mac's localhost**
(talk to host apps through files), **no route to github.com** (DNS fails;
local git on the mounted tree works), **can't delete files** (a stale
`.git/index.lock` sticks).

**Refused mounts:** `Scheduled/` and `Artifacts/` in the data folder;
`~/.claude/{scheduled-tasks,agents,plugins,commands,skills}`; `~/.ssh`,
`~/.aws`, `~/.gnupg`, `~/.kube`, `~/.docker`, parts of `~/.config`;
`~/Library/{Keychains,LaunchAgents,…}` and system launch folders; shell startup
files, `.netrc`. Also any folder inside one of these or *containing* one or the
data folder, so **a data folder inside `~/projects` blocks granting all of
`~/projects`**. Cowork's own session storage is unreadable from sessions.

**Cloud sessions have two shells** (tested 2026-10-22):

| | Cloud shell | `device_bash` |
|---|---|---|
| Where | x86_64 cloud VM, `root`, empty `/home/claude` | the Mac's VM, per-run user |
| Folders | none | connected ones at `$HOME/mnt/<folder>` |
| Network | mandatory proxy, allow-listed destinations only | VM egress filter |

Both use UTC. Anything that must land on the Mac goes through `device_bash`.

**GitHub from the cloud shell:** `git`/`gh` are installed; `GH_TOKEN` is a
proxy placeholder (`prox…`). Public repos read without setup (tested with
GitHub connected and the Claude GitHub App installed). Private repos and pushes
need the repo attached with the **`add_repo`** tool (`list_repos` shows reach
and push rights); it returns a shallow clone command and asks for
`register_repo_root` afterwards. Clone, commit and push worked with and without
a folder connected. Claude may not call `add_repo` unprompted, so **name it in
the prompt**. claude-code#84581 and #100164 report sessions lacking `add_repo`;
then push from the Mac or use a Claude Code cloud task.

## 5. A task can rewrite itself

Built-in tools: `list_scheduled_tasks`, `create_scheduled_task`,
`update_scheduled_task`, `delete_scheduled_task`, `list_task_runs`,
`run_scheduled_task`. `update_scheduled_task` can change prompt, schedule and
enabled state **of the task running it**; only delete refuses that. The prompt
is mounted read-only, so files can't change it, but tools can. Tool approvals
persist on the task and apply to every later run.

## 6. Scheduler

- **Nothing checks a run can do its job.** 3.x skips due runs only for: not
  signed in, per-task/global run limits (server flag, usually off), a Dispatch
  hold, host not ready (`host_unavailable`), or throttling (≤15 min). Missing
  folders don't stop a run, and `lastRunAt` is set at session start: it means
  **"started", not "worked"**. Put a check at the top of the prompt. CCD's
  History shows skips and reasons.
- **Recurring runs are delayed on purpose:** fixed per task, ≤10 min (server
  flag), logged `Delaying dispatch for <task> by <n>s (jitter)`; off with
  `disableJitter`. One-off runs fire on time.
- **Missed runs catch up once,** for the latest missed slot, when the app
  starts or the Mac wakes (CCD docs: 7-day lookback). Routines catch up when
  the device is online; their prompt shows scheduled and actual fire times, and
  device-bound runs can be hours late.
- **Re-enabling waits for the next slot** (`missedRunScanFloor`, since 2.x; 1.x
  ran it at once).

## 7. Hand-editing

- **Quit the app first.** `scheduled-tasks.json` is read at startup and saved
  from memory; live edits are ignored and overwritten. Back up; validate JSON.
- **Never symlink in `Scheduled/` or `<session-dir>`** (seen on 2.x): the
  prompt writer fails (`ELOOP`), and the JSON writer's temp-file rename silently
  replaces the link with a plain file. Copy one way to a repo, or use the stub
  pattern.
- **`spaces.json` is dead** since the September 2026 merge; projects are
  claude.ai projects now.
- The app isn't sandboxed, so hand-written paths work, except Desktop,
  Documents and Downloads (macOS permission prompt).

**Moving the data folder:** change it in the app, quit, make sure the old
folder is gone, update every `filePath`, `userSelectedFolders` and project
folder, search your home folder for the old path, then **run one task by
hand**: nothing reports a broken path. Don't hard-code Cowork-owned paths
elsewhere.

## 8. Unattended work: the short version

Full reasoning in `production-patterns.md`:

1. **Real prompt in git**; the stored prompt is a stub running
   `git show origin/master:<file>`, so prompts get review and history and a run
   can't rewrite its future instructions.
2. **Files, not HTTP,** to local apps: an inbox folder with a written format.
3. **Pre-flight check first:** a known file exists and isn't empty, else abort
   loudly. A run with nothing mounted still "succeeds".
4. **No git from the VM** beyond that one `git show`; the commands that succeed
   do the damage.
5. **Verify outputs on disk,** not the run's summary.

Design so a silent product change fails loudly: in four months storage, place
of execution and defaults all changed, announced only in help articles.
