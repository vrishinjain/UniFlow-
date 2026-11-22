# Demo seed data

`seed.sql` **deletes all data** in every UniFlow table and replaces it with the demo
dataset (61 users, 4 courses, 13 projects, 6 CS682 teams with boards and team chats).
It runs in one transaction: if any statement fails, nothing changes.

Every demo account shares one password, which is shared with the team separately;
it is not written in this repo.

## Running it on a Neon branch

Order on **every** branch:

1. `db/migrations/chatdev.sql` (creates the chat tables; once per branch)
2. `scripts/seed/seed.sql`

If step 1 is skipped, `seed.sql` stops at its first line and changes nothing.

Run each file in the Neon SQL Editor with the **branch dropdown set to the right
branch**, or with `psql "<branch connection string>" -f <file>`.

Always make a Neon backup branch of production before seeding it.

## Changing the data

Edit `seed_content.py` (people, courses, projects, tickets, chat messages), then
rebuild `seed.sql` from this folder:

```bash
pip install reportlab        # only needed for regenerating; the app doesn't use it
python generate_seed.py '<bcrypt hash of the demo password>' > seed.sql
```

Keep the single quotes; the hash contains `$` signs. To make a new hash:

```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'NEW_PASSWORD', bcrypt.gensalt(12)).decode())"
```

The output is deterministic: the same content and hash always produce the same
`seed.sql`. Commit `seed_content.py`, `generate_seed.py` and the regenerated
`seed.sql` together.
