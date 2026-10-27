#!/usr/bin/env python3
"""Check Apple's Mac Studio store page for the 512GB M5 Ultra memory option.

No AI involved: it fetches the page, reads the memory options Apple's configurator
lists, and sends a push notification through ntfy.sh when 512GB appears.

Exit codes: 0 = still coming (or past the end date), 2 = 512GB is orderable, 3 = page changed / fetch failed.
Env: NTFY_TOPIC (optional; notifications go to https://ntfy.sh/<topic>), END_DATE (YYYY-MM-DD, default 2026-11-02).
"""
import datetime
import os
import re
import sys
import urllib.request

URL = "https://www.apple.com/shop/buy-mac/mac-studio"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15"


def notify(title, message, priority="default"):
    topic = os.environ.get("NTFY_TOPIC")
    print(f"{title}: {message}")
    if not topic:
        return
    req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=message.encode(), method="POST",
                                 headers={"Title": title, "Priority": priority, "Click": URL, "Tags": "computer"})
    urllib.request.urlopen(req, timeout=20).read()


def check():
    req = urllib.request.Request(URL, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    block = re.search(r'"memory-dimensionMemory":\{.{0,600}?"variantOrder":\[([^\]]*)\]', page)
    coming_note = re.search(r"512GB memory option[^\"<]{0,80}", page)
    if not block:
        return "unknown", "Couldn't find the memory options on Apple's page; the page layout may have changed."
    options = re.findall(r'"([0-9]+gb)"', block.group(1))
    if "512gb" in options:
        return "available", f"512GB is now an orderable memory option ({', '.join(options)})."
    if not coming_note:
        return "unknown", f"The 'coming late October' note is gone but 512GB isn't listed yet ({', '.join(options)}). Worth a look."
    return "coming", f"Not yet: memory options {', '.join(options)}; note says '{coming_note.group(0).strip()}'."


def main():
    end = datetime.date.fromisoformat(os.environ.get("END_DATE", "2026-11-02"))
    if datetime.date.today() > end:
        print(f"Past end date {end}; not checking.")
        return 0
    try:
        state, msg = check()
    except Exception as e:  # network hiccup or Apple blocking a request
        print(f"fetch failed: {e}")
        return 3
    if state == "available":
        notify("512GB Mac Studio is orderable", msg + " Tap to open the Apple Store.", "urgent")
        return 2
    if state == "unknown":
        notify("Mac Studio page changed", msg, "high")
        return 3
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
