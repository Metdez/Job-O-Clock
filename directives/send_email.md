# Send Email via Power Automate

Flow: "Analyze emails sentiment with AI Builder and send results to Teams"
Trigger: HTTP request ("manual"), who can trigger: Anyone. Action: Outlook "Send an email (V2)"
(sender connection is the flow owner's Outlook account).

## Config
- `POWER_AUTOMATE_EMAIL_URL` in `.env` (URL includes a `sig=` secret; never commit or log it).

## Request body JSON schema (all required)
```json
{
  "type": "object",
  "properties": {
    "to": {"type": "string"},
    "subject": {"type": "string"},
    "body": {"type": "string"}
  },
  "required": ["to", "subject", "body"]
}
```
Mapping: To <- `to`, Subject <- `subject`, Body (HTML editor) <- `body`.

## Run
`python execution/send_email.py --to a@b.com --subject "Hi" --body "Hello"`
A 200/202 response means the flow was accepted, not that the email was delivered; check the flow run history.
