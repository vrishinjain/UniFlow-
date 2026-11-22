"""Generate seed.sql: a complete, realistic replacement dataset for UniFlow.

Usage:  python generate_seed.py <bcrypt-hash-of-demo-password> > seed.sql

The output wipes every UniFlow table (TRUNCATE ... RESTART IDENTITY) and inserts the
dataset described in seed_content.py inside one transaction. Output is deterministic.
"""

import io
import random
import sys
from datetime import datetime, timedelta

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

import seed_content as C

rng = random.Random(682)
PASSWORD_HASH = sys.argv[1]
out: list[str] = []


def q(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, bytes):
        return "'\\x" + value.hex() + "'::bytea"
    return "'" + str(value).replace("'", "''") + "'"


def ts(value: str | datetime) -> str:
    """Boston local time with the correct UTC offset (DST ends 2026-11-01)."""
    dt = datetime.fromisoformat(value) if isinstance(value, str) else value
    offset = "-04" if dt < datetime(2026, 11, 1, 2) else "-05"
    return f"'{dt.strftime('%Y-%m-%d %H:%M:%S')}{offset}'"


def insert(table: str, cols: list[str], rows: list[list[str]]) -> None:
    out.append(f"INSERT INTO public.{table} ({', '.join(cols)}) VALUES")
    out.append(",\n".join("  (" + ", ".join(r) + ")" for r in rows) + ";\n")


def email_for(name: str) -> str:
    first, last = name.lower().split(" ", 1)
    last = "".join(ch for ch in last if ch.isalpha())
    return f"{first}.{last}@{C.UNI}"


