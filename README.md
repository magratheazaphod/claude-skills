# claude-skills

Agent skills by Jesse Day, written from months of daily use.

| Skill | What it covers |
|---|---|
| [`claude-cowork`](skills/claude-cowork/SKILL.md) | How Claude Cowork actually works on macOS beyond the help center: where tasks live on disk, local tasks vs routines, what a session can reach, how the scheduler decides to run, the editing traps, and a log of what changed from July to October 2026. Its [`production-patterns.md`](skills/claude-cowork/production-patterns.md) covers running unattended products on Cowork: prompts in git behind a stub, file handoff to local apps, pre-flight checks, model tiering, browser hygiene, and debugging routines |

Cowork changes fast. The skill says which app version and date it was checked
against. Where a skill and Anthropic's docs disagree about *behaviour*, trust
the docs and open an issue.

## Install

Claude Code:

```
/plugin marketplace add magratheazaphod/claude-skills
/plugin install cowork@magratheazaphod-skills
```

Or copy a folder from `skills/` into `~/.claude/skills/`. To use a skill in
Claude or Cowork, upload it as a skill.

## Keeping it honest

Cowork changes without notice, so `checks/drift.py` tests the skills against
reality. It runs on a Mac with Claude Desktop installed; it can't run in CI,
because the thing under test is the app itself.

- **Version:** flags any app update, and calls out major versions.
- **Anchors:** each important claim is tied to a string that must still appear
  in the app bundle (`checks/anchors.json`). A missing anchor names the skill
  section to re-check.
- **Docs:** flags any text change in the official Cowork articles.

```
python3 -I checks/drift.py            # exit 1 on drift
python3 -I checks/drift.py --issue    # also open or update a GitHub issue
python3 -I checks/drift.py --rebaseline   # only after re-verifying the skills
```

It runs weekly on Mondays at 10:00 via launchd
(`checks/launchd/com.jesse.claude-skills-drift.plist`, installed as a copy in
`~/Library/LaunchAgents/`), logging to `~/Library/Logs/claude-skills-drift.log`.
If the check itself crashes, that also opens an issue, so a broken check can't
look like a quiet week. The job waits up to 15 minutes for the network first,
since the Mac is often just awake and offline. If GitHub still can't be
reached, it posts a macOS notification instead, and a run that finds no
completed check in the last 8 days reports that too.

Passing anchors means the app's internals still contain what the claims rely
on. It does not prove the behaviour is unchanged. A version or docs change
starts a manual review; only a full review updates the version a skill says it
was checked against.

## Provenance

Written with heavy help from Claude, from first-hand observation: the app's
on-disk state, run logs and bundled source, cross-checked against the official
docs. No Anthropic source code is reproduced here.

## License

MIT - see [LICENSE](LICENSE).
