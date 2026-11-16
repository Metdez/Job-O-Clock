#!/usr/bin/env python3
"""Send the NEU VC + Founder invite from Gmail (zack@solid.tech), N per day (default 33) at random times.

Default is a DRY RUN: nothing is sent. Use --go to really send. See directives/send_outreach.md.

  python execution/send_outreach.py                 # dry run: shows today's plan + writes .tmp/preview.html
  python execution/send_outreach.py --test-to a@b.c # sends ONE real test email (needs Gmail creds)
  python execution/send_outreach.py --go            # sends today's batch (sleeping between sends)

Safe to re-run: today's count and already-sent addresses come from send_log.csv.
Stops on the first API error. Honors do_not_email.csv.
"""
import argparse, base64, csv, json, os, random, re, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

D = "data/northeastern-event-contacts"
QUEUE, LOG, DNC = f"{D}/send_queue.csv", f"{D}/send_log.csv", f"{D}/do_not_email.csv"
FLYER = "assets/fireside-chats-flyer.png"
TPL = "templates/neu_vc_founder"
TZ = ZoneInfo("America/New_York")
SENDER_NAME = "Zack Hanna"
LOG_FIELDS = ["sent_at", "email", "name", "position", "message_id"]


def load_env(path=".env"):
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def read_csv(p):
    return list(csv.DictReader(open(p, encoding="utf-8-sig"))) if os.path.exists(p) else []


def build_message(to_addr, sender):
    subject = open(f"{TPL}.subject").read().strip()
    m = MIMEMultipart("related")
    m["To"], m["From"], m["Subject"] = to_addr, f"{SENDER_NAME} <{sender}>", subject
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(open(f"{TPL}.txt").read(), "plain", "utf-8"))
    alt.attach(MIMEText(open(f"{TPL}.html").read(), "html", "utf-8"))
    m.attach(alt)
    img = MIMEImage(open(FLYER, "rb").read(), _subtype="png")
    img.add_header("Content-ID", "<flyer>")
    img.add_header("Content-Disposition", "inline", filename="fireside-chats-flyer.png")
    m.attach(img)
    return m


def access_token():
    data = urllib.parse.urlencode({
        "client_id": os.environ["GMAIL_CLIENT_ID"], "client_secret": os.environ["GMAIL_CLIENT_SECRET"],
        "refresh_token": os.environ["GMAIL_REFRESH_TOKEN"], "grant_type": "refresh_token"}).encode()
    with urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", data=data), timeout=30) as r:
        return json.load(r)["access_token"]


def gmail_send(msg, token):
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    req = urllib.request.Request(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        data=json.dumps({"raw": raw}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["id"]


def plan_times(n, now, start_h, end_h, min_gap):
    """n random send times between max(now, start) and end, at least min_gap sec apart."""
    start = max(now + timedelta(seconds=5), now.replace(hour=start_h, minute=0, second=0, microsecond=0))
    end = now.replace(hour=end_h, minute=0, second=0, microsecond=0)
    span = (end - start).total_seconds()
    if n <= 0 or span <= 0:
        return []
    n = min(n, int(span // min_gap) + 1)
    slack = span - (n - 1) * min_gap
    offs = sorted(random.uniform(0, slack) for _ in range(n))
    return [start + timedelta(seconds=o + i * min_gap) for i, o in enumerate(offs)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--go", action="store_true", help="actually send (default is dry run)")
    ap.add_argument("--test-to", help="send ONE real test email to this address and exit")
    ap.add_argument("--per-day", type=int, default=33)
    ap.add_argument("--window", default="9-18", help="send window, ET hours, e.g. 9-18")
    ap.add_argument("--min-gap", type=int, default=240, help="min seconds between sends")
    a = ap.parse_args()
    load_env()
    sender = os.environ.get("GMAIL_SENDER", "zack@solid.tech")
    start_h, end_h = map(int, a.window.split("-"))

    if a.test_to:
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", a.test_to):
            sys.exit("bad --test-to address")
        mid = gmail_send(build_message(a.test_to, sender), access_token())
        print("test sent", mid)
        return

    queue = read_csv(QUEUE)
    if not queue:
        sys.exit(f"{QUEUE} missing: run python execution/build_send_queue.py")
    log = read_csv(LOG)
    sent = {r["email"].lower() for r in log}
    dnc = {r["email"].strip().lower() for r in read_csv(DNC)}
    now = datetime.now(TZ)
    today = now.strftime("%Y-%m-%d")
    sent_today = sum(1 for r in log if r["sent_at"].startswith(today))
    todo = [r for r in queue if r["email"].lower() not in sent and r["email"].lower() not in dnc]
    batch = todo[: max(0, a.per_day - sent_today)]
    times = plan_times(len(batch), now, start_h, end_h, a.min_gap)
    batch = batch[: len(times)]
    print(f"[{'GO' if a.go else 'DRY RUN'}] {now:%a %b %d %H:%M %Z} | queue {len(queue)} | sent {len(sent)} | "
          f"remaining {len(todo)} | sent today {sent_today} | planned now {len(batch)}")
    for r, t in zip(batch, times):
        print(f"  {t:%H:%M:%S}  #{r['position']:>3}  {r['name']} <{r['email']}>  [{r['organizations'][:40]}]")
    os.makedirs(".tmp", exist_ok=True)
    open(".tmp/preview.html", "w").write(open(f"{TPL}.html").read().replace("cid:flyer", "../" + FLYER))
    if not a.go:
        print("Nothing sent. Preview: .tmp/preview.html. Re-run with --go to send.")
        return
    if not batch:
        print("Nothing to send right now (daily cap reached, window closed, or queue finished).")
        return

    token, token_at = access_token(), time.time()
    new_file = not os.path.exists(LOG)
    with open(LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if new_file:
            w.writeheader()
        for r, t in zip(batch, times):
            wait = (t - datetime.now(TZ)).total_seconds()
            if wait > 0:
                time.sleep(wait)
            if time.time() - token_at > 2700:
                token, token_at = access_token(), time.time()
            try:
                mid = gmail_send(build_message(r["email"], sender), token)
            except urllib.error.HTTPError as e:
                sys.exit(f"STOPPED at #{r['position']} {r['email']}: HTTP {e.code} {e.read().decode()[:300]}")
            w.writerow({"sent_at": datetime.now(TZ).isoformat(timespec="seconds"), "email": r["email"],
                        "name": r["name"], "position": r["position"], "message_id": mid})
            f.flush()
            print(f"sent #{r['position']} {r['email']} {mid}", flush=True)
    print("batch complete")


if __name__ == "__main__":
    main()
