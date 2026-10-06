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
import glob
import hashlib
import json
import os
import plistlib
import re
import subprocess
import sys
import tempfile
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
APP = "/Applications/Claude.app"
ISSUE_TITLE = "Cowork drift detected - re-verify the skills"


def app_version():
    with open(f"{APP}/Contents/Info.plist", "rb") as f:
        return plistlib.load(f)["CFBundleShortVersionString"]


def bundle_sources(workdir):
    # The app ships its main-process JS inside app.asar; extract once per run.
    subprocess.run(
        ["npx", "-y", "@electron/asar", "extract",
         f"{APP}/Contents/Resources/app.asar", workdir],
        check=True, capture_output=True,
    )
    text = []
    for path in glob.glob(os.path.join(workdir, ".vite", "build", "**", "*.js"), recursive=True):
        with open(path, errors="ignore") as f:
            text.append(f.read())
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

    with tempfile.TemporaryDirectory() as tmp:
        src = bundle_sources(tmp)
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

    version, doc_hashes, findings = run_checks(cfg, baseline)

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
    print("\n".join(findings))
    if args.issue:
        open_issue(findings, version)
    return 1


if __name__ == "__main__":
    sys.exit(main())
