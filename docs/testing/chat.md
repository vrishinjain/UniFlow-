# Team chat — test plan

Run everything against the `chat-dev` Neon branch, never production.

## Setup

1. `db/migrations/chatdev.sql` has been run on `chat-dev` (Neon SQL Editor, branch dropdown = `chat-dev`).
2. Local `.env` points `REFLEX_DB_URL` at `chat-dev`, loaded with `set -a; source .env; set +a`.
3. Checks that need no database:
   ```bash
   python scripts/test_chat.py
   python scripts/test_workspace_static.py
   ```

## Manual checks (two browsers, e.g. one normal + one incognito)

| # | Steps | Expected |
|---|---|---|
| 1 | Sign in as an assigned student, open the project workspace | "Team chat" card below "Project team", above milestones; "No messages yet"; Live indicator |
| 2 | Type a message, press Enter | Message appears with "(you)", Student badge and time; box clears |
| 3 | Shift+Enter in the box | New line, not sent |
| 4 | Second browser: teammate on the same project | First message visible; new messages from either side appear within ~3 s |
| 5 | Course faculty opens the same workspace | Same chat; Faculty badge; trash icon on every message |
| 6 | Student hovers a teammate's message | No trash icon |
| 7 | Student deletes own message → Delete | Shows "Message deleted" in both browsers within ~3 s |
| 8 | Send `<b>hi</b>` | Shown literally as text, not bold |
| 9 | Paste 2,001+ characters | Counter turns red, Send disabled |
| 10 | Send 21 messages within a minute | 21st shows "sending messages too quickly" |
| 11 | Hide chat → Show chat | Collapses to header; reloads on Show |
| 12 | Student from another project opens this workspace URL | Access denied page (no chat) |
| 13 | Sign out, sign in as a different user in same tab | No messages from the previous session visible |
| 14 | Leave a tab idle 15+ minutes | "Live updates paused…" with Resume; Resume reloads |
| 15 | 60+ messages in chat | "Load older messages" at top loads the rest |

## Database spot checks (SQL Editor on `chat-dev`)

```sql
SELECT scope, project, count(*) FROM chat_channel GROUP BY 1, 2;      -- one row per opened project
SELECT id, sender, deleted_at IS NOT NULL AS deleted FROM chat_message ORDER BY id DESC LIMIT 10;
```
