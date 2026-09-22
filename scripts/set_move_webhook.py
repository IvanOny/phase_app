"""Re-register Move's webhook so Telegram also sends reaction updates.

A bot receives `message_reaction` updates only if its webhook explicitly asks
for them in `allowed_updates` -- and once you pass that list you must name
every type you want, since the default set is replaced, not extended. So this
reads the current webhook URL back from Telegram and re-sets it with the full
list: messages, edits, button taps, reactions.

One-time. Needs MOVE_BOT_TOKEN in the environment; never prints it.

    "C:/Users/nebel/AppData/Local/Programs/Python/Python313/python.exe" scripts/set_move_webhook.py
"""
import json
import os
import sys
import urllib.request

ALLOWED = ["message", "edited_message", "callback_query", "message_reaction"]


def call(token: str, method: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload or {}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}", data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    token = os.environ.get("MOVE_BOT_TOKEN")
    if not token:
        print("MOVE_BOT_TOKEN is not set.", file=sys.stderr)
        return 2
    info = call(token, "getWebhookInfo").get("result") or {}
    url = info.get("url")
    if not url:
        print("No webhook URL is registered; set one first.", file=sys.stderr)
        return 1
    print(f"webhook: {url}")
    print(f"allowed_updates now: {info.get('allowed_updates') or '(default)'}")
    res = call(token, "setWebhook", {"url": url, "allowed_updates": ALLOWED,
                                      "drop_pending_updates": False})
    if not res.get("ok"):
        print(f"setWebhook failed: {res}", file=sys.stderr)
        return 1
    after = call(token, "getWebhookInfo").get("result") or {}
    print(f"allowed_updates after: {after.get('allowed_updates')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
