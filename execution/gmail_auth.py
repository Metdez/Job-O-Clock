#!/usr/bin/env python3
"""ONE-TIME: get a Gmail refresh token for zack@solid.tech. Run this on YOUR computer (needs a browser).

Setup (about 5 min): Google Cloud Console -> new project -> enable "Gmail API" -> OAuth consent screen
(User type "Internal" if solid.tech is Google Workspace; refresh tokens then don't expire) -> Credentials ->
Create "OAuth client ID" -> Application type "Desktop app". Copy the client ID and secret.

  GMAIL_CLIENT_ID=... GMAIL_CLIENT_SECRET=... python execution/gmail_auth.py

Sign in as zack@solid.tech, approve "send email". It prints three lines to paste into .env.
Scope is gmail.send only (can send, cannot read your mail).
"""
import http.server, json, os, secrets, sys, threading, urllib.parse, urllib.request, webbrowser

cid, csec = os.environ.get("GMAIL_CLIENT_ID"), os.environ.get("GMAIL_CLIENT_SECRET")
if not (cid and csec):
    sys.exit("Set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET first (see docstring).")
state, got = secrets.token_urlsafe(16), {}

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if q.get("state") == [state] and "code" in q:
            got["code"] = q["code"][0]
        self.send_response(200); self.end_headers()
        self.wfile.write(b"Done. You can close this tab.")
    def log_message(self, *a): pass

srv = http.server.HTTPServer(("127.0.0.1", 0), H)
redirect = f"http://127.0.0.1:{srv.server_port}"
url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
    "client_id": cid, "redirect_uri": redirect, "response_type": "code", "state": state,
    "scope": "https://www.googleapis.com/auth/gmail.send", "access_type": "offline", "prompt": "consent",
    "login_hint": "zack@solid.tech"})
print("Opening browser...\n", url)
webbrowser.open(url)
t = threading.Thread(target=srv.handle_request); t.start(); t.join(300)
if "code" not in got:
    sys.exit("No authorization received.")
data = urllib.parse.urlencode({"code": got["code"], "client_id": cid, "client_secret": csec,
                               "redirect_uri": redirect, "grant_type": "authorization_code"}).encode()
tok = json.load(urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", data=data)))
if "refresh_token" not in tok:
    sys.exit("No refresh_token returned; revoke the app at myaccount.google.com/permissions and retry.")
print("\nPaste into .env:\nGMAIL_CLIENT_ID=%s\nGMAIL_CLIENT_SECRET=%s\nGMAIL_REFRESH_TOKEN=%s" % (cid, csec, tok["refresh_token"]))
