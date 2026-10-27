# Mac Studio 512GB watcher

Checks https://www.apple.com/shop/buy-mac/mac-studio every 15 minutes until 2026-11-02 and sends a phone
notification (via the free [ntfy](https://ntfy.sh) app) when the 512GB M5 Ultra memory option becomes orderable.
Uses no AI at all.

- Notifications: install ntfy on your phone, subscribe to the topic stored in the `NTFY_TOPIC` repo secret.
- It switches itself off after the first "orderable" alert. To stop earlier: Actions → this workflow → Disable.
- If Apple's page changes so the check can't read it, the run fails and GitHub emails you.
