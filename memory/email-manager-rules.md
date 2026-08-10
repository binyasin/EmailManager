# Email Manager Workflow & Rules

## Core Functionality
- **Incoming Mail Processing:** Check unread/incoming emails, read content, and extract/analyze attachments (PDFs, images, documents).
- **Daily Reporting:** Generate a summarized report of all processed emails, key insights, urgency, and actions taken.
- **Drafting Responses:** By default, compose responses and save them to the **Drafts** folder so the user can review and send them the next day.

## Sending Modes & User Preferences
- **Draft Mode (Default):** All responses are created as drafts for manual review and sending.
- **Direct Send Mode:** Specific senders, email categories, or user instructions can bypass draft mode and send responses directly to the recipient immediately.
- **Configurable Rules:** Allow the user (binyasin) to instruct Email Manager on which emails/senders to auto-send versus keep in drafts.

## Reply Channel (chat, not Gmail drafts)
When the user *asks about* email in chat (e.g. "check my email", "any new emails?", "read that one"), the reply to the user must match how they asked, same as any other conversation: voice question → voice note reply (TTS), text question → text reply. See `TOOLS.md` for the TTS steps. Don't let the smart-email skill's text-bullet-list formatting example override this — it's silent on voice, not an exception to it.
