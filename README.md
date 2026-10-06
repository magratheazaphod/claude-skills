# claude-skills

Agent skills by Jesse Day, written from months of daily use.

| Skill | What it covers |
|---|---|
| [`claude-cowork`](skills/claude-cowork/SKILL.md) | How Claude Cowork actually works on macOS beyond the help center: where tasks live on disk, local tasks vs routines, what a session can reach, how the scheduler decides to run, the editing traps, and a log of what changed from July to October 2026 |
| [`cowork-in-production`](skills/cowork-in-production/SKILL.md) | Patterns for running unattended products on Cowork: prompts in git behind a stub, file handoff to local apps, pre-flight checks, model tiering, browser hygiene, debugging routines |

Cowork changes fast. Each skill says which app version and date it was checked
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
