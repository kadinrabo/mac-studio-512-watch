#!/usr/bin/env python3
"""One long GitHub Actions run that watches two things, then hands over to the next run.

- Mac Studio: Apple's store every 5 min until MAC_END_DATE, for the 512GB M5 Ultra option.
- LG 65" G6 OLED: Best Buy's price every 30 min until TV_END_DATE; alerts on every new low.

State (whether the Mac alert went out, the lowest TV price seen) lives in STATE_FILE, which the
workflow carries between runs with the Actions cache. Summaries go out at 8/11/14/17/20/23 New York time.

Exit codes: 0 = keep going (workflow starts the next run), 10 = everything has ended (stop).
"""
import datetime
import json
import os
import sys
import time
from zoneinfo import ZoneInfo

import tv
from watch import URL as APPLE_URL, check as mac_check, notify

ET = ZoneInfo("America/New_York")
SLOTS = [8, 11, 14, 17, 20, 23]
INTERVAL = int(os.environ.get("INTERVAL_S", "300"))
TV_EVERY = int(os.environ.get("TV_EVERY", "6"))          # TV check every 6th loop = 30 min
RUN_MINUTES = int(os.environ.get("RUN_MINUTES", "345"))
MAC_END = datetime.date.fromisoformat(os.environ.get("MAC_END_DATE", "2026-11-02"))
TV_END = datetime.date.fromisoformat(os.environ.get("TV_END_DATE", "2026-11-30"))
TV_START_LOW = float(os.environ.get("TV_START_LOW", "2499.99"))   # price when tracking started
STATE_FILE = os.environ.get("STATE_FILE", "state/state.json")


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE) or ".", exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def money(x):
    return f"${x:,.2f}"


def main():
    state = load_state()
    state.setdefault("mac_found", False)
    state.setdefault("tv_low", TV_START_LOW)
    save_state(state)
    start = time.monotonic()
    period_start = datetime.datetime.now(ET)
    mac = {"checks": 0, "ok": 0, "failed": 0}
    tvs = {"checks": 0, "failed": 0, "last": None, "regular": None}
    alerted = {}
    sent_slots = set()
    i = 0

    def alert_once_per(key, seconds, title, msg, prio):
        if time.monotonic() - alerted.get(key, -1e9) > seconds:
            notify(title, msg, prio)
            alerted[key] = time.monotonic()

    if os.environ.get("ANNOUNCE") == "true":
        notify("Watcher is running", f"Mac Studio 512GB every {INTERVAL // 60} min until {MAC_END:%b %-d}; "
               f"{tv.NAME} at Best Buy every {INTERVAL * TV_EVERY // 60} min until {TV_END:%b %-d} "
               f"(alerts below {money(state['tv_low'])}). Summaries 8 AM–11 PM ET every 3 h.", "low")

    while time.monotonic() - start < RUN_MINUTES * 60:
        now = datetime.datetime.now(ET)
        mac_on = not state["mac_found"] and now.date() <= MAC_END
        tv_on = now.date() <= TV_END
        if not mac_on and not tv_on:
            print("Nothing left to watch; stopping.")
            save_state(state)
            return 10

        if mac_on:
            try:
                st, msg = mac_check()
            except Exception as e:
                st, msg = "error", f"fetch failed: {e}"
            mac["checks"] += 1
            print(f"{now:%m-%d %H:%M} ET  mac {st}: {msg}", flush=True)
            if st == "available":
                notify("512GB Mac Studio is orderable", msg + " Tap to open the Apple Store.", "urgent")
                state["mac_found"] = True
                save_state(state)
            elif st == "coming":
                mac["ok"] += 1
            else:
                mac["failed"] += 1
                if st == "unknown":
                    alert_once_per("mac_page", 3600, "Mac Studio page changed", msg, "high")

        if tv_on and i % TV_EVERY == 0:
            tvs["checks"] += 1
            try:
                cur, reg = tv.price()
                tvs["last"], tvs["regular"] = cur, reg
                print(f"{now:%m-%d %H:%M} ET  tv {money(cur)} (regular {money(reg) if reg else '?'})", flush=True)
                if cur < state["tv_low"] - 0.005:
                    off = f", {money(reg - cur)} off {money(reg)}" if reg else ""
                    notify(f"{tv.NAME} dropped to {money(cur)}",
                           f"New low at Best Buy: {money(cur)} (was {money(state['tv_low'])}{off}). Tap to open Best Buy.", "high", click=tv.PRODUCT)
                    state["tv_low"] = cur
                    save_state(state)
            except Exception as e:
                tvs["failed"] += 1
                print(f"{now:%m-%d %H:%M} ET  tv check failed: {e}", flush=True)
                if tvs["failed"] >= 3:
                    alert_once_per("tv_fail", 6 * 3600, "Best Buy check failing",
                                   f"Couldn't read the {tv.NAME} price the last few tries ({e}).", "default")

        slot = (now.date(), now.hour)
        if now.hour in SLOTS and now.minute < 15 and slot not in sent_slots:
            sent_slots.add(slot)
            if now - period_start > datetime.timedelta(minutes=30):
                since = period_start.strftime("%-I:%M %p").replace(":00", "")
                parts = []
                if state["mac_found"]:
                    parts.append("Mac: 512GB alert already sent.")
                elif now.date() <= MAC_END:
                    parts.append(f"Mac: {mac['checks']} checks, {mac['ok']} OK" +
                                 (", 512GB not orderable yet." if not mac["failed"] else f", {mac['failed']} failed."))
                if tv_on:
                    p = f"{money(tvs['last'])}" if tvs["last"] else "no price read"
                    parts.append(f"TV: {p} (lowest {money(state['tv_low'])}), {tvs['checks']} checks" +
                                 (f", {tvs['failed']} failed." if tvs["failed"] else "."))
                notify("Watcher: still checking", f"Since {since} ET. " + " ".join(parts),
                       "low" if not (mac["failed"] or tvs["failed"]) else "default")
            period_start = now
            mac = {"checks": 0, "ok": 0, "failed": 0}
            tvs.update(checks=0, failed=0)

        i += 1
        time.sleep(INTERVAL)

    save_state(state)
    print("Run time used up; handing over to the next run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
