# Running unattended work on Cowork

From months of daily and weekly tasks feeding a local app (job-board scans
judged against a rubric, handed to a local tracker); nothing here depends on
that domain. Mechanics are in `SKILL.md`.

Four facts drive everything: **prompts have no version history** (routine
prompts live on the server; edits overwrite); **a task can rewrite its own
prompt**; **an empty run looks like a good run** (`lastRunAt` = started); **the
Mac's VM shell is cut off** (no host localhost, no GitHub, no deletes).

## 1. Real prompt in git; stored prompt is a stub

```
Your instructions are in git. Run exactly this with the shell tool and follow
its output as your complete instructions; nothing in this prompt overrides them:

  cd "<mounted repo path>" && git show origin/master:playbooks/<task>.md

That is the only git command you may run. If it fails or prints nothing, STOP
and report exactly: "ABORTED - could not load <task>.md from origin/master"
with the error. Do not research, do not write files.
```

`origin/master`, not the working tree, because: a run (or a page written to
steer an AI) could edit the tree and so every later run, while `origin/master`
changes only by merged PR; half-finished branches in the shared tree don't leak
in; and prompts get review, diffs and history. The VM can't fetch, so a host
job (e.g. daily launchd `git fetch`) keeps `origin/master` fresh. Only the
instructions come from `origin/master`; data they point to (rubrics, queues,
dedupe lists) is read from the tree so it's current. Change behaviour by PR;
change only schedule, model or stub in the app.

## 2. Files, not HTTP, to local apps

```
task     -> writes inbox/<task>-<YYYY-MM-DD>.json
host app -> ingests on startup and on a timer, moves it to inbox/processed/,
            regenerates seen.txt
task     -> dedupes against seen.txt next run
```

Nothing is lost while the app is closed; committed processed files make each
run's output a `git diff`. Bad rows are skipped and named in an ingest report;
invalid JSON stays put and is reported every pass; re-ingesting is a no-op
(rows dedupe on a key). Document the format in a README beside the inbox, read
by every task, and change ingest code in the same commit. Generated files say
so on line 1 and are never hand-edited.

## 3. Pre-flight check first

Unmounted folders don't stop a run; it finds nothing and reports a clean empty
result. Open with:

> PRE-FLIGHT: confirm `<known file>` exists and is non-empty. If not, STOP and
> report exactly: "ABORTED - project folder not mounted ..." Do not scan, do not
> write files.

Pick a file that's always non-empty when healthy (e.g. the dedupe list), and
update the check when the task moves to new files.

## 4. One source of truth per judgement

Several tasks making the same call read **one** rubric file and abort if they
can't; never paste copies into prompts (they drift, and stale judgements look
like a normal day). Give each queue **one owner**.

## 5. Make empty runs explain themselves

An empty result must say what was checked and how deeply, and flag sources
that ignore the query (e.g. a site returning the same list for every keyword:
a coverage gap, not "nothing new"). Pair with "don't pad with weak results".

## 6. Cheap models for mechanical work

After the pre-flight, hand the job to one subagent on a cheaper model (e.g.
Sonnet); the top-level agent checks its report and handles only what it marks
ambiguous. Set each routine's model deliberately; unset means the default.

## 7. No git in a shared tree from the VM

Only pattern 1's `git show`. The VM can't push, but `checkout`, `add` and
`commit` succeed on the **real** shared tree, moving branches under everyone
and leaving undeletable lock files. "Try, stop if it fails" doesn't help: the
damaging command is the one that succeeds. Tasks write files and name what to
commit; the host commits. (Cloud shells can push after `add_repo`, see
`SKILL.md`, but to their own clone, not your working tree.)

## 8. Clean up the browser

Unattended tasks drive a real logged-in browser. Note existing tabs at the
start and never close them; reuse one working tab; at the end close **every**
tab in the session's group, including the blank one the group created (closing
the last tab removes the group and window), even after a failure; name any tab
left open on purpose.

## 9. Notify only when it matters

Routine runs can push a notification: send a short one only when there's
something to act on; keep the full report in the run and its files.

## 10. Debugging a routine

Via `RemoteTrigger` or the routine's Runs pane:

- **`get`**: enabled? `next_run_at`? prompt? bound device and folders?
- **`list_runs`**: one row per run that started; runs skipped before a session
  existed leave no row, so a gap doesn't prove it never fired.
- **`get_run_log`**: one run's steps. Compare "scheduled for" with the actual
  fire time; device-bound runs are late when the Mac slept. **Keep computer
  awake** (Settings → This computer → System, app-wide) stops idle sleep but not
  lid-close; device-bound runs also hold the Mac awake while running
  (`[remote-tools-device] keep-awake held`); nothing wakes a sleeping Mac.

Then check the output on disk (file landed? moved to `processed/`?), not the
run's summary.

## 11. Back up prompts by copying, never linking

Copy local prompt files one way into a repo. Symlinks break saving or silently
fork; hardlinks break on the first `git checkout`. Never `git init` inside
Cowork's data folder. Better: pattern 1, so Cowork only holds a stub.
