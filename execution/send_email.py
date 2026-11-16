#!/usr/bin/env python3
"""Send an email through the Power Automate HTTP-trigger flow. See directives/send_email.md."""
import argparse, json, os, sys, urllib.request, urllib.error

def load_env(path=".env"):
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k, v)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--to", required=True)
    p.add_argument("--subject", required=True)
    p.add_argument("--body", required=True)
    a = p.parse_args()
    load_env()
    url = os.environ.get("POWER_AUTOMATE_EMAIL_URL")
    if not url:
        sys.exit("POWER_AUTOMATE_EMAIL_URL not set in .env")
    req = urllib.request.Request(
        url,
        data=json.dumps({"to": a.to, "subject": a.subject, "body": a.body}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            print("HTTP", r.status, r.read().decode()[:500])
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:500]}")

if __name__ == "__main__":
    main()
