"""Check whether the Cowork skills have drifted from the installed Claude Desktop.

Runs on a Mac with Claude Desktop installed; it cannot run in CI, because the
thing under test is the app on this machine. Three checks:

1. Version: has the app moved off the version recorded in baseline.json?
2. Anchors: does every string in anchors.json still appear in the app bundle?
3. Docs: has the text of any official article changed since the baseline?

Usage:
  python3 -I checks/drift.py              # report; exit 1 if anything drifted
  python3 -I checks/drift.py --issue      # also open/refresh a GitHub issue
  python3 -I checks/drift.py --rebaseline # after re-verifying the skills
"""

import argparse
import hashlib
import json
import os
import plistlib
import re
import subprocess
import struct
import sys
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
APP = "/Applications/Claude.app"
ISSUE_TITLE = "Cowork drift detected - re-verify the skills"
# Outside the repo: it records this Mac's runs, not the skills' state.
STATE = os.path.expanduser("~/Library/Logs/claude-skills-drift.state.json")
STALE_AFTER = timedelta(days=8)


def app_version():
    with open(f"{APP}/Contents/Info.plist", "rb") as f:
        return plistlib.load(f)["CFBundleShortVersionString"]


def bundle_sources():
    """Concatenate the main-process JS under .vite/build/ inside app.asar.

    Reads the asar archive directly (stdlib only) so the check has no Node
    dependency: launchd runs it without the interactive shell that puts nvm's
    npx on PATH. Format: four little-endian uint32s (pickle header), where the
    second is the header buffer size and the fourth the JSON length; the JSON
    index follows at byte 16, and file data starts at 8 + header buffer size.
    """
    path = f"{APP}/Contents/Resources/app.asar"
    with open(path, "rb") as f:
        _, header_size, _, json_len = struct.unpack("<4I", f.read(16))
        index = json.loads(f.read(json_len))
        base = 8 + header_size
        build = index["files"][".vite"]["files"]["build"]
        text = []

        def walk(node):
            for name, entry in node.get("files", {}).items():
                if "files" in entry:
                    walk(entry)
                elif name.endswith(".js") and not entry.get("unpacked"):
                    f.seek(base + int(entry["offset"]))
                    text.append(f.read(entry["size"]).decode("utf-8", errors="ignore"))

        walk(build)
    return "\n".join(text)


def doc_hash(url):
    # curl rather than urllib: python.org builds on macOS ship without a CA
    # bundle, while curl uses the system trust store.
    body = subprocess.run(
        ["curl", "-fsSL", "--max-time", "30", "-A", "claude-skills-drift-check", url],
        capture_output=True, text=True, check=True,
    ).stdout
    # Normalize whitespace so cosmetic reflows don't count as drift.
    return hashlib.sha256(" ".join(body.split()).encode()).hexdigest()


def run_checks(cfg, baseline):
    findings = []
    version = app_version()
    if version != baseline.get("app_version"):
        old_major = baseline.get("app_version", "0").split(".")[0]
        kind = "MAJOR" if version.split(".")[0] != old_major else "minor"
        findings.append(f"App version changed ({kind}): {baseline.get('app_version')} -> {version}")

    src = bundle_sources()
    for a in cfg["anchors"]:
        if not re.search(a["regex"], src):
            findings.append(f"Anchor missing: {a['id']} -> re-verify {a['skill']} section '{a['section']}'")

    doc_hashes = {}
    for url in cfg["docs"]:
        try:
            doc_hashes[url] = doc_hash(url)
        except Exception as e:  # a fetch failure is reported, not treated as drift
            findings.append(f"Could not fetch {url}: {e}")
            continue
        if baseline.get("docs", {}).get(url) not in (None, doc_hashes[url]):
            findings.append(f"Official doc changed: {url}")
    return version, doc_hashes, findings


def notify(msg):
    # Last resort when GitHub can't be reached: a failure must reach a human
    # somehow, or a broken week looks like a quiet one.
    script = f"display notification {json.dumps(msg[:200])} with title \"claude-skills drift check\""
    subprocess.run(["osascript", "-e", script], check=False)


def last_completed():
    try:
        with open(STATE) as f:
            return datetime.fromisoformat(json.load(f)["last_completed"])
    except (OSError, KeyError, ValueError):
        return None


def mark_completed():
    with open(STATE, "w") as f:
        json.dump({"last_completed": datetime.now().isoformat(timespec="seconds")}, f)


def report(findings, version, issue):
    print("\n".join(findings))
    if not issue:
        return
    try:
        open_issue(findings, version)
    except Exception as e:
        print(f"Could not open a GitHub issue: {type(e).__name__}: {e}")
        notify(f"{len(findings)} finding(s), and the GitHub issue failed. See ~/Library/Logs/claude-skills-drift.log")


def open_issue(findings, version):
    body = (f"Drift check on {date.today()} against Claude Desktop {version}:\n\n"
            + "\n".join(f"- {f}" for f in findings)
            + "\n\nRe-verify the named sections, update the skills, then run "
              "`python3 -I checks/drift.py --rebaseline`.")
    existing = subprocess.run(
        ["gh", "issue", "list", "--state", "open", "--search", ISSUE_TITLE, "--json", "number"],
        cwd=HERE, capture_output=True, text=True, check=True,
    )
    numbers = [i["number"] for i in json.loads(existing.stdout)]
    if numbers:
        subprocess.run(["gh", "issue", "comment", str(numbers[0]), "--body", body], cwd=HERE, check=True)
    else:
        subprocess.run(["gh", "issue", "create", "--title", ISSUE_TITLE, "--body", body], cwd=HERE, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--issue", action="store_true")
    ap.add_argument("--rebaseline", action="store_true")
    args = ap.parse_args()

    with open(os.path.join(HERE, "anchors.json")) as f:
        cfg = json.load(f)
    baseline_path = os.path.join(HERE, "baseline.json")
    baseline = {}
    if os.path.exists(baseline_path):
        with open(baseline_path) as f:
            baseline = json.load(f)

    stale = []
    last = last_completed()
    if last and datetime.now() - last > STALE_AFTER:
        stale = [f"No completed drift check since {last:%Y-%m-%d}; earlier scheduled runs failed or never ran"]

    try:
        version, doc_hashes, findings = run_checks(cfg, baseline)
    except Exception as e:
        # A check that crashes must not look like a quiet week.
        report(stale + [f"Drift check itself failed: {type(e).__name__}: {e}"], "unknown", args.issue)
        return 2
    findings = stale + findings
    if not any(f.startswith("Could not fetch") for f in findings):
        mark_completed()

    if args.rebaseline:
        missing = [f for f in findings if f.startswith(("Anchor missing", "Could not fetch"))]
        if missing:
            print("Refusing to rebaseline while anchors are missing or docs unreachable:")
            print("\n".join(missing))
            return 1
        with open(baseline_path, "w") as f:
            json.dump({"app_version": version, "verified_on": str(date.today()), "docs": doc_hashes},
                      f, indent=2)
            f.write("\n")
        print(f"Baseline written for Claude Desktop {version}.")
        return 0

    if not findings:
        print(f"No drift: Claude Desktop {version}, all anchors present, docs unchanged.")
        return 0
    report(findings, version, args.issue)
    return 1


if __name__ == "__main__":
    sys.exit(main())
