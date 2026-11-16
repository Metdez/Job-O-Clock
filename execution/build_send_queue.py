#!/usr/bin/env python3
"""Build data/northeastern-event-contacts/send_queue.csv (ordered recipient list).

Order: (1) shortlist-org + confident email, (2) shortlist-org + name-match-only email,
(3) everyone else (confident first). Random order within each tier (seeded, reproducible).
Skips malformed emails and anything in do_not_email.csv. Safe to re-run: keeps order if queue exists unless --rebuild.
"""
import csv, os, random, re, sys
D = "data/northeastern-event-contacts"
C = f"{D}/csv"
Q = f"{D}/send_queue.csv"
SEED = 20261116
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def rows(p): return list(csv.DictReader(open(p, encoding="utf-8-sig")))

def main():
    if os.path.exists(Q) and "--rebuild" not in sys.argv:
        sys.exit(f"{Q} exists (use --rebuild to regenerate; sent history lives in send_log.csv, not here).")
    shortlist = {r["name"] for r in rows(f"{C}/04_speaker_shortlist.csv")}
    dnc = set()
    if os.path.exists(f"{D}/do_not_email.csv"):
        dnc = {r["email"].strip().lower() for r in rows(f"{D}/do_not_email.csv")}
    people, seen = [], set()
    for r in rows(f"{C}/02_distinct_emails.csv"):
        e = r["email"].strip().lower()
        if not EMAIL_RE.match(e) or e in seen or e in dnc:
            continue
        seen.add(e)
        orgs = [o.strip() for o in r["organizations"].split("|")]
        fit = any(o in shortlist for o in orgs)
        provisional = r["email_status"].strip().startswith("Northeastern directory (name match)")
        tier = (0 if fit else 2) + (1 if provisional else 0) if fit else (2 if not provisional else 3)
        people.append({"tier": tier, "name": r["name"], "email": e, "organizations": r["organizations"],
                       "email_status": r["email_status"]})
    random.Random(SEED).shuffle(people)
    people.sort(key=lambda p: p["tier"])
    with open(Q, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["position", "tier", "name", "email", "organizations", "email_status"])
        w.writeheader()
        for i, p in enumerate(people, 1):
            w.writerow({"position": i, **p})
    from collections import Counter
    print(f"wrote {Q}: {len(people)} recipients; tiers {sorted(Counter(p['tier'] for p in people).items())}")

if __name__ == "__main__":
    main()
