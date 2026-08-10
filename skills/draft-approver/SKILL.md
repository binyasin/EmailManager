---
name: "draft-approver"
description: "WhatsApp draft approval: say \"approve\" or \"send\" to auto-send a Gmail draft via SMTP. Adds draft listing and send commands to the email workflow."
homepage: https://clawhub.ai/skills/draft-approver
---

# Draft Approver — WhatsApp Approval for Email Drafts

Lets the user approve and send Gmail drafts directly from WhatsApp with simple voice or text commands like "approve", "send it", or "send the draft".

## How It Works

1. Email manager creates a draft in Gmail (via IMAP APPEND to `[Gmail]/Drafts`)
2. User gets notified about the draft
3. User replies on WhatsApp: "approve", "send", "yes send it", etc.
4. Agent uses the `draft-send` script to read the draft from Gmail and send it via SMTP
5. The draft is removed from Drafts folder after sending

## Intent Matching

When a user on WhatsApp says any of these after being shown a draft:

| User says | Action |
|---|---|
| "approve" / "send it" / "yes" / "send" | Send the most recent draft, or the draft currently in context |
| "send the draft to Azam" | If multiple drafts, sends the one matching "Azam" |
| "send draft [subject]" | Sends the draft matching the subject |
| "show drafts" / "what drafts" | Lists current drafts in Gmail |
| "delete draft [subject]" | Deletes a draft without sending |

## Script: `draft-send.py`

Located at `<SKILL_DIR>/scripts/draft-send.py`

### Commands

```bash
python "<SKILL_DIR>/scripts/draft-send.py" list
```

Lists all drafts in Gmail's `[Gmail]/Drafts` folder. Output is JSON:

```json
{
  "drafts": [
    {
      "uid": "123",
      "to": "Azam Azizi",
      "subject": "Re: hi",
      "date": "2026-08-05T10:05:00+05:00",
      "body_preview": "Salam Azam! Just a heads up..."
    }
  ]
}
```

```bash
python "<SKILL_DIR>/scripts/draft-send.py" send --uid 123
```

Sends the draft with the given IMAP UID via SMTP, then deletes it from the Drafts folder.

```bash
python "<SKILL_DIR>/scripts/draft-send.py" send --to "Azam"
```

Sends the most recent draft matching the recipient name.

```bash
python "<SKILL_DIR>/scripts/draft-send.py" send --latest
```

Sends the most recent draft regardless of recipient.

```bash
python "<SKILL_DIR>/scripts/draft-send.py" delete --uid 123
```

Deletes a draft without sending.

## Email Credentials

The script reads credentials from the smart-email skill's SQLite database:
- Path: `<workspace>/skills/smart-email/data/email.db`
- Table: `accounts`
- Uses the same App Password stored there

No separate credential setup needed — it piggybacks on the existing smart-email configuration.

## Gmail SMTP Settings (hardcoded in script)

- Server: `smtp.gmail.com`
- Port: `587`
- Uses STARTTLS

## Agent Integration

When the draft-approver skill is loaded and the user says an approval phrase:

1. If there's a specific draft in context (just shown to user), send it directly
2. If ambiguous, run `list` to show available drafts, then ask which one
3. After sending, confirm with: "✅ Draft sent to [recipient]: [subject]"
4. If sending fails, report the error clearly

## Error Handling

- If no drafts exist: tell the user "No drafts to send"
- If SMTP fails: report the error (likely auth or network)
- If the draft was already sent/deleted: tell the user it's no longer in Drafts
- If multiple drafts match: list them and ask the user to pick

## Privacy

- Script reads credentials from the local encrypted store only
- No credentials are logged or transmitted outside the local machine
- Temp script is deleted after use if it contains credentials inline
