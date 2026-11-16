# Hourly outreach tick (Gmail connector, zack@solid.tech)

A scheduled task wakes the Claude session every hour, 9:17-17:17 ET, and this runs. Replaces the API-script path
(`send_outreach.py` stays as an optional fallback). Cap: 35/day, counted from `data/northeastern-event-contacts/send_log.csv`.

## Each tick
1. `cd /home/user/Job-O-Clock && git pull -q origin claude/tender-clarke-14zweq` (skip if it errors; the local files are fine).
2. `python3 execution/outreach_tick.py next` -> JSON. If `send` is empty, stop quietly.
3. For each recipient in `send`, in order, call `mcp__Gmail__send_message` (load its schema with ToolSearch if needed):
   `to=[email]`, `subject`, `body`, `htmlBody` and `attachments=[attachment]` EXACTLY as given in the JSON (no edits).
   Right after each success: `python3 execution/outreach_tick.py record EMAIL MESSAGE_ID`.
   Between sends wait a random 60-420 s: `python3 -c "import random,time;time.sleep(random.randint(60,420))"` (run in background, continue when it finishes).
4. If ANY send fails: stop, record nothing for it, tell the user what failed. Never retry in a loop.
5. `git add data && git commit -m "outreach log" && git push origin claude/tender-clarke-14zweq` (retry push up to 4x).
6. Reply with one line: sent N this hour, X today, Y remaining.

## Rules
- Only addresses from `next`. Never send to anyone else, never send more than `next` returns.
- If a reply says "remove"/"unsubscribe", add the address to `do_not_email.csv` (needs `email,reason`).
- Turn it on/off: enable/disable the scheduled task (`update_trigger enabled`). Disabled = nothing sends.
