# Mac Studio 512GB + LG G6 price watcher

Checks https://www.apple.com/shop/buy-mac/mac-studio every 5 minutes (one long Actions run that restarts itself every ~6 hours) until 2026-11-02 and sends a phone
notification (via the free [ntfy](https://ntfy.sh) app) when the 512GB M5 Ultra memory option becomes orderable.
Uses no AI at all.

- Notifications: install ntfy on your phone and subscribe to the topic set in `.github/workflows/watch.yml` (or override it with an `NTFY_TOPIC` repo secret).
- A "still checking" summary arrives at 8 AM, 11 AM, 2 PM, 5 PM, 8 PM and 11 PM New York time (nothing overnight). It warns you if no checks ran.
- It switches itself off after the first "orderable" alert. To stop earlier: Actions → this workflow → Disable.
- If Apple's page changes so the check can't read it, you get a push at most once an hour and the run fails so GitHub emails you.
- Every 5 minutes for a week is ~2,000 Actions minutes: the whole free monthly allowance for private repos on GitHub Free (3,000 on Pro). Set the cron back to */15 if that matters.

- Also tracks Best Buy's price for the LG 65" G6 OLED (OLED65G6WUA, SKU 6673119) every 30 minutes until Nov 30 and pushes on every new low (started at $2,499.99, regular $3,399.99). The lowest price seen is kept between runs with the Actions cache.
