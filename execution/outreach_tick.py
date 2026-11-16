#!/usr/bin/env python3
"""Helper for the hourly scheduled outreach (sends go through the Gmail connector, not the API).

  next    -> JSON: who to send RIGHT NOW (this hour's share of today's 30). Sends/records nothing.
  record EMAIL MESSAGE_ID  -> append to send_log.csv (call once per email actually sent)
  status  -> counts

Schedule: fires hourly 9:00-17:59 ET (9 fires). Each fire sends remaining_today / fires_left (+/-1 jitter);
the last fire of the day sends whatever is left. Cap 30/day, counted from send_log.csv (so reruns are safe).
"""
import csv, hashlib, json, os, random, sys
from datetime import datetime
from zoneinfo import ZoneInfo

D = "data/northeastern-event-contacts"
QUEUE, LOG, DNC = f"{D}/send_queue.csv", f"{D}/send_log.csv", f"{D}/do_not_email.csv"
FLYER = os.path.abspath("assets/fireside-chats-flyer.png")
TPL = "templates/neu_vc_founder"
TZ = ZoneInfo("America/New_York")
PER_DAY, FIRST_H, LAST_H = 30, 9, 17
FIELDS = ["sent_at", "email", "name", "position", "message_id"]

def rd(p): return list(csv.DictReader(open(p, encoding="utf-8-sig"))) if os.path.exists(p) else []

def state():
    now = datetime.now(TZ)
    log = rd(LOG)
    sent = {r["email"].lower() for r in log}
    dnc = {r["email"].strip().lower() for r in rd(DNC)}
    today = sum(1 for r in log if r["sent_at"].startswith(now.strftime("%Y-%m-%d")))
    todo = [r for r in rd(QUEUE) if r["email"].lower() not in sent and r["email"].lower() not in dnc]
    return now, today, todo, len(sent)

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
    elif cmd == "record":
        email, mid = sys.argv[2].lower(), sys.argv[3]
        row = next((r for r in rd(QUEUE) if r["email"].lower() == email), None)
        if not row: sys.exit("email not in queue")
        new = not os.path.exists(LOG)
        with open(LOG, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            if new: w.writeheader()
            w.writerow({"sent_at": now.isoformat(timespec="seconds"), "email": email, "name": row["name"], "position": row["position"], "message_id": mid})
        print("recorded", email)
    else:
        sys.exit("usage: next | record EMAIL ID | status")

if __name__ == "__main__":
    main()
