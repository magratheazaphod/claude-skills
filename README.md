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

## Provenance

Written with heavy help from Claude, from first-hand observation: the app's
on-disk state, run logs and bundled source, cross-checked against the official
docs. No Anthropic source code is reproduced here.

## License

MIT - see [LICENSE](LICENSE).
