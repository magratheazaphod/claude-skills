# Bakeoff: Claude Code with and without the cowork plugin

**Status: DRAFT for review. Freeze (commit) before any run; don't edit after.**

## Protocol

- **Arms:** (A) Claude Code with web search/fetch, no plugin; (B) the same plus
  the `cowork` plugin. Same model, same version, fresh config, empty working
  folder, no file or shell tools, so neither arm can read the tester's Mac.
- **Runs:** 12 questions x 2 runs x 2 arms = 48. Each question gets
  " Answer in under 200 words." appended.
- **Blind grading:** strip arm-identifying text (skill mentions, "the
  reference", links), shuffle, grade with a separate model against the key
  below. Jesse blind-grades a random 25% and we report agreement.
- **Scores per answer:** key facts hit (0-3); confidently wrong claims (count;
  a claim stated as fact that contradicts the key or a listed wrong claim);
  "would this solve the problem?" (yes/partly/no). Also tokens, cost, time, tool
  calls.
- **Controls (C):** questions the public docs answer well. Arm A should do fine
  on these; if it doesn't, the test is unfair.
- **"Cowork" named?** Half the questions avoid the product name, as many users
  would.

Ground truth comes from Anthropic's docs and live tests on 2026-10-22 (Claude
Desktop 3.1623.4), as recorded in the skill.

---

### P1. Edits ignored (no product name)
> I edited the instructions file for my scheduled Claude task on my Mac, but the runs still follow the old instructions. Why, and how do I fix it?

Key facts:
1. Likely a silent migration: a background sweep converted the local task to a server-side routine (cloud scheduled task) and disabled the local copy, so the file is no longer read.
2. Confirm via `migratedToRemote` / `enabled: false` on the task's entry in `scheduled-tasks.json`, or the app log line "Remote migration completed; local copy disabled".
3. Fix: edit the prompt where it now lives (the app or claude.ai), not the file.

Known wrong: "the prompt is copied at creation time"; "restart the app to reload the file".

### P2. Where it lives on disk (Cowork named)
> Where does Claude Cowork store a scheduled task's prompt and its settings on macOS?

Key facts:
1. Prompt: `<app data folder>/Scheduled/<task-id>/SKILL.md` (data folder set by `coworkUserFilesPath`).
2. Settings: `scheduled-tasks.json` under `~/Library/Application Support/Claude/local-agent-mode-sessions/<account>/<org>/`; no field holds the prompt.
3. Cloud and migrated tasks live on Anthropic's servers, not on disk.

Known wrong: `~/.claude/scheduled-tasks/...` (that's Claude Code Desktop); settings in the prompt file's frontmatter.

### P3. Ran but no output (no product name)
> My scheduled Claude task shows a recent last-run time but produced no output. Did it work? How do I make it reliable?

Key facts:
1. The last-run time is set when a session starts; it means "started", not "worked".
2. Missing or unmounted folders don't stop a run; it can run, find nothing and report a clean empty result.
3. Fix: a pre-flight check at the top of the prompt (a known file exists and is non-empty, else abort loudly), and verify outputs on disk.

Known wrong: "an updated last-run time means it completed successfully".

### P4. Push to GitHub from the cloud (no product name)
> My scheduled Claude task runs in the cloud. Can it push commits to my GitHub repo, and how should I write its prompt?

Key facts:
1. Yes, from the cloud shell, once the repo is attached with the session's `add_repo` tool (private repos and pushes need it; requires the Claude GitHub App).
2. Name `add_repo` in the prompt; Claude may not call it unprompted.
3. Some sessions lack `add_repo` (open issues #84581, #100164); fallback is pushing from the Mac or a Claude Code cloud task.

Known wrong: "cloud tasks can't reach GitHub"; "just give it a personal access token".

### P5. `gh pr create` fails (no product name)
> In a cloud Claude task, `git push` works but `gh pr create` fails with an HTTP 403. What's going on, and how do I open the PR?

Key facts:
1. The session proxy blocks GitHub's GraphQL API, which all `gh pr` commands use.
2. Use the REST API instead, e.g. `gh api repos/<owner>/<repo>/pulls -f head=... -f base=main -f title=...`.
3. It isn't a token or permissions problem with the repo (pushing works).

Known wrong: "re-authenticate gh"; "the GitHub App lacks pull-request permission".

### P6. Version the prompt with a symlink (Cowork named)
> I want my Cowork scheduled task prompts in git. Can I symlink the prompt file into my repo?

Key facts:
1. No: the prompt writer refuses symlinks (saving fails), and the settings writer silently replaces a symlink with a plain file.
2. Copy one way into the repo instead, or make the stored prompt a stub that loads the real one with `git show origin/<branch>:<file>`.
3. Migrated or cloud tasks have no local prompt file at all.

Known wrong: "symlinks work fine"; "use a hardlink" (breaks on checkout).

### P7. Can a task change itself (no product name)
> Can a scheduled Claude task change its own instructions or schedule while it runs?

Key facts:
1. Yes, through the built-in `update_scheduled_task` tool, including the task that is running.
2. Only deleting has a guard against the running task; it can't change its prompt by writing files.
3. Tool approvals persist on the task across runs, so treat an unattended task's prompt as mutable (pin it, e.g. the git stub).

Known wrong: "tasks can't modify themselves".

### P8. Can't grant a folder (Cowork named)
> Cowork won't let me connect my whole ~/projects folder, though it lets me connect folders inside it. Why?

Key facts:
1. Cowork refuses any folder that contains its own app data folder (or a protected folder like `~/.ssh`).
2. So the app data folder is probably inside `~/projects`.
3. Fix: move the app data folder elsewhere (Settings → Cowork), then update paths and test a task by hand.

Known wrong: "macOS Full Disk Access"; "too many files".

### C1. Localhost (control, Cowork named)
> Can a Claude Cowork task send data to a small web server I run on localhost on my Mac?

Key facts:
1. Not directly: the local shell runs in a VM with no route to the Mac's localhost.
2. Cloud sessions can't reach your network at all.
3. Workaround: write files to a connected folder that the server watches.

### C2. Laptop closed (control, no product name)
> Will my scheduled Claude tasks keep running when my laptop is closed?

Key facts:
1. Since 2026-10-06, new Pro/Max scheduled tasks run in the cloud and keep running.
2. Anything needing local files, the browser, computer use or local connectors needs the desktop app open.
3. Tasks created before 2026-10-06 that run on the computer still need it awake.

### C3. Move to Claude Code (control, Cowork named)
> How do I move a Cowork task over to Claude Code so it runs locally?

Key facts:
1. Open the task and select "Download task data".
2. Unzip it and open the folder in Claude Code.
3. Run `/port-task-data`.

### C4. Missed while asleep (control, no product name)
> My scheduled Claude task was due at 9am but my Mac was asleep. When does it run?

Key facts:
1. Cloud tasks run on time regardless.
2. Tasks bound to the Mac run once when it wakes (with the app open), for the most recent missed time only.
3. Older missed runs are discarded, not run in a burst.

Known wrong: "all missed runs fire on wake".
