# Send NEU VC + Founder invite (30/day, random times)

Sends `templates/neu_vc_founder.*` (subject "NEU VC + Founder", inline flyer `assets/fireside-chats-flyer.png`)
from **zack@solid.tech** via the Gmail API to `data/northeastern-event-contacts/send_queue.csv`.

## Status: configured, NOT started. Nothing is sent until `--go`.

## Files
- `execution/build_send_queue.py` builds the ordered queue (588 people). Order: shortlist orgs + confident email (234),
  shortlist + name-match-only email (191), everyone else (163). Random within tier, seeded. Re-run only with `--rebuild`.
- `execution/send_outreach.py` dry run by default. `--go` sends today's batch; `--test-to addr` sends one real test.
- `execution/gmail_auth.py` one-time OAuth helper (run on a computer with a browser).
- `data/.../send_log.csv` created on first send; the source of truth for who was sent / how many today. Commit it after each run.
- `data/.../do_not_email.csv` add an `email` row for anyone who replies "remove". Honored by the sender.

## Settings (defaults)
30/day, 9am-6pm America/New_York, random times, at least 4 min apart. Override: `--per-day`, `--window 9-18`, `--min-gap`.
Re-running the same day only sends the remainder of the 30. Stops immediately on any Gmail API error.

## Before "go" (one-time)
1. Create Google OAuth Desktop credentials and run `gmail_auth.py` (see its docstring). Paste the 3 lines into `.env`:
   `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`. (`.env` is gitignored.)
2. `python execution/send_outreach.py --test-to zh@licom.ai` and confirm it arrives with the image.
3. `python execution/send_outreach.py` (dry run) and review the plan + `.tmp/preview.html`.

## Go
Run `python execution/send_outreach.py --go` once per day (a long-running process; it sleeps between sends).
It needs a machine that stays on for ~9 hours/day for ~20 days (cron on a server, or a daily scheduled task).
Days needed: 588 / 30 = 20. Starting Nov 17 the last send is ~Dec 6, after the Dec 3 event; the shortlist
tiers (425 people) finish ~Dec 1. Raise `--per-day` to finish sooner.

## Notes / risks
- All 588 addresses are @northeastern.edu. 209 of them are name-match-only (provisional), so some may be the wrong person.
- Template includes a one-line opt-out ("reply remove"). Keep honoring `do_not_email.csv`.
- Gmail limits: ~500/day for normal accounts, so 30/day is well inside it. Bounces are not auto-detected; check the inbox for them.
- Google OAuth apps in "Testing" mode with an external user type expire refresh tokens in 7 days. Use "Internal" if solid.tech is Workspace.