def brief_pdf(project: dict, org: str, contact: str, contact_email: str, filename: str) -> bytes:
    styles = getSampleStyleSheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, title=project["title"], author=org,
                            leftMargin=60, rightMargin=60, topMargin=60, bottomMargin=60)
    body = styles["BodyText"]
    story = []
    if "data_dictionary" in filename:
        story += [Paragraph("Harbor Buoy Data Dictionary", styles["Title"]),
                  Paragraph(org, styles["Heading3"])]
        for var, desc in [("timestamp_utc", "ISO 8601 time of the reading, UTC."),
                          ("buoy_id", "B1 through B6; see the deployment map for locations."),
                          ("water_temp_c", "Water temperature at 1 m depth, degrees Celsius."),
                          ("salinity_psu", "Practical salinity units."),
                          ("do_mg_l", "Dissolved oxygen, mg/L."),
                          ("turbidity_ntu", "Turbidity, nephelometric turbidity units."),
                          ("battery_v", "Buoy battery voltage; below 11.8 V readings are unreliable.")]:
            story.append(Paragraph(f"<b>{var}</b>: {desc}", body))
    elif "historical_bookings" in filename:
        story += [Paragraph("Historical Dock Bookings (sample)", styles["Title"]),
                  Paragraph("Excerpt of 3 months of bookings. Full CSV is shared with the team on request.", body),
                  Spacer(1, 8)]
        r = random.Random(41)
        carriers = ["Bay State Haulers", "Pike Freight", "Atlantic LTL", "Granite Express", "Seacoast Carriers"]
        for i in range(18):
            d = datetime(2026, 6, 2) + timedelta(days=i // 3, hours=6 + 2 * (i % 3) + r.randint(0, 1))
            story.append(Paragraph(
                f"{d:%Y-%m-%d %H:%M} &nbsp; Door {r.randint(1, 40):02d} &nbsp; {r.choice(carriers)} &nbsp; "
                f"{r.randint(6, 26)} pallets &nbsp; waited {r.choice([0, 5, 15, 35, 60, 95])} min", body))
    elif "room_layout" in filename:
        story += [Paragraph("Branch Study Rooms", styles["Title"])]
        for branch, rooms in [("Main Branch", 6), ("Eastside Branch", 4), ("Hillcrest Branch", 2)]:
            story.append(Paragraph(branch, styles["Heading3"]))
            for n in range(1, rooms + 1):
                cap = [2, 4, 4, 6, 8, 12][(n - 1) % 6]
                story.append(Paragraph(f"Room {n}: seats {cap}" + (", display screen" if cap >= 6 else ""), body))
    else:
        story += [Paragraph(project["title"], styles["Title"]),
                  Paragraph(f"Project proposal from {org}", styles["Heading3"]),
                  Paragraph(f"Contact: {contact} ({contact_email})", body), Spacer(1, 10),
                  Paragraph("Background and problem", styles["Heading2"])]
        story += [Paragraph(p, body) for p in project["description"].split("\n\n")]
        story += [Paragraph("Goals for the semester", styles["Heading2"]),
                  ListFlowable([ListItem(Paragraph(g, body)) for g in project["goals"]], bulletType="bullet"),
                  Paragraph("Technology and data", styles["Heading2"]), Paragraph(project["tech"], body),
                  Paragraph("Sponsor commitment", styles["Heading2"]),
                  Paragraph("A sponsor representative will meet the team every two weeks, review each sprint "
                            "demo, and answer questions on the team's chat channel within two business days.", body)]
    doc.build(story)
    data = buf.getvalue()
    # Make output byte-for-byte reproducible.
    import re
    data = re.sub(rb"/(CreationDate|ModDate) \(D:[^)]*\)", rb"/\1 (D:20260815000000+00'00')", data)
    data = re.sub(rb"/ID\s*\n?\[<[0-9a-f]+><[0-9a-f]+>\]", b"/ID [<00><00>]", data)
    return data


# ---------------------------------------------------------------- users
users = []  # (id, name, email, role, status, created, must_change)
uid = {}
def add_user(key, name, email, role, status, created, must_change=False):
    users.append((len(users) + 1, name, email, role, status, created, must_change))
    uid[key] = len(users)

add_user("admin", *C.ADMIN, "system_admin", "active", "2026-08-03 09:00")
for i, (key, name, email, status) in enumerate(C.FACULTY):
    add_user(key, name, email, "faculty", status, f"2026-08-0{4 + i} 10:{15 + i * 7:02d}" if status == "active"
             else "2026-11-16 13:42")
for i, (key, (name, email, _org, status)) in enumerate(C.SPONSORS.items()):
    created = "2026-11-17 18:05" if status == "pending" else f"2026-08-{10 + i:02d} {9 + i % 8:02d}:{(i * 13) % 60:02d}"
    add_user(key, name, email, "sponsor", status, created)

students = []
for i, name in enumerate(C.STUDENT_NAMES):
    key = f"s{i}"
    if i < 45:
        # Accounts bulk-imported by faculty in late August; two have never logged in yet.
        add_user(key, name, email_for(name), "student", "active",
                 f"2026-08-{26 + i % 5:02d} {10 + i % 7:02d}:{(i * 7) % 60:02d}", must_change=i in (38, 39))
        students.append(uid[key])
    elif i < 47:
        add_user(key, name, email_for(name), "student", "pending", f"2026-11-1{5 + i - 45} 20:{i:02d}")
    else:
        add_user(key, name, email_for(name), "student", "rejected", "2026-09-09 22:31")

insert("users", ["id", "full_name", "email", "password_hash", "role", "status", "created_at", "must_change_password"],
       [[q(i), q(n), q(e), q(PASSWORD_HASH), q(r), q(s), ts(c), q(m)] for i, n, e, r, s, c, m in users])

# ---------------------------------------------------------------- courses & enrollments
insert("courses", ["id", "name", "code", "term", "faculty_id", "created_at", "preferences_open"],
       [[q(i + 1), q(name), q(code), q(term), q(uid[fac]), ts(created), q(open_)]
        for i, (code, name, term, fac, open_, created) in enumerate(C.COURSES)])

roster = {1: students[0:24], 2: students[24:40], 3: students[37:45], 4: []}
enroll_rows = []
for course, ids in roster.items():
    base = datetime(2026, 9, 2, 9, 0) if course != 3 else datetime(2026, 9, 3, 13, 0)
    for k, s in enumerate(ids):
        enroll_rows.append([q(course), q(s), ts(base + timedelta(minutes=k))])
insert("course_enrollments", ["course_id", "student_id", "enrolled_at"], enroll_rows)

# ---------------------------------------------------------------- projects, files, reviews, visibility
pid = {p["key"]: i + 1 for i, p in enumerate(C.PROJECTS)}
insert("projects", ["id", "sponsor_id", "title", "description", "status", "created_at"],
       [[q(pid[p["key"]]), q(uid[p["sponsor"]]), q(p["title"]), q(p["description"]), q(p["status"]), ts(p["submitted"])]
        for p in C.PROJECTS])

file_rows = []
for p in C.PROJECTS:
    name, email, org, _ = C.SPONSORS[p["sponsor"]]
    for fn in p["files"]:
        data = brief_pdf(p, org, name, email, fn)
        assert data.startswith(b"%PDF-1.4\n") and len(data) < 10 * 1024 * 1024
        file_rows.append([q(len(file_rows) + 1), q(pid[p["key"]]), q(fn), q("application/pdf"), q(len(data)), q(data),
                          ts(p["submitted"])])
insert("project_files", ["id", "project_id", "filename", "content_type", "size_bytes", "data", "uploaded_at"], file_rows)

ACTION = {"request_revision": "revision_requested", "reject": "rejected", "resubmitted": "resubmitted"}
review_rows = []
for p in C.PROJECTS:
    for action, actor, when, notes in p.get("history", []):
        actor_id = uid[p["sponsor"]] if action == "resubmitted" else uid[actor]
        review_rows.append((when, [q(pid[p["key"]]), q(actor_id), q(ACTION[action]), q(notes), ts(when)]))
    if p["key"] in C.ACCEPTED_BY:
        fac, when = C.ACCEPTED_BY[p["key"]]
        review_rows.append((when, [q(pid[p["key"]]), q(uid[fac]), q("accepted"), "NULL", ts(when)]))
review_rows.sort(key=lambda r: r[0])
insert("project_reviews", ["project_id", "actor_id", "action", "notes", "created_at"], [r for _, r in review_rows])

vis_rows, visible = [], {}
for course_idx, items in C.VISIBILITY.items():
    for key, fac, when in items:
        visible.setdefault(course_idx + 1, []).append(pid[key])
        vis_rows.append([q(pid[key]), q(course_idx + 1), q(uid[fac]), ts(when)])
insert("project_course_visibility", ["project_id", "course_id", "shared_by", "shared_at"], vis_rows)

# ---------------------------------------------------------------- preferences & assignments
CAPACITY = 4
pref_rows, prefs = [], {}
def rank_projects(options, weights):
    pool, w, picked = list(options), list(weights), []
    for _ in range(3):
        choice = rng.choices(pool, weights=w)[0]
        i = pool.index(choice); pool.pop(i); w.pop(i); picked.append(choice)
    return picked

# CS 682 Fall 2026: everyone submitted (window closed 2026-10-01). Buoy and tutoring are the most popular.
c1_projects = visible[1]
c1_weights = [{pid["buoy"]: 9, pid["tutoring"]: 8, pid["dock"]: 5, pid["solar"]: 6, pid["rooms"]: 4,
               pid["reminders"]: 3}[p] for p in c1_projects]
for k, s in enumerate(roster[1]):
    prefs[s] = rank_projects(c1_projects, c1_weights)
    when = datetime(2026, 9, 21, 10) + timedelta(hours=rng.randint(0, 230), minutes=rng.randint(0, 59))
    for rank, p in enumerate(prefs[s], 1):
        pref_rows.append([q(s), q(p), q(1), q(rank), ts(when)])

# CS 410: window still open; 11 of 16 have submitted.
c2_projects = visible[2]
for s in roster[2][:11]:
    picks = rank_projects(c2_projects, [5, 3, 4, 6, 4])
    when = datetime(2026, 11, 10, 12) + timedelta(hours=rng.randint(0, 160), minutes=rng.randint(0, 59))
    for rank, p in enumerate(picks, 1):
        pref_rows.append([q(s), q(p), q(2), q(rank), ts(when)])
insert("student_preference", ["student", "project", "course", "rank", "submitted_at"], pref_rows)

# Assign CS 682 teams of four, honoring the best available choice (random tie order).
load = {p: [] for p in c1_projects}
order = list(roster[1]); rng.shuffle(order)
assignment, got_rank = {}, {}
for rank in range(3):
    for s in order:
        if s in assignment:
            continue
        p = prefs[s][rank]
        if len(load[p]) < CAPACITY:
            load[p].append(s); assignment[s] = p; got_rank[s] = rank + 1
for s in order:  # anyone left goes to the emptiest team
    if s not in assignment:
        p = min(load, key=lambda x: len(load[x])); load[p].append(s); assignment[s] = p; got_rank[s] = None
assert all(len(v) == CAPACITY for v in load.values())
insert("project_assignment", ["student", "project", "course", "assigned_by", "assigned_at"],
       [[q(s), q(assignment[s]), q(1), q(uid["suzuki"]), ts(datetime(2026, 10, 2, 14, 30) + timedelta(seconds=k))]
        for k, s in enumerate(roster[1])])

# ---------------------------------------------------------------- milestones & tickets
ms_rows, ticket_rows, ms_id = [], [], {}
for key in C.TICKETS:
    for m, (title, desc, due) in enumerate(C.MILESTONES):
        ms_rows.append([q(len(ms_rows) + 1), q(pid[key]), q(title), q(desc), q(due), q(uid["suzuki"])])
        ms_id[(key, m)] = len(ms_rows)
insert("milestone", ["id", "project", "title", "description", "due_date", "created_by"], ms_rows)

for key, tickets in C.TICKETS.items():
    team = load[pid[key]]
    for n, (title, desc, priority, m) in enumerate(tickets):
        status = {0: "Done", 1: "Done", 3: "To Do"}.get(m) or ["In Progress", "Review", "To Do"][n % 3]
        if m == 1 and n == 3:
            status = "Review"
        assignee = None if (m == 3 and key in ("solar", "rooms")) else team[n % len(team)]
        creator = uid["suzuki"] if n == 0 else team[(n + 1) % len(team)]
        created = datetime(2026, 10, 6, 10) + timedelta(days=m * 12 + n % 3, hours=n)
        updated = created + timedelta(days={"Done": 6, "Review": 9, "In Progress": 4, "To Do": 0}[status],
                                      hours=n * 2)
        updated = max(created, min(updated, datetime(2026, 11, 17, 21, 0)))
        ticket_rows.append([q(len(ticket_rows) + 1), q(pid[key]), q(title), q(desc), q(status), q(priority),
                            q(assignee), q(ms_id[(key, m)]), q(creator), ts(created), ts(updated)])
insert("ticket", ["id", "project", "title", "description", "status", "priority", "assignee", "milestone",
                  "created_by", "created_at", "updated_at"], ticket_rows)

# ---------------------------------------------------------------- team chat (db/migrations/chatdev.sql)
# One project chat per team, with a short conversation between the students and the course instructor.
first_name = {u[0]: u[1].split(" ")[0] for u in users}
channel_rows, message_rows = [], []
for key, messages in C.CHAT.items():
    team = load[pid[key]]
    channel_id = len(channel_rows) + 1
    opened = min(datetime.fromisoformat(m[1]) for m in messages) - timedelta(minutes=5)
    channel_rows.append([q(channel_id), q("project"), "NULL", q(pid[key]), "NULL", "NULL", ts(opened), "NULL"])
    names = {f"t{i}": first_name[s] for i, s in enumerate(team)}
    for entry in messages:
        who, when, text = entry[0], entry[1], entry[2]
        deleted = len(entry) > 3 and entry[3]
        sender = uid["suzuki"] if who == "faculty" else team[int(who[1:])]
        sent = datetime.fromisoformat(when)
        message_rows.append([q(len(message_rows) + 1), q(channel_id), q(sender), q(text.format(**names)), ts(sent),
                             ts(sent + timedelta(minutes=1)) if deleted else "NULL",
                             q(sender) if deleted else "NULL"])
insert("chat_channel", ["id", "scope", "course", "project", "name", "created_by", "created_at", "archived_at"],
       channel_rows)
insert("chat_message", ["id", "channel", "sender", "body", "created_at", "deleted_at", "deleted_by"], message_rows)

# ---------------------------------------------------------------- assemble
first_choice = sum(1 for r in got_rank.values() if r == 1)
header = f"""-- UniFlow demo dataset (generated by generate_seed.py; do not hand-edit).
--
-- WARNING: this DELETES ALL DATA in every UniFlow table and replaces it.
-- Run it on a Neon branch first. Everything runs in one transaction: if any
-- statement fails, nothing changes.
--
-- Contents: {len(users)} users, {len(C.COURSES)} courses, {len(C.PROJECTS)} projects, {len(file_rows)} PDF attachments,
-- {len(review_rows)} review events, {len(enroll_rows)} enrollments, {len(pref_rows)} preference rows,
-- {len(assignment)} assignments ({first_choice} students got their 1st choice), {len(ms_rows)} milestones, {len(ticket_rows)} tickets,
-- {len(channel_rows)} team chats with {len(message_rows)} messages.
--
-- Requires the chat tables: run db/migrations/chatdev.sql on the branch BEFORE this file.
-- Every account shares one demo password (given separately). Emails use reserved .test domains.

BEGIN;

TRUNCATE public.chat_message, public.chat_channel_project, public.chat_channel,
         public.ticket, public.milestone, public.project_assignment, public.student_preference,
         public.project_course_visibility, public.project_reviews, public.project_files,
         public.course_enrollments, public.projects, public.courses, public.users
         RESTART IDENTITY;
-- No CASCADE on purpose: if any table outside this list references one of these,
-- Postgres refuses the TRUNCATE and the whole transaction rolls back untouched.
"""
footer = "\n-- Move identity counters past the explicit ids so new rows from the app don't collide.\n" + "\n".join(
    f"SELECT setval(pg_get_serial_sequence('public.{t}', 'id'), (SELECT max(id) FROM public.{t}));"
    for t in ["users", "courses", "projects", "project_files", "milestone", "student_preference",
              "project_assignment", "ticket", "chat_channel", "chat_message"]) + "\n\nCOMMIT;\n"
sys.stdout.write(header + "\n" + "\n".join(out) + footer)
print(f"first-choice: {first_choice}/24, ranks: "
      f"{sorted((r or 0) for r in got_rank.values())}", file=sys.stderr)
