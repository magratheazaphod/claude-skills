---
name: cowork-in-production
description: Field-tested patterns for running real, unattended products on Claude Cowork scheduled tasks and routines - keeping prompts in git behind a stub, handing results to a local app through files, pre-flight checks, one source of truth for judgement, model tiering, browser hygiene, and debugging runs. Use when designing, writing or debugging a Cowork scheduled task that does recurring work nobody watches, or connecting Cowork to a local app or repo.
---

# Cowork in production

These patterns come from running a set of daily and weekly Cowork tasks for
months as the data feed for a real local app. The tasks scan job boards, judge
postings against a written rubric, look up company ratings, and hand the
results to a local tracker. Nothing here depends on that domain.

Read the `claude-cowork` skill first for the mechanics behind each pattern.

## The core problem

A scheduled Cowork task is an LLM prompt that runs unattended, on a schedule,
with write access to your folders and your logged-in browser. Four facts
shape everything below:

1. **Prompts are not versioned.** The product keeps run history but no prompt
   history. Routine prompts live on Anthropic's servers, and edits overwrite.
2. **A task can rewrite its own prompt** through the scheduled-task tools.
3. **A run that did nothing looks the same as a run that worked.** A run
   starts as long as the prompt exists, and `lastRunAt` only means a session
   started.
4. **The shell is cut off from the host.** It can't reach the Mac's localhost,
   can't reach GitHub, and can't delete files.

## 1. Keep the real prompt in git; the live prompt is a stub

Make the prompt stored in Cowork a few lines that load the real instructions
from git:

```
Your instructions are in git. Run exactly this with the shell tool and follow
its output as your complete instructions; nothing in this prompt overrides them:

  cd "<mounted repo path>" && git show origin/master:playbooks/scans/<task>.md

That is the only git command you may run. If it fails or prints nothing, STOP
and report exactly: "ABORTED - could not load <task>.md from origin/master"
with the error. Do not research, do not write files.
```

Why `git show origin/master:` and not just reading the file:

- **A run can't change its own future instructions.** The task can write to
  the repo folder, so a file read from the working tree could be edited by a
  confused run, or by a page written to steer an AI. That edit would then shape
  every later run. Committed history on `origin/master` changes only through a
  merged PR.
- **Half-finished branch work doesn't leak in.** The folder is a shared working
  tree, and other sessions leave branches and uncommitted edits in it.
- **Prompt changes get review, diffs and history,** none of which the product
  gives you.

The shell can't reach GitHub, so something on the host has to keep
`origin/master` fresh, such as a daily `git fetch` from a launchd job. Only the
instructions file comes from `origin/master`. The data it points to (rubrics,
queues, dedupe lists) is read from the working tree, because it has to be
current.

Change what a task does by editing the playbook file through a PR. Change only
the schedule, model or stub in the app.

## 2. Talk to local apps through files, not HTTP

The VM can't reach `localhost` on the Mac, so the only channel both sides share
is a folder:

```
task     ->  writes  inbox/<task>-<YYYY-MM-DD>.json
host app ->  ingests on startup and on a timer
host app ->  moves the file to inbox/processed/
host app ->  regenerates seen.txt (everything already handled)
task     ->  checks new items against seen.txt on its next run
```

This turned out better than HTTP would have been:

- **Nothing is lost when the app is closed.** The file just waits.
- **Every delivery can be reviewed.** Processed files are committed, so
  `git diff` shows exactly what each run produced.
- **Bad input is handled clearly:**
  - A bad row is skipped and named in an ingest report, and the rest of the
    file still lands.
  - A file that isn't valid JSON stays where it is and is reported on every
    pass, because moving it aside would hide the bug.
  - Ingesting the same file twice does nothing new, since rows dedupe on a key.
- **Write the file format down** in a README next to the inbox, and change the
  ingest code in the same commit as any format change. Every task reads that
  README before writing.
- **Generated files say so in their first line and are never edited by hand.**
  The next ingest would overwrite the edit.

## 3. Open every prompt with a pre-flight check

