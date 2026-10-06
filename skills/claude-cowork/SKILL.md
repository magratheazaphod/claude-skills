---
name: claude-cowork
description: How Claude Cowork (the agentic mode of the Claude desktop app) actually works on macOS, beyond the help center, and how to run real unattended work on it - where scheduled-task prompts and settings live on disk, local tasks vs cloud and device-bound routines, what a session can and cannot reach, how the scheduler decides to run, editing traps, and field-tested production patterns (prompts in git behind a stub, file handoff to local apps, pre-flight checks, debugging runs). Use before designing, editing or debugging a Cowork scheduled task or routine, connecting Cowork to a local app or repo, reasoning about what Cowork can access, or touching Cowork's data folder.
---

# Claude Cowork: how it actually works

Cowork is the agentic mode of the Claude desktop app: you give it folders,
connectors and a browser, and it plans and carries out a task. Anthropic's help
center explains how to *use* it. This skill covers the parts it leaves out:
where things live, what reaches what, and how scheduled work really runs.

**How this was verified.** Everything here was checked on macOS against Claude
Desktop **2.19675.1** in October 2026. Sources were the app's own bundled
JavaScript, its state files on disk, the run logs of real scheduled runs, and
the official help articles. Earlier findings date back to version 1.24012.9
(July 2026). Cowork changes fast, and it changed a lot on 2026-10-06. Check the
installed version first:

```bash
defaults read /Applications/Claude.app/Contents/Info.plist CFBundleShortVersionString
```

If it has moved well past 2.19675, treat specific paths and field names as
leads to re-check, not facts.

Official sources, which win on *behaviour* (append `.md` to a URL for raw text):

