"""Check that a clean Claude Code reaches for the skill without being told to.

Installs this checkout's plugins into a config that has nothing else (no
personal skills, CLAUDE.md or memory), asks questions a stranger might ask, and
checks each one loads the expected skill. Grading the answers stays manual.

Needs a logged-in config. Once per Mac:
  CLAUDE_CONFIG_DIR=~/.claude-skills-trigger claude auth login

Usage:
  python3 -I checks/trigger_test.py          # exit 1 if any question missed
  python3 -I checks/trigger_test.py --issue  # also open/refresh a GitHub issue
"""

import argparse
import importlib
import json
import os
import subprocess
import sys
import tempfile

# -I leaves the script's folder off sys.path, and drift.py lives beside it.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
drift = importlib.import_module("drift")

REPO = os.path.dirname(drift.HERE)
CONFIG = os.path.expanduser("~/.claude-skills-trigger")
MARKET = "magratheazaphod-skills"

# (expected skill, question). Most avoid the product name on purpose: a
# description that only fires on "Cowork" misses how people actually ask.
CASES = [
    ("cowork:claude-cowork",
     "I have a Claude Cowork scheduled task on my Mac. I edited its prompt file but runs still use the old instructions. Why? Answer briefly."),
    ("cowork:claude-cowork",
     "My scheduled Claude task keeps using its old instructions even though I edited the instructions file. Why? Answer briefly."),
    ("cowork:claude-cowork",
     "I set up a recurring task in the Claude desktop app that keeps running while my laptop is closed. Can it push to my GitHub repo? Answer briefly."),
]


def claude(*args, **kw):
    env = dict(os.environ, CLAUDE_CONFIG_DIR=CONFIG)
    return subprocess.run(["claude", *args], env=env, capture_output=True, text=True, **kw)


def install_from_checkout():
    claude("plugin", "marketplace", "remove", MARKET)
    r = claude("plugin", "marketplace", "add", REPO)
    if r.returncode:
        raise RuntimeError(f"marketplace add failed: {r.stdout}{r.stderr}")
    with open(os.path.join(REPO, ".claude-plugin", "marketplace.json")) as f:
        for p in json.load(f)["plugins"]:
            r = claude("plugin", "install", f"{p['name']}@{MARKET}")
            if r.returncode:
                raise RuntimeError(f"install {p['name']} failed: {r.stdout}{r.stderr}")


def skills_loaded(question):
    # An empty working folder, so nothing from this repo leaks into the answer.
    with tempfile.TemporaryDirectory() as cwd:
        r = claude("-p", question, "--output-format", "stream-json", "--verbose",
                   "--max-turns", "3", "--allowedTools", "Skill", cwd=cwd, timeout=600)
    loaded = []
    for line in r.stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "result" and "Not logged in" in str(event.get("result")):
            raise RuntimeError(f"{CONFIG} is not logged in; see this script's docstring")
        if event.get("type") == "assistant":
            loaded += [c["input"].get("skill") for c in event["message"]["content"]
                       if c.get("type") == "tool_use" and c.get("name") == "Skill"]
    return loaded


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--issue", action="store_true")
    args = ap.parse_args()
    try:
        install_from_checkout()
        findings = []
        for expected, question in CASES:
            loaded = skills_loaded(question)
            ok = expected in loaded
            print(f"{'ok  ' if ok else 'MISS'} {expected} <- {question[:70]}")
            if not ok:
                findings.append(f"Skill {expected} not loaded for: \"{question}\" (loaded: {loaded or 'none'})")
    except Exception as e:
        findings = [f"Trigger test itself failed: {type(e).__name__}: {e}"]
    if not findings:
        print(f"All {len(CASES)} questions loaded their skill.")
        return 0
    drift.report(findings, drift.app_version(), args.issue, "Skill trigger test failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