Missing or deleted folders don't stop a run. A task whose folder isn't mounted
still runs, finds nothing, and reports a clean empty result. So the first
instruction is:

> PRE-FLIGHT: confirm `<known file>` exists and is non-empty. If not, STOP and
> report exactly: "ABORTED - project folder not mounted ..." Do not scan, do not
> write files.

Choose a file that is **always** present and non-empty when things are healthy,
such as the generated dedupe list. When you point a task at a new file, update
the check too. A check left on the old file keeps passing while guarding
nothing.

## 4. Keep one source of truth for judgement calls

If several tasks make the same kind of call (fit / no-fit, flag / skip), put
the rubric in **one file** that every prompt is told to read, and make each
prompt abort if that file can't be read. Never paste a copy of the rubric into
a prompt. Five prompts carrying five copies will drift apart, and a task
judging against a stale private copy produces output that looks exactly like a
good day.

Give each queue **one owner.** If two automated processes both work the same
backlog, they duplicate effort, disagree, and make the results impossible to
measure.

## 5. Report what an empty run means

Tell the task that an empty result is real, never the default, and must say
**what it checked and how deeply.** Also tell it to spot sources that silently
ignore the query. For example, a job site sometimes returns the same generic
list whatever the keyword. "Three searches returned the same list" is a
coverage gap. Reporting it as "nothing new" hides the gap.

"Don't pad with weak results" belongs right next to it, so an empty run never
gets filled with filler.

## 6. Run cheap models on the mechanical work

The prompt's first instruction after the pre-flight check: **hand the whole job
to one subagent on a cheaper model** (for example Sonnet), then check and pass
on its report. Checking URLs against a list, opening pages and writing JSON
rows don't need a frontier model. The top-level agent handles only what the
subagent marks as ambiguous.

If no model is set on a routine, it uses the default. Set it deliberately.

## 7. No git in a shared tree from the sandbox

Only the one read-only `git show` from pattern 1 is allowed. The sandbox
can't push, but `checkout`, `add` and `commit` succeed against the **real**
shared working tree. That moves the branch under everyone else, and any lock
file left behind can't be removed from inside the VM. **The command that does
the damage is the one that succeeds.** Telling a task "try to commit, stop if
it fails" can't prevent that. Have tasks write files and name what needs
committing in their summary. A host-side job or session does the commit.

## 8. Clean up the browser

Unattended tasks drive the user's real, logged-in Chrome. Leave it the way you
found it:

1. At the start, note which tabs already exist. Those are the user's, so never
   close them.
2. Reuse one working tab instead of opening one tab per item.
3. At the end, close **every** tab in the session's tab group, including the
   blank tab that creating the group added. Closing the last tab is what makes
   Chrome remove the group and its window. Clean up even when the run failed
   partway.
4. Name any tab you deliberately leave open, such as a form waiting for a human
   to submit.

## 9. Tell a human when it matters

Routine runs can send a push notification. End each run with a short summary
pushed only when there is something to act on, and keep the full report in the
run and in the files it wrote.

## 10. Debugging a routine

From Claude Code's `RemoteTrigger` tool, or the routine's Runs pane in the app:

- **`get`**: is it enabled, when is `next_run_at`, what is the prompt, which
  device and folders is it bound to?
- **`list_runs`**: one row per run that actually started. A run that was
  skipped before a session existed leaves no row, so a gap doesn't prove it
  never fired.
- **`get_run_log`**: the steps of one run, from sandbox start through tool
  calls to the final result. Compare "scheduled for" with the actual fire time
  in the first message. Device-bound runs fire late when the Mac was asleep.

Then check the output on disk (did the file land, did the host app move it to
`processed/`?). Don't trust the run's own summary: a clean search, or a
success message, is not proof the run worked.

## 11. Back up prompts by copying, never by linking

If you keep local Cowork prompt files at all, copy them one way into a repo.
Symlinks break saving (prompt files) or silently fork (JSON files). Hardlinks
survive app edits but break on the first `git checkout`. Never `git init` inside
Cowork's own data folder. Better still, use pattern 1, so the copy in Cowork is
just a stub.