- [Schedule recurring tasks in Claude Cowork](https://support.claude.com/en/articles/13854387-schedule-recurring-tasks-in-claude-cowork)
- [Use Claude Cowork on web, desktop, and mobile](https://support.claude.com/en/articles/15520349)
- [Get started with Claude Cowork](https://support.claude.com/en/articles/13345190)
- For scheduler mechanics the Cowork pages leave out, the Claude Code Desktop
  page [Schedule recurring tasks](https://code.claude.com/docs/en/desktop-scheduled-tasks)
  is the best public reference. Both products use the same scheduler, but their
  file paths differ (see below).

None of the official docs say where anything is stored on disk.

## 1. Three ways Cowork work runs

| | Local session | Cloud session | Device-bound routine |
|---|---|---|---|
| Agent runs | on your Mac | Anthropic's cloud | Anthropic's cloud |
| Shell runs | Cowork's Linux VM on your Mac | cloud sandbox | Cowork's Linux VM on **your Mac** |
| Local folders | mounted directly | copies fetched for the task, deleted afterwards | through the bound device |
| Needs the Mac awake and the app open | yes | no | **yes** |
| Scheduled-task prompt lives | a file on your Mac | Anthropic's servers | Anthropic's servers |

**The 2026-10-06 change** (official): new Pro and Max Cowork sessions and
scheduled tasks run in the cloud by default, and the "Only on your computer"
setting is gone. Tasks created before that date keep running on the device.
Anything that needs local files, browser use, computer use or local connectors
still needs the desktop app open. For new work that must stay on the computer,
Anthropic now points to Claude Code Desktop.

**Migration of existing tasks.** The app can convert local scheduled tasks into
server-side routines in an automatic background sweep (`[RemoteMigrationSweep]`).
It runs on a timer, is switched on by a server-side flag, and only considers
enabled tasks. **It asks nobody.** Its "decline" outcomes are the system
declining (`declined_surface`, `declined_routines_disabled`,
`declined_mode_unavailable`), not a user prompt. It waits until the Mac is
awake and online, then converts tasks a few seconds apart. The app log
(`~/Library/Logs/Claude/main*.log`) records each one as `Remote migration
completed; local copy disabled: <task>`. Moving a task by hand stamps
`via: "manual"` instead. When it does, the local entry is
set `enabled: false` and stamped
`migratedToRemote: {triggerId: "trig_…", via: "sweep"}`. Its `SKILL.md` stays
on disk but **nothing reads it any more**. If you edit a local prompt file and
nothing changes, check for that stamp first.

## 2. Cowork vs Claude Code Desktop: same scheduler, different folders

The desktop app has two agentic surfaces: Cowork, and Claude Code Desktop
("CCD", the Claude Code CLI in a desktop window). Both use one scheduler, with
different settings:

| | Cowork | Claude Code Desktop |
|---|---|---|
| Task prompts | `<cowork-data>/Scheduled/<task-id>/SKILL.md` | `~/.claude/scheduled-tasks/<name>/SKILL.md` |
| Task settings | `<session-dir>/scheduled-tasks.json` | the app's userData folder |
| Execution | VM, folder grants | on the host, full user permissions |
| Enabled by | `coworkScheduledTasksEnabled` | `ccdScheduledTasksEnabled` |

So most of the CCD scheduling docs apply to Cowork (catch-up runs,
self-modification, approvals that stick). **The paths do not carry over.**

## 3. Where things live on macOS

- **App config:** `~/Library/Application Support/Claude/claude_desktop_config.json`.
  `coworkUserFilesPath` in this file is what the UI calls "Claude's app data
  folder" (written `<cowork-data>` here). Its default location has changed over
  versions; older installs used `~/Documents/Claude/`
  ([claude-code#54859](https://github.com/anthropics/claude-code/issues/54859)).
  It can be moved under Settings → Cowork.
- **Per-account state:**
  `~/Library/Application Support/Claude/local-agent-mode-sessions/<account-uuid>/<org-uuid>/`
  (written `<session-dir>` here). It holds `scheduled-tasks.json`,
  `spaces.json` (projects), one `local_<uuid>.json` per session, and
  `spaces/<space-id>/memory/`. There may be several account/org folders, so
  edit the one that actually has data.
- **Routine folder grants:** `routineFolderGrants` in the app config, keyed by
  trigger id.
- **The VM image:** `~/Library/Application Support/Claude/vm_bundles/`.
- **Routines themselves** live server-side. You can see them in the app, at
  claude.ai, or from Claude Code's `RemoteTrigger` tool (`get`, `list_runs`,
  `get_run_log`).

### A local scheduled task has two halves

| | Where | Holds |
|---|---|---|
| Prompt | `<cowork-data>/Scheduled/<task-id>/SKILL.md` | the instructions, with YAML frontmatter |
| Settings | `<session-dir>/scheduled-tasks.json` | everything else |

Each settings entry holds `id`, `cronExpression` or `fireAt` (a one-off run, in
epoch ms), `enabled`, `filePath`, `userSelectedFolders`, `userSelectedFiles`,
`chromeAllowedDomains`, `chromePermissionMode`, `approvedPermissions`,
`lastRunAt`, `lastScheduledFor`, and on newer versions `model`,
`permissionMode`, `missedRunScanFloor` and `migratedToRemote`. **No field holds
the prompt text.** So the prompt file changes *what* a task does, and the JSON
or the UI changes *when*, *whether* and *with what access*.

A project ("space") binds to folders by plain absolute path. These can be
anywhere on disk, not just under `<cowork-data>/Projects/`, which is only the
default for new projects. **A task's effective folders are the union of its own
`userSelectedFolders` and its project's folders.**

## 4. What a session can and cannot reach

**Local sessions often run in a split mode** (`hostLoopMode: true` in the
session JSON):

| Tool | Runs on | Path form |
|---|---|---|
| Read / Write / Edit / Grep / Glob | the **real host filesystem** | real paths like `/Users/you/project/...` |
| Shell | the **Linux VM** | `/sessions/<vm>/mnt/<folder>/...` |

So the same file has two paths depending on the tool. Something the shell
writes outside `/sessions/<vm>/mnt/`, including `/tmp`, is invisible to you and
to the file tools. A device-bound routine's shell (`device_bash`) runs in the
same VM, as a per-run user, with folders at `$HOME/mnt/<folder>`.

From the VM shell, as observed on one Mac:

- **No route to the host's localhost.** A server on `127.0.0.1` on the Mac is
  unreachable. Use files to talk to host-side apps (see `production-patterns.md`).
- **No route to github.com** (DNS failed), so `git push`, `git fetch` and `gh`
  fail. Local git commands work against the real mounted tree.
- **Files can't be deleted.** A leftover `.git/index.lock` can't be removed
  from inside the VM.

**Folders Cowork refuses to mount** (from the app's own list):

- `Scheduled/` and `Artifacts/` under the app data folder.
- `~/.claude/{scheduled-tasks,agents,plugins,commands,skills}`.
- Credential folders: `~/.ssh`, `~/.aws`, `~/.gnupg`, `~/.kube`, `~/.docker`,
  and several under `~/.config`.
- `~/Library/{Keychains,LaunchAgents,…}` and the system LaunchAgents and
  LaunchDaemons folders.
- Shell startup files and `.netrc`.

A folder is refused if it sits *inside* one of these, or if it *contains* one
or the app data folder itself. The practical trap: **if the app data folder is
inside `~/projects`, you can never grant all of `~/projects`**. Subfolders and
sibling folders are still fine. Keep the data folder out of any tree you might
want to grant whole.

Cowork's own session storage is deliberately unreadable from a session.

## 5. A task can rewrite itself, through tools and not files

Every Cowork session gets built-in tools for scheduled tasks:
`list_scheduled_tasks`, `create_scheduled_task`, `update_scheduled_task`,
`delete_scheduled_task`, `list_task_runs` and `run_scheduled_task`.

- `update_scheduled_task` can replace a task's prompt, schedule and enabled
  state, **including the task that launched the current run**. Only delete has
  a "not the task that launched this session" guard.
- A task can read its own prompt (it is mounted read-only), but it cannot
  change it by writing files.
- Tool approvals are stored on the task and reused on every later run, so
  one approval keeps applying while nobody is watching.

Treat an unattended task's prompt as something the task itself can change.
`production-patterns.md` covers how to pin it down.

## 6. How the scheduler decides to run

- **The only check before a run is that the prompt file exists.** Missing or
  deleted granted folders do not stop a run, and `lastRunAt` is set when the
  session starts. So **`lastRunAt` means "a session started", not "it worked."**
  Put your own check at the start of the prompt.
- **Missed runs catch up** the next time the app is open, or the device is
  online for a routine. A routine run's prompt includes both the scheduled time
  and the time it actually fired, and device-bound runs can fire hours late.
- **Re-enabling a task now waits for its next scheduled time.** On 1.x,
  enabling a task with no recent runs ran it immediately, whatever its day.
  Version 2.x records a floor at enable time (`missedRunScanFloor`), and the
  catch-up check ignores anything before it.

## 7. Editing Cowork's files by hand

- **Quit the app first.** `scheduled-tasks.json` and `spaces.json` are read
  once at startup and saved from memory. An edit made while the app runs is
  invisible to it and gets overwritten. Back up the file and check the JSON is
  still valid after editing.
- **Never symlink anything in `Scheduled/` or the session folder.**
  - The prompt writer refuses symlinks (`ELOOP`), so saving in the UI fails.
  - The JSON writer saves to a temporary file and renames it over the
    original, which **silently replaces a symlink** with a plain file. Your
    copy then stops getting updates and nothing tells you.
  - To version prompts, keep a one-way copy in a repo somewhere else, or use
    the stub pattern in `production-patterns.md`.
- **`spaces.json` was the live project store until the September 2026
  merge.** Before then, every project change was saved to it straight away.
  Since the merge, projects are claude.ai projects held on the server, and
  `spaces.json` is a leftover from the move. Check projects at claude.ai.
- The app is not App Sandboxed, so hand-written folder paths work. The
  exceptions are Desktop, Documents and Downloads, which macOS protects behind
  its own permission prompt.

## 8. Moving the app data folder

Change the setting in the app, then:

1. Quit the app.
2. Make sure the old folder is gone. A copy that stays behind means edits go
   somewhere nothing reads.
3. Update every `filePath` and `userSelectedFolders` entry, and each project's
   folders.
4. Search your home folder for the old path.
5. **Run one task by hand.** Nothing reports a broken path, and a clean search
   is not a working run.

Don't hard-code absolute paths that Cowork owns in anything outside Cowork,
because users can change them.

## 9. Running real work on it: the short version

For anything that runs unattended, read **`production-patterns.md`** in this
skill's folder. It has the full patterns and the reasons for each. The rules
that matter most:

1. **Keep the real prompt in git.** The prompt stored in Cowork is a stub that
   runs `git show origin/master:<file>`, so prompts get history and review, and
   a run can't rewrite its own future instructions.
2. **Hand data to local apps through files,** in an inbox folder with a written
   format, never over HTTP. The VM can't reach the host's localhost.
3. **Start every prompt with a pre-flight check** that a known file exists and
   isn't empty, and abort loudly if it fails. A run with nothing mounted still
   "succeeds".
4. **Run no git commands from the sandbox** other than that one read-only
   `git show`. The commands that succeed are the ones that do damage.
5. **Check outputs on disk, not the run's own summary.** Debug routines with
   `list_runs` and `get_run_log`.

## 10. What changed while this was being tracked (July to October 2026)

This is first-hand: what was seen to change on one Mac while running Cowork
tasks every day. It is not a full product changelog.

| When | Change | What it broke or fixed |
|---|---|---|
| Before mid-2026 | The app data folder defaulted to `~/Documents/Claude/` | macOS can deny the app access to Documents, which caused mount errors (claude-code#54859). The folder became movable under Settings → Cowork |
| July 2026 (1.24012.9) | Local scheduler. Tasks stored as a `Scheduled/<id>/SKILL.md` file plus a JSON entry | Enabling a task with no recent runs ran it **at once**, whatever its day. A weekly Tuesday task enabled on a Friday ran that afternoon |
| July 2026 | Split ("host-loop") sessions observed: file tools on the host, shell in the VM | The old "Cowork is a VM" picture became wrong for file paths. A path that works in Read can fail in the shell |
| August 2026 | Artifact format changed on 2026-08-19 (official) | |
| 2026-09-14 to 09-16 | **Cowork and chat merged into one Claude** (announced 2026-09-16, Pro/Max first). No mode picker; Claude decides per conversation whether to answer or do a multi-step task. Cowork "spaces" became claude.ai **projects**, now shared by chat and tasks (memory, instructions, files, scheduled tasks). On the Mac, the app converted each local space to a cloud project and **uploaded its memory files** (`space-memory-copy/` records each upload with the new `projectUuid`), two days before the announcement | Local `spaces.json` stopped being the live store, so editing it no longer changes anything. A space's memory now lives in the cloud project too |
| 2026-09-24 | A background sweep **converted local tasks into server-side routines** bound to the device, and turned off the local copies | Local `SKILL.md` files stopped being read without any warning. Prompts moved to the server, with no file and no history |
| September 2026 | Routine runs: agent in the cloud, shell (`device_bash`) in the Mac's VM, browser in the user's Chrome | Runs fire hours late when the Mac was asleep. The prompt shows both the scheduled and the actual fire time |
| By October 2026 (2.19675.1) | Re-enabling waits for the next scheduled time (`missedRunScanFloor`) | Fixes the surprise run on enable |
| By October 2026 | The protected-folder list grew (git and direnv config, shell history, login files, system launch folders). A refusal reason was renamed (`managed_root` → `managed_root_overlap`) | Some folders that could be granted before are now refused |
| By October 2026 | New built-in tools `list_task_runs` and `run_scheduled_task`. One-off tasks (`fireAt`), and per-task `model` and `permissionMode` | A task can check its own run history and start runs |
| By October 2026 | In split sessions the shell became a separate tool, and its prompt warns that files written outside `/sessions/<vm>/mnt/` are invisible | |
| 2026-10-06 | **Cloud by default** for new Pro/Max sessions and tasks, and "Only on your computer" removed (official). Older tasks stay on the device. Anthropic points local-only work to Claude Code Desktop | The biggest change so far: "Cowork runs on your Mac" is no longer the default |

What stayed the same throughout:

- The prompt-file / settings-JSON split for local tasks.
- Self-rewrite through `update_scheduled_task`, with no self-guard.
- The writer behaviour that breaks symlinks.
- The only check before a run being that the prompt file exists.
- No route from the VM to the host's localhost or to GitHub.
- No hand edits while the app is running.

The lesson: in four months the storage model, the place tasks execute and the
defaults all changed, and the only notice was a help article. **Design tasks so
a silent change fails loudly** (pre-flight checks, outputs you verify) instead
of trusting how things worked last month.
