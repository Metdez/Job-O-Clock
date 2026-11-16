#!/usr/bin/env python3
"""Helper for the hourly scheduled outreach (sends go through the Gmail connector, not the API).

  next    -> JSON: who to send RIGHT NOW (this hour's share of today's 35). Sends/records nothing.
  record EMAIL MESSAGE_ID  -> append to send_log.csv (call once per email actually sent)
  status  -> counts

Schedule: fires hourly 9:00-17:59 ET (9 fires). Each fire sends remaining_today / fires_left (+/-1 jitter);
the last fire of the day sends whatever is left. Cap 35/day, counted from send_log.csv (so reruns are safe).
"""
import csv, hashlib, json, os, random, sys
from datetime import datetime
from zoneinfo import ZoneInfo

D = "data/northeastern-event-contacts"
QUEUE, LOG, DNC = f"{D}/send_queue.csv", f"{D}/send_log.csv", f"{D}/do_not_email.csv"
FLYER = os.path.abspath("assets/fireside-chats-flyer.png")
TPL = "templates/neu_vc_founder"
TZ = ZoneInfo("America/New_York")
PER_DAY, FIRST_H, LAST_H = 35, 9, 17
FIELDS = ["sent_at", "email", "name", "position", "message_id", "kind"]  # kind: queue | extra (extras do not count toward the daily cap)

def rd(p): return list(csv.DictReader(open(p, encoding="utf-8-sig"))) if os.path.exists(p) else []

def state():
    now = datetime.now(TZ)
    log = rd(LOG)
    sent = {r["email"].lower() for r in log}
    dnc = {r["email"].strip().lower() for r in rd(DNC)}
    today = sum(1 for r in log if r["sent_at"].startswith(now.strftime("%Y-%m-%d")) and r.get("kind", "queue") != "extra")
    todo = [r for r in rd(QUEUE) if r["email"].lower() not in sent and r["email"].lower() not in dnc]
    return now, today, todo, len(sent)

def write_ledger():
    """Regenerate the human-readable ledger: send_ledger.csv (every queue row + status) and LEDGER.md (summary)."""
    log = rd(LOG)
    by = {r["email"].lower(): r for r in log if r.get("kind", "queue") != "extra"}
    dnc = {r["email"].strip().lower() for r in rd(DNC)}
    q = rd(QUEUE)
    with open(f"{D}/send_ledger.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["position", "name", "email", "organizations", "tier", "status", "sent_at", "message_id"])
        for r in q:
            e = r["email"].lower(); l = by.get(e)
            status = "SENT" if l else ("SKIPPED (do not email)" if e in dnc else "PENDING")
            w.writerow([r["position"], r["name"], r["email"], r["organizations"], r["tier"], status,
                        l["sent_at"] if l else "", l["message_id"] if l else ""])
    days = {}
    for r in log:
        if r.get("kind", "queue") != "extra":
            days[r["sent_at"][:10]] = days.get(r["sent_at"][:10], 0) + 1
    extras = [r for r in log if r.get("kind") == "extra"]
    sent, total = len(by), len(q)
    md = [f"# Outreach ledger (NEU VC + Founder)", "",
          f"Updated {datetime.now(TZ):%Y-%m-%d %H:%M %Z}. Sender: zack@solid.tech. Cap: {PER_DAY}/day.", "",
          f"- Queue: **{total}**  |  Sent: **{sent}**  |  Pending: **{total - sent - sum(1 for r in q if r['email'].lower() in dnc and r['email'].lower() not in by)}**  |  Do-not-email: **{sum(1 for r in q if r['email'].lower() in dnc and r['email'].lower() not in by)}**", "",
          "## Sent per day (queue only)", "", "| Date | Sent |", "|---|---|"] + [f"| {d} | {n} |" for d, n in sorted(days.items())]
    md += ["", "## Extra sends (not counted toward the cap)", "", "| Sent at | To |", "|---|---|"] + [f"| {r['sent_at']} | {r['email']} |" for r in extras]
    md += ["", "Full per-person status: `send_ledger.csv` (SENT / PENDING / SKIPPED). Raw send events: `send_log.csv`."]
    open(f"{D}/LEDGER.md", "w").write("\n".join(md) + "\n")

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    now, today, todo, nsent = state()
    if cmd == "status":
        print(json.dumps({"now_et": now.isoformat(timespec="minutes"), "sent_total": nsent, "sent_today": today, "remaining": len(todo)}))
    elif cmd == "next":
        h = now.hour
        remaining_today = PER_DAY - today
        if not (FIRST_H <= h <= LAST_H) or remaining_today <= 0 or not todo:
            print(json.dumps({"send": [], "reason": "outside window, daily cap reached, or queue finished", "sent_today": today, "remaining": len(todo)})); return
        fires_left = LAST_H - h + 1
        n = remaining_today if fires_left == 1 else max(0, min(remaining_today, round(remaining_today / fires_left) + random.choice([-1, 0, 0, 1])))
        n = max(n, 1) if fires_left <= 2 else n
        batch = todo[:n]
        html = open(f"{TPL}.html").read().replace("cid:flyer", "cid:att0")
        sha = hashlib.sha256(open(FLYER, "rb").read()).hexdigest()
        print(json.dumps({
            "send": [{"email": r["email"], "name": r["name"], "position": r["position"]} for r in batch],
            "subject": open(f"{TPL}.subject").read().strip(),
            "body": open(f"{TPL}.txt").read(), "htmlBody": html,
            "attachment": {"content": f"sha256:{sha}:{FLYER}", "filename": "fireside-chats-flyer.png", "mimeType": "image/png", "inline": True},
            "sent_today": today, "remaining_after": len(todo) - len(batch)}))
    elif cmd == "payload":
        html = open(f"{TPL}.html").read().replace("cid:flyer", "cid:att0")
        sha = hashlib.sha256(open(FLYER, "rb").read()).hexdigest()
        print(json.dumps({"subject": open(f"{TPL}.subject").read().strip(), "body": open(f"{TPL}.txt").read(), "htmlBody": html,
            "attachment": {"content": f"sha256:{sha}:{FLYER}", "filename": "fireside-chats-flyer.png", "mimeType": "image/png", "inline": True}}))
    elif cmd in ("record", "record-extra"):
        email, mid = sys.argv[2].lower(), sys.argv[3]
        kind = "extra" if cmd == "record-extra" else "queue"
        row = next((r for r in rd(QUEUE) if r["email"].lower() == email), None)
        if kind == "queue" and not row: sys.exit("email not in queue")
        row = row or {"name": "(extra, not in queue)", "position": ""}
        new = not os.path.exists(LOG)
        with open(LOG, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            if new: w.writeheader()
            w.writerow({"sent_at": now.isoformat(timespec="seconds"), "email": email, "name": row["name"], "position": row["position"], "message_id": mid, "kind": kind})
        print("recorded", kind, email)
        write_ledger()
    elif cmd == "ledger":
        write_ledger(); print("ledger written")
    else:
        sys.exit("usage: next | payload | record EMAIL ID | record-extra EMAIL ID | ledger | status")

if __name__ == "__main__":
    main()
