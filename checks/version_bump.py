"""Fail when a plugin's files changed but its version did not.

Installed plugins are cached by version, so a change shipped without a bump
may never reach people who already installed it. This script only demands
*a* bump; choosing patch, minor or major is a human call.

Usage:
  python3 -I checks/version_bump.py --staged        # pre-commit: index vs HEAD
  python3 -I checks/version_bump.py BASE HEAD       # CI: a commit range
"""

import json
import subprocess
import sys

MANIFEST = ".claude-plugin/plugin.json"


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def version_at(ref, plugin):
    # ref "" means the index (staged content).
    try:
        text = git("show", f"{ref}:plugins/{plugin}/{MANIFEST}")
    except subprocess.CalledProcessError:
        return None  # the plugin is new, or was removed
    return json.loads(text).get("version")


def main():
    if sys.argv[1:] == ["--staged"]:
        if subprocess.run(["git", "rev-parse", "--verify", "-q", "HEAD"], capture_output=True).returncode:
            return 0  # first commit: nothing to compare against
        old, new = "HEAD", ""
        changed = git("diff", "--cached", "--name-only", "HEAD").split()
    elif len(sys.argv) == 3:
        old, new = sys.argv[1], sys.argv[2]
        changed = git("diff", "--name-only", old, new).split()
    else:
        print(__doc__)
        return 2

    plugins = sorted({p.split("/")[1] for p in changed if p.startswith("plugins/") and p.count("/") >= 2})
    stale = []
    for plugin in plugins:
        before, after = version_at(old, plugin), version_at(new, plugin)
        if before is not None and after is not None and before == after:
            stale.append((plugin, before))

    if not stale:
        return 0
    for plugin, version in stale:
        print(f"plugins/{plugin} changed but its version is still {version}.")
    print(
        f"\nBump \"version\" in plugins/<name>/{MANIFEST} so installed copies update:\n"
        "  patch (0.2.0 -> 0.2.1): typo or wording fixes, no change in what it claims\n"
        "  minor (0.2.0 -> 0.3.0): new or corrected claims, new sections, re-verification\n"
        "  major (0.2.0 -> 1.0.0): renamed or removed skills, a changed install path\n"
        "To skip on purpose (e.g. a commit that only moves files), use git commit --no-verify."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
