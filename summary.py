#!/usr/bin/env python3
"""Send a "still checking" summary of the watcher's recent runs via ntfy.

Runs hourly from summary.yml; only sends at 8, 11, 14, 17, 20 and 23 o'clock New York time,
so nothing arrives between 11 PM and 8 AM. Each summary covers the runs since the previous slot.

Env: GITHUB_TOKEN, GITHUB_REPOSITORY, NTFY_TOPIC, END_DATE (YYYY-MM-DD). Flags: --force (send now), --dry-run (print only).
"""
import datetime
import json
import os
import sys
import urllib.request
from zoneinfo import ZoneInfo

from watch import notify

ET = ZoneInfo("America/New_York")
SLOTS = [8, 11, 14, 17, 20, 23]
REPO = os.environ.get("GITHUB_REPOSITORY", "kadinrabo/mac-studio-512-watch")


def gh(path):
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/{path}",
                                 headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
                                          "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def previous_slot(now):
    """Start of the period this summary covers: the slot before the current one."""
    i = SLOTS.index(now.hour)
    if i == 0:  # the 8 AM summary covers the night since 11 PM
        return (now - datetime.timedelta(days=1)).replace(hour=SLOTS[-1], minute=0, second=0, microsecond=0)
    return now.replace(hour=SLOTS[i - 1], minute=0, second=0, microsecond=0)


def main():
    force, dry = "--force" in sys.argv, "--dry-run" in sys.argv
    now = datetime.datetime.now(ET)
    if datetime.date.today() > datetime.date.fromisoformat(os.environ.get("END_DATE", "2026-11-02")):
        print("Past end date; no summary.")
        return 0
    if not force and now.hour not in SLOTS:
        print(f"{now:%H:%M} ET isn't a summary slot.")
        return 0
    if gh("actions/workflows/watch.yml")["state"] != "active":
        print("Watcher is off (512GB alert already sent, or disabled by hand); no summary.")
        return 0
    since = previous_slot(now.replace(minute=0)) if now.hour in SLOTS else now - datetime.timedelta(hours=3)
    since_utc = since.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    runs, page = [], 1
    while True:
        batch = gh(f"actions/workflows/watch.yml/runs?created=>={since_utc}&per_page=100&page={page}")["workflow_runs"]
        runs += batch
        if len(batch) < 100:
            break
        page += 1
    checks = [r for r in runs if r["event"] == "schedule" and r["status"] == "completed"]
    failed = [r for r in checks if r["conclusion"] != "success"]
    hours = (now - since).total_seconds() / 3600
    period = f"since {since:%-I %p}".replace(" 0", " ")
    if not checks:
        title, msg, prio = "Mac Studio watcher: no checks ran", f"No checks completed {period} ET. GitHub may have paused the schedule; open the repo's Actions tab.", "high"
    else:
        last = max(datetime.datetime.fromisoformat(r["updated_at"].replace("Z", "+00:00")) for r in checks).astimezone(ET)
        ok = len(checks) - len(failed)
        status = "512GB still not orderable." if not failed else f"{len(failed)} check(s) failed (network or page change); the rest found 512GB still not orderable."
        title, prio = "Mac Studio watcher: still checking", "low" if not failed else "default"
        msg = f"{len(checks)} checks {period} ET ({ok} OK, about one every {hours * 60 / len(checks):.0f} min). {status} Last check {last:%-I:%M %p} ET."
    if dry:
        print(f"[dry run] {title}: {msg} (priority {prio})")
    else:
        notify(title, msg, prio)
    return 0


if __name__ == "__main__":
    sys.exit(main())
