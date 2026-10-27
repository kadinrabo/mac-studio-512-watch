#!/usr/bin/env python3
"""Check Apple's store every few minutes for one long GitHub Actions run, then hand over to the next run.

GitHub's cron scheduler is best-effort, so instead of relying on it, each run loops for ~5h45m and the
workflow starts a fresh run at the end. Also sends the "still checking" summaries at 8/11/14/17/20/23 New York time.

Exit codes: 0 = keep going (workflow starts the next run), 2 = 512GB found (stop), 10 = past the end date (stop).
Env: NTFY_TOPIC, END_DATE (YYYY-MM-DD), INTERVAL_S (default 300), RUN_MINUTES (default 345), ANNOUNCE ("true" sends a start push).
"""
import datetime
import os
import sys
import time
from zoneinfo import ZoneInfo

from watch import URL, check, notify

ET = ZoneInfo("America/New_York")
SLOTS = [8, 11, 14, 17, 20, 23]
INTERVAL = int(os.environ.get("INTERVAL_S", "300"))
RUN_MINUTES = int(os.environ.get("RUN_MINUTES", "345"))
END = datetime.date.fromisoformat(os.environ.get("END_DATE", "2026-11-02"))


def main():
    start = time.monotonic()
    started_et = datetime.datetime.now(ET)
    period_start = started_et
    checks = ok = failed = 0
    last_ok = None
    last_change_alert = 0.0
    sent_slots = set()
    if os.environ.get("ANNOUNCE") == "true":
        notify("Mac Studio watcher is running", f"Checking Apple's store every {INTERVAL // 60} min until {END:%b %-d}. "
               "Summaries at 8 AM, 11 AM, 2 PM, 5 PM, 8 PM and 11 PM ET.", "low")
    while time.monotonic() - start < RUN_MINUTES * 60:
        now = datetime.datetime.now(ET)
        if now.date() > END:
            print(f"Past end date {END}; stopping.")
            return 10
        try:
            state, msg = check()
        except Exception as e:
            state, msg = "error", f"fetch failed: {e}"
        checks += 1
        print(f"{now:%Y-%m-%d %H:%M} ET  {state}: {msg}", flush=True)
        if state == "available":
            notify("512GB Mac Studio is orderable", msg + " Tap to open the Apple Store.", "urgent")
            return 2
        if state == "coming":
            ok += 1
            last_ok = now
        else:
            failed += 1
            if state == "unknown" and time.monotonic() - last_change_alert > 3600:
                notify("Mac Studio page changed", msg, "high")
                last_change_alert = time.monotonic()
        # summary at each slot, once
        slot = (now.date(), now.hour)
        if now.hour in SLOTS and now.minute < 15 and slot not in sent_slots:
            sent_slots.add(slot)
            if checks > 1 or now - period_start > datetime.timedelta(minutes=30):
                since = period_start.strftime("%-I:%M %p").replace(":00", "")
                status = "512GB still not orderable." if not failed else f"{failed} check(s) failed (network or page change)."
                last = f" Last good check {last_ok:%-I:%M %p} ET." if last_ok else ""
                notify("Mac Studio watcher: still checking",
                       f"{checks} checks since {since} ET, {ok} OK. {status}{last}", "low" if not failed else "default")
            period_start, checks, ok, failed = now, 0, 0, 0
        time.sleep(INTERVAL)
    print("Run time used up; handing over to the next run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
