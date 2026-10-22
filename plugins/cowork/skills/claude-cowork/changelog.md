# Cowork changes seen July-October 2026

First-hand, from running Cowork tasks daily on one Mac; not a full changelog.

| When | Change | Effect |
|---|---|---|
| Before mid-2026 | Data folder defaulted to `~/Documents/Claude/` | macOS could deny Documents, causing mount errors (claude-code#54859); folder became movable |
| July (1.24012.9) | Local scheduler: `Scheduled/<id>/SKILL.md` + JSON entry | Enabling a task with no recent runs ran it at once, whatever its day |
| July | Split ("host-loop") sessions: file tools on host, shell in VM | A path that works in Read can fail in the shell |
| 2026-08-19 | Artifact format changed (official) | |
| 2026-09-14 to 16 | **Cowork and chat merged** (announced 09-16, Pro/Max first). Spaces became claude.ai projects shared by chat and tasks; the app uploaded each space's memory (`space-memory-copy/` logs it) | `spaces.json` stopped being the live store |
| 2026-09-24 | Sweep **converted local tasks to device-bound routines**, disabling the local copies | Local `SKILL.md` edits silently stopped mattering; prompts moved server-side with no history |
| September | Routine runs: agent in cloud, `device_bash` in the Mac's VM, browser in the user's Chrome (by October, a built-in browser by default) | Runs fire hours late when the Mac slept |
| By October (2.19675.1) | Re-enable waits for next slot (`missedRunScanFloor`) | No more surprise run on enable |
| By October | Protected-folder list grew (git/direnv config, shell history, login files, launch folders); `managed_root` → `managed_root_overlap` | Some previously grantable folders refused |
| By October | `list_task_runs`, `run_scheduled_task`; one-off `fireAt`; per-task `model`, `permissionMode`; shell became its own tool in split sessions | Tasks can read their own history and start runs |
| 2026-10-06 | **Cloud by default** for new Pro/Max sessions and tasks; "Only on your computer" removed (official) | "Cowork runs on your Mac" no longer the default |
| By 2026-10-22 (3.1623.4) | Major version 3: scheduler skip checks and recorded skips; routines renamed "cloud scheduled tasks" in docs; built-in browser; Keep computer awake; CCD worktrees; `/port-task-data` | Runs can be skipped for reasons unrelated to the task |
| 2026-10-22 | Cloud sessions: two shells (cloud VM behind a proxy, `device_bash` on the Mac). GitHub needs `add_repo`; then clone and push work, but `gh pr` (GraphQL) is blocked. Auto approval became the default in the new experience; cloud scheduled tasks run in auto mode | Unlike the Mac's VM, a cloud shell can use GitHub, for attached repos |

Unchanged throughout: prompt-file/settings-JSON split for local tasks;
self-rewrite via `update_scheduled_task`; the symlink-breaking writer; no
pre-run check that a task can do its job; no route from the Mac's VM to
localhost or GitHub; no hand edits while the app runs.
