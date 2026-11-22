"""Hand-written content for the UniFlow demo dataset (people, courses, projects, workspaces).

The admin account is named for the course instructor (Kenneth Fletcher). Course codes and titles
come from cs.umb.edu/courses. Faculty, students, sponsors and organizations are fictional.
Every email uses a reserved .test domain,
so no message can ever reach a real inbox.
"""

UNI = "university.test"

ADMIN = ("Kenneth Fletcher", f"kenneth.fletcher@{UNI}")

FACULTY = [
    # (key, name, email, status)
    ("suzuki", "Elena Marsh", f"elena.marsh@{UNI}", "active"),
    ("haehn", "Rajiv Menon", f"rajiv.menon@{UNI}", "active"),
    ("iyer", "Laura Bennett", f"laura.bennett@{UNI}", "pending"),  # awaiting admin approval
]

# key -> (contact name, email, organization, status)
SPONSORS = {
    "cobalt": ("Priya Nair", "priya.nair@cobaltfreight.test", "Cobalt Freight Logistics", "active"),
    "harborview": ("Marcus Bell", "marcus.bell@harborviewclinic.test", "Harborview Community Clinic", "active"),
    "greenline": ("Sofia Alvarez", "sofia.alvarez@greenlineenergy.test", "Greenline Energy Co-op", "active"),
    "oceanlab": ("Daniel Okoro", f"daniel.okoro@{UNI}", "Coastal Ocean Sensing Lab (School for the Environment)", "active"),
    "brightpath": ("Hannah Leclerc", "hannah.leclerc@brightpathtutoring.test", "Brightpath Tutoring", "active"),
    "library": ("Tom Gallagher", "tom.gallagher@riversidelibrary.test", "Riverside Public Library", "active"),
    "northwind": ("Mei Chen", "mei.chen@northwindrobotics.test", "Northwind Robotics", "active"),
    "pocketledger": ("Jamal Rivers", "jamal.rivers@pocketledger.test", "Pocket Ledger", "active"),
    "lumen": ("Ana Petrova", "ana.petrova@lumenanalytics.test", "Lumen Analytics", "pending"),  # new signup, no projects yet
}

STUDENT_NAMES = [
    "Aisha Rahman", "Benjamin Ortiz", "Chloe Nguyen", "David Kim", "Emily Johnson", "Farhan Siddiqui",
    "Gabriela Santos", "Henry Walsh", "Isabella Rossi", "Jason Lee", "Kavya Reddy", "Liam O'Connor",
    "Maya Patel", "Nathan Brooks", "Olivia Martinez", "Pedro Alves", "Quinn Murphy", "Rachel Goldberg",
    "Samuel Adeyemi", "Tara Sullivan", "Umar Haddad", "Valentina Cruz", "William Chen", "Xavier Dubois",
    "Yuki Tanaka", "Zoe Thompson", "Adrian Popescu", "Bianca Ferreira", "Caleb Wright", "Divya Iyer",
    "Ethan Park", "Fatima Al-Sayed", "Grace O'Brien", "Hassan Karimi", "Ivy Zhang", "Jonah Friedman",
    "Keisha Brown", "Lucas Moreau", "Mariana Lopez", "Noah Fitzgerald", "Omar Farouk", "Priyanka Shah",
    "Ryan Doyle", "Sana Mirza", "Tyler Hughes", "Victor Nascimento", "Wen Li", "Yasmin Costa",
]

# code, name, term, faculty key, preferences_open, created
COURSES = [
    ("CS682", "Software Development Laboratory", "Fall 2026", "suzuki", False, "2026-08-20 09:10"),
    ("CS410", "Introduction to Software Engineering", "Fall 2026", "suzuki", True, "2026-08-21 11:25"),
    ("CS681", "Object-Oriented Software Development", "Fall 2026", "haehn", False, "2026-08-24 15:40"),
    ("CS682", "Software Development Laboratory", "Spring 2027", "haehn", False, "2026-11-10 10:05"),
]

# Each project: sponsor, title, status, submitted, summary (stored as projects.description),
# plus brief sections used to render the attached PDF.
PROJECTS = [
    dict(
        key="dock", sponsor="cobalt", title="Dock Appointment Scheduler", status="accepted",
        submitted="2026-08-18 13:20",
        description=(
            "Cobalt Freight runs a 40-door cross-dock in Chelsea, MA. Carriers book unloading slots by phone "
            "and email today, which causes double-bookings and trucks idling in the yard for hours.\n\n"
            "Build a web app where carriers request dock appointments, dispatchers approve or move them on a "
            "drag-and-drop daily calendar, and drivers get a confirmation with their door number. A simple "
            "dashboard should show door utilization and average wait time per day."
        ),
        goals=["Self-service booking for carriers with company accounts",
               "Dispatcher calendar view with conflict detection",
               "Utilization and wait-time dashboard"],
        tech="Any modern web stack. We can provide a CSV export of three months of historical bookings.",
        files=["dock_scheduler_project_brief.pdf", "historical_bookings_sample.pdf"],
    ),
    dict(
        key="reminders", sponsor="harborview", title="Patient Appointment Reminders", status="accepted",
        submitted="2026-08-19 10:05",
        description=(
            "Harborview Community Clinic loses about 18% of appointments to no-shows. Front-desk staff call "
            "patients the day before, but only reach about half of them.\n\n"
            "Build a reminder service that reads the daily appointment list, sends SMS and email reminders in "
            "the patient's preferred language (English, Spanish, Haitian Creole), and lets patients confirm or "
            "cancel with a one-word reply. Staff need a screen showing who confirmed, cancelled, or never replied. "
            "Students will work only with synthetic patient data."
        ),
        goals=["Scheduled reminders 48 and 24 hours before each visit",
               "Two-way confirm/cancel replies",
               "Front-desk status board and no-show report"],
        tech="Twilio test credentials are fine; no real messages are sent. Synthetic data generator provided by the clinic.",
        files=["appointment_reminders_project_brief.pdf"],
        history=[("request_revision", "suzuki", "2026-08-25 16:30",
                  "Please confirm that students will never handle real patient records, and say which "
                  "languages are in scope for the first release."),
                 ("resubmitted", None, "2026-08-27 09:12", None)],
    ),
    dict(
        key="volunteers", sponsor="harborview", title="Volunteer Shift Planner", status="accepted",
        submitted="2026-08-22 14:45",
        description=(
            "The clinic relies on about 60 volunteers for its Saturday health fairs and food pantry. Shifts are "
            "coordinated in a shared spreadsheet that nobody trusts.\n\n"
            "Build a mobile-friendly site where volunteers sign up for open shifts, swap shifts with each other, "
            "and get reminders. Coordinators should see coverage gaps at a glance and export hours for annual grant reports."
        ),
        goals=["Shift sign-up and swap requests", "Coverage-gap view for coordinators",
               "Volunteer-hours export for grant reporting"],
        tech="Mobile-first web app. Must work on older Android phones.",
        files=["volunteer_planner_project_brief.pdf"],
    ),
    dict(
        key="solar", sponsor="greenline", title="Rooftop Solar Output Forecasting", status="accepted",
        submitted="2026-08-17 08:55",
        description=(
            "Greenline Energy Co-op manages 210 member rooftop solar systems around Boston. Members want to know "
            "how much power to expect tomorrow so they can plan when to run heavy appliances.\n\n"
            "Using two years of 15-minute inverter readings and public weather forecasts, build a model that predicts "
            "next-day output per system, and a small member portal that shows the forecast next to actual production."
        ),
        goals=["Data pipeline for inverter readings and weather forecasts",
               "Next-day forecast model with an accuracy report",
               "Member portal showing forecast vs. actual"],
        tech="Python preferred for the modelling. Anonymized inverter data (about 2 GB) will be shared via a cloud bucket.",
        files=["solar_forecasting_project_brief.pdf"],
    ),
    dict(
        key="buoy", sponsor="oceanlab", title="Harbor Buoy Data Pipeline", status="accepted",
        submitted="2026-08-16 16:10",
        description=(
            "The Coastal Ocean Sensing Lab has six buoys in Boston Harbor reporting temperature, salinity, dissolved "
            "oxygen and turbidity every ten minutes. Today the data arrives as raw text files that a graduate student "
            "cleans by hand.\n\n"
            "Build an automated pipeline that ingests the files, flags sensor faults, stores clean data in a database, "
            "and publishes a public web page with live charts and a CSV download for researchers."
        ),
        goals=["Automated ingestion with fault and outlier flags",
               "Clean time-series store with an API",
               "Public dashboard with charts and downloads"],
        tech="Lab server runs Linux. PostgreSQL/TimescaleDB suggested but not required.",
        files=["buoy_pipeline_project_brief.pdf", "buoy_data_dictionary.pdf"],
    ),
    dict(
        key="samples", sponsor="oceanlab", title="Field Sample Tracking App", status="accepted",
        submitted="2026-08-23 11:30",
        description=(
            "Lab staff collect around 400 water and sediment samples each season. Labels get smudged, freezers fill "
            "up, and it is hard to tell which samples have already been analyzed.\n\n"
            "Build a mobile app that prints QR labels in the field, records GPS location and time on collection, and "
            "tracks each sample through freezer storage and lab analysis."
        ),
        goals=["QR label generation and scanning", "Chain-of-custody history per sample",
               "Freezer inventory view"],
        tech="Must work offline on boats and sync when back on Wi-Fi.",
        files=["sample_tracking_project_brief.pdf"],
    ),
    dict(
        key="tutoring", sponsor="brightpath", title="Tutor-Student Matching Platform", status="accepted",
        submitted="2026-08-18 19:40",
        description=(
            "Brightpath Tutoring pairs about 150 volunteer tutors with middle- and high-school students across "
            "Dorchester and Mattapan. Matching is done by one staff member using email threads.\n\n"
            "Build a platform where tutors list their subjects and availability, families request help, and staff "
            "approve suggested matches. Include session logging so Brightpath can report hours to its funders."
        ),
        goals=["Tutor and family profiles with availability", "Suggested matches for staff approval",
               "Session log and funder report"],
        tech="Families mostly use phones; Spanish translation of family-facing pages is a stretch goal.",
        files=["tutor_matching_project_brief.pdf"],
    ),
    dict(
        key="rooms", sponsor="library", title="Study Room Booking System", status="accepted",
        submitted="2026-08-20 12:15",
        description=(
            "Riverside Public Library has 12 study rooms booked on a paper sign-up sheet at the front desk. Rooms "
            "sit empty while people are turned away.\n\n"
            "Build a booking system where patrons reserve rooms online with their library card number, check in with "
            "a QR code on the door, and lose the booking if they don't show within 15 minutes. Staff need usage "
            "reports by branch and time of day."
        ),
        goals=["Online booking with library-card login", "QR check-in and automatic no-show release",
               "Usage reporting for staff"],
        tech="Will eventually integrate with the library's catalog system; a mock card-lookup API is enough for this project.",
        files=["room_booking_project_brief.pdf", "branch_room_layout.pdf"],
    ),
    dict(
        key="robots", sponsor="northwind", title="Warehouse Robot Fleet Simulator", status="pending",
        submitted="2026-08-26 10:00",
        description=(
            "Northwind Robotics builds autonomous carts for small warehouses. Before installing at a customer site, "
            "we need to estimate how many carts are needed and where they will get congested.\n\n"
            "Build a 2D simulator that loads a warehouse floor plan and order history, runs a fleet of carts with "
            "simple path planning, and reports throughput and congestion heat maps. Scope has been narrowed to a "
            "single warehouse layout and up to 20 carts."
        ),
        goals=["Floor-plan import and grid map", "Cart path planning with collision avoidance",
               "Throughput report and congestion heat map"],
        tech="Python or C++. Visualization in the browser is preferred.",
        files=["fleet_simulator_project_brief.pdf"],
        history=[("request_revision", "haehn", "2026-09-02 13:45",
                  "The original scope (multi-site, 200 carts, live hardware integration) is too large for one "
                  "semester. Please narrow it to one layout and a simulated fleet."),
                 ("resubmitted", None, "2026-11-12 08:30", None)],
    ),
    dict(
        key="receipts", sponsor="pocketledger", title="Receipt Scanning Expense Tracker", status="rejected",
        submitted="2026-08-21 17:05",
        description=(
            "Pocket Ledger wants a feature that lets customers photograph receipts, extracts the merchant, total and "
            "date with OCR, and files the expense into the right budget category."
        ),
        goals=["Receipt OCR", "Automatic categorization", "Integration with the Pocket Ledger app"],
        tech="Requires access to production customer accounts for testing.",
        files=["receipt_scanner_project_brief.pdf"],
        history=[("reject", "suzuki", "2026-08-29 11:20",
                  "The project requires students to test against real customers' financial data, which we can't "
                  "support in a course. You're welcome to resubmit a version that uses synthetic data only.")],
    ),
    dict(
        key="budgetbot", sponsor="pocketledger", title="Budgeting Coach Chatbot", status="revision_requested",
        submitted="2026-11-05 15:50",
        description=(
            "A chat assistant inside the Pocket Ledger app that answers questions like \"how much did I spend on "
            "food this month?\" and suggests a realistic monthly budget, using a synthetic transaction dataset."
        ),
        goals=["Natural-language questions over transactions", "Budget suggestions", "Usage analytics"],
        tech="Synthetic transaction dataset will be provided.",
        files=["budget_coach_project_brief.pdf"],
        history=[("request_revision", "suzuki", "2026-11-09 10:40",
                  "Please describe what students will build themselves versus what an outside chatbot service "
                  "provides, and how answers will be checked for accuracy.")],
    ),
    dict(
        key="signup", sponsor="greenline", title="Community Solar Sign-up Portal", status="pending",
        submitted="2026-11-14 09:25",
        description=(
            "Greenline is launching a community solar garden for renters who can't install their own panels. Build "
            "a sign-up portal that checks eligibility by address and utility account, estimates monthly savings, "
            "and manages a waitlist when the garden is fully subscribed."
        ),
        goals=["Eligibility check by address", "Savings estimate", "Waitlist management"],
        tech="Web app; utility account lookup can be mocked.",
        files=["community_solar_project_brief.pdf"],
    ),
    dict(
        key="hos", sponsor="cobalt", title="Driver Hours-of-Service Logger", status="accepted",
        submitted="2026-11-03 14:00",
        description=(
            "Cobalt's local drivers record their working hours on paper logs that are typed up weekly. Build a simple "
            "mobile logger that tracks on-duty, driving and break time, warns drivers before they hit federal hour "
            "limits, and exports weekly timesheets for payroll."
        ),
        goals=["One-tap duty status changes", "Hour-limit warnings", "Weekly timesheet export"],
        tech="Mobile-first; must work with intermittent cell coverage.",
        files=["hours_logger_project_brief.pdf"],
    ),
]

# course index -> list of (project key, faculty key sharing it, shared at)
VISIBILITY = {
    0: [("dock", "suzuki", "2026-08-28 10:00"), ("reminders", "suzuki", "2026-08-28 10:02"),
        ("solar", "suzuki", "2026-08-28 10:04"), ("buoy", "suzuki", "2026-08-28 10:06"),
        ("tutoring", "suzuki", "2026-08-28 10:08"), ("rooms", "suzuki", "2026-08-28 10:10")],
    1: [("dock", "suzuki", "2026-09-08 09:30"), ("volunteers", "suzuki", "2026-09-08 09:32"),
        ("samples", "suzuki", "2026-09-08 09:34"), ("tutoring", "suzuki", "2026-09-08 09:36"),
        ("rooms", "suzuki", "2026-09-08 09:38")],
    2: [("solar", "haehn", "2026-09-04 14:00"), ("buoy", "haehn", "2026-09-04 14:02"),
        ("samples", "haehn", "2026-09-04 14:04")],
    3: [("hos", "haehn", "2026-11-11 16:20"), ("volunteers", "haehn", "2026-11-11 16:22")],
}

# Accept actions (who accepted each accepted project, and when)
ACCEPTED_BY = {
    "dock": ("suzuki", "2026-08-28 10:00"), "reminders": ("suzuki", "2026-08-28 10:02"),
    "solar": ("suzuki", "2026-08-28 10:04"), "buoy": ("suzuki", "2026-08-28 10:06"),
    "tutoring": ("suzuki", "2026-08-28 10:08"), "rooms": ("suzuki", "2026-08-28 10:10"),
    "volunteers": ("suzuki", "2026-09-08 09:32"), "samples": ("haehn", "2026-09-04 14:04"),
    "hos": ("haehn", "2026-11-11 16:20"),
}

MILESTONES = [
    ("Sprint 1: Requirements and setup",
     "Meet the sponsor, agree on user stories, set up the repository, CI and a deployed hello-world.",
     "2026-10-16"),
    ("Sprint 2: Core features",
     "Deliver the main user flow end to end with real (synthetic) data and demo it to the sponsor.",
     "2026-11-06"),
    ("Sprint 3: Integration and testing",
     "Finish secondary features, write automated tests, fix bugs found in sponsor testing.",
     "2026-11-27"),
    ("Final demo and handoff",
     "Final presentation, deployment guide and handoff of the code and documentation to the sponsor.",
     "2026-12-11"),
]

# Workspace tickets for each CS 682 Fall 2026 project: (title, description, priority, milestone index)
TICKETS = {
    "dock": [
        ("Interview dispatchers about booking rules", "Capture door types, slot lengths and carrier priority rules from the two shift leads.", "High", 0),
        ("Set up repo, CI and staging deploy", "Monorepo with lint and test checks on every pull request; auto-deploy main to staging.", "Medium", 0),
        ("Carrier booking form", "Carriers pick a date, load type and estimated pallets; system offers open slots.", "High", 1),
        ("Dispatcher daily calendar", "Doors as columns, 30-minute rows; drag an appointment to move it.", "Urgent", 1),
        ("Double-booking detection", "Block overlapping appointments on the same door and warn on tight turnarounds.", "High", 2),
        ("Import historical bookings CSV", "Load the three-month sample so the dashboard has realistic data.", "Medium", 2),
        ("Utilization and wait-time dashboard", "Daily door utilization percentage and average yard wait.", "Medium", 2),
        ("Write deployment guide for Cobalt IT", "Step-by-step install, configuration and backup instructions.", "Low", 3),
    ],
    "reminders": [
        ("Define reminder message templates", "Short SMS and email templates in English, Spanish and Haitian Creole, reviewed by clinic staff.", "High", 0),
        ("Synthetic patient data generator", "Generate realistic appointment lists with no real patient information.", "Medium", 0),
        ("Scheduler for 48h and 24h reminders", "Background job that queues reminders and never sends twice.", "Urgent", 1),
        ("Handle CONFIRM / CANCEL replies", "Parse one-word replies in all three languages and update the appointment.", "High", 1),
        ("Front-desk status board", "Live list of today's patients with confirmed, cancelled and no-reply badges.", "High", 2),
        ("Opt-out and quiet hours", "Respect STOP replies and never send between 9pm and 8am.", "High", 2),
        ("Weekly no-show report", "Compare no-show rate before and after reminders.", "Medium", 2),
        ("Accessibility review of staff screens", "Check contrast, keyboard navigation and screen-reader labels.", "Low", 3),
    ],
    "solar": [
        ("Explore inverter dataset", "Profile the two years of readings: gaps, outliers and timezone issues.", "High", 0),
        ("Weather forecast ingestion", "Daily job that pulls next-day cloud cover and irradiance forecasts.", "Medium", 0),
        ("Baseline forecast model", "Clear-sky model scaled by forecast cloud cover; record its error as the baseline.", "High", 1),
        ("Gradient-boosted forecast model", "Per-system model with weather and seasonal features; must beat the baseline.", "Urgent", 1),
        ("Model accuracy report", "Mean absolute error by system size and season, with charts.", "Medium", 2),
        ("Member portal forecast page", "Tomorrow's hourly forecast next to today's actual production.", "High", 2),
        ("Nightly retraining job", "Retrain weekly and alert if accuracy drops below the baseline.", "Low", 2),
        ("Handoff notebook for Greenline analysts", "Documented notebook that reproduces training and evaluation.", "Low", 3),
    ],
    "buoy": [
        ("Document raw file formats for all six buoys", "Two buoys use an older firmware with different column order.", "High", 0),
        ("Database schema for time series", "Tables for readings, sensors and quality flags; agree with lab staff.", "Medium", 0),
        ("Ingestion service", "Watch the upload folder, parse new files and load them idempotently.", "Urgent", 1),
        ("Sensor fault and outlier flags", "Flag stuck values, sudden spikes and out-of-range readings.", "High", 1),
        ("Public dashboard charts", "Last 7 days per buoy and variable, with flagged points shown in grey.", "High", 2),
        ("CSV download API", "Researchers choose buoy, variables and date range.", "Medium", 2),
        ("Alert lab when a buoy goes silent", "Email the lab if no data arrives for two hours.", "Medium", 2),
        ("Operations runbook", "How to add a buoy, re-run ingestion and restore from backup.", "Low", 3),
    ],
    "tutoring": [
        ("Map current matching process", "Shadow the program coordinator and document every step and email.", "High", 0),
        ("Tutor and family profile models", "Subjects, grade levels, availability windows and language preferences.", "Medium", 0),
        ("Tutor sign-up and availability editor", "Weekly availability grid that works on phones.", "High", 1),
        ("Family help request form", "Short form in plain language; Spanish version as a stretch goal.", "High", 1),
        ("Match suggestion algorithm", "Score tutors by subject, availability overlap and distance; staff approve.", "Urgent", 2),
        ("Session logging", "Tutors log date, duration and topics after each session.", "Medium", 2),
        ("Funder hours report", "Hours by tutor, subject and neighborhood for a date range.", "Medium", 2),
        ("Spanish translation of family pages", "Translate and have Brightpath staff review the wording.", "Low", 3),
    ],
    "rooms": [
        ("Gather room list and booking policies", "Room capacities, equipment, max booking length and branch hours.", "High", 0),
        ("Mock library card lookup API", "Stub that validates card numbers and returns the patron's home branch.", "Medium", 0),
        ("Room search and booking flow", "Pick branch, date and time; see available rooms and book in two taps.", "Urgent", 1),
        ("QR code check-in", "Printable QR code per room; scanning confirms the booking.", "High", 1),
        ("Automatic no-show release", "Free the room if nobody checks in within 15 minutes.", "High", 2),
        ("Staff usage reports", "Bookings and no-shows by branch, room and hour of day.", "Medium", 2),
        ("Load test peak booking times", "Simulate the 9am rush on exam weeks.", "Low", 2),
        ("Printable QR signs for every room", "Generate a PDF of door signs with room name and code.", "Low", 3),
    ],
}

# Team chat for each CS 682 Fall 2026 project. One chat per project (chat_channel scope 'project').
# (sender, sent at, message). Sender is a team member index "t0".."t3" (same order the generator
# uses for ticket assignees) or "faculty" for the course instructor. {t0}..{t3} become first names.
# A fourth element True marks a message its sender later deleted (shows as "Message deleted").
CHAT = {
    "dock": [
        ("t0", "2026-11-12 09:14", "Morning all. Dispatcher calendar is in Review, {t3} can someone pair with you on the drag-and-drop edge cases today?"),
        ("t3", "2026-11-12 09:31", "Yes please. Dragging an appointment onto a door that's already booked still lets it drop for a split second before snapping back."),
        ("t2", "2026-11-12 09:40", "I can pair after 2pm. I need the same overlap check for the utilization dashboard anyway."),
        ("t1", "2026-11-12 10:05", "Pushed the wrong branch, ignore the last PR link", True),
        ("t1", "2026-11-12 10:07", "Heads up: the historical bookings CSV from Cobalt uses DD/MM dates. I'll normalize them on import."),
        ("faculty", "2026-11-13 16:20", "Nice progress on the calendar. For the Sprint 3 demo, please show the double-booking warning live with Priya on the call."),
        ("t0", "2026-11-13 16:42", "Will do. Double-booking detection is in Review now, so it should be merged by Monday."),
    ],
    "reminders": [
        ("t0", "2026-11-11 11:02", "Front-desk status board is up on staging. Badges for confirmed / cancelled / no reply are working with the synthetic data."),
        ("t2", "2026-11-11 11:20", "Looks great. The no-show report needs the reply timestamps, can you expose them in the API?"),
        ("t0", "2026-11-11 11:26", "Sure, adding replied_at to the appointment endpoint this afternoon."),
        ("t1", "2026-11-12 14:48", "Quiet hours question: if a reminder is due at 9:30pm, do we send it at 8am the next day or skip it?"),
        ("faculty", "2026-11-12 17:05", "Check with Marcus, but 8am the next day is usually what clinics want. Write the decision down in the ticket."),
        ("t3", "2026-11-13 10:12", "Started the accessibility pass. Contrast on the cancelled badge fails WCAG AA, I'll darken it."),
    ],
    "solar": [
        ("t3", "2026-11-10 13:30", "Gradient-boosted model beats the baseline by 23% MAE on the validation months. Notebook is linked in the ticket."),
        ("t0", "2026-11-10 13:52", "Nice! Can you split the error by system size for the accuracy report?"),
        ("t3", "2026-11-10 14:05", "Already on it. Small systems are noisier, probably because of shading."),
        ("t1", "2026-11-12 09:18", "Member portal forecast page is blocked until the model API is deployed. Who owns that?"),
        ("t2", "2026-11-12 09:33", "I'll deploy it with the retraining job. Aiming for Friday."),
        ("faculty", "2026-11-14 11:45", "Remember Sofia asked for the handoff notebook to run end to end on a fresh machine. Please test that before the final demo."),
    ],
    "buoy": [
        ("t1", "2026-11-11 08:47", "Buoy B4 sent a stuck salinity value all night (31.20 for 9 hours). Fault flag caught it, so the pipeline works!"),
        ("t3", "2026-11-11 09:02", "Great, that's exactly the case Daniel wanted. I'll add a screenshot to the Review ticket."),
        ("t0", "2026-11-11 09:15", "Dashboard now greys out flagged points. B4 looks right on staging."),
        ("t2", "2026-11-12 16:30", "Silent-buoy alert sends a test email to the .test inbox. Two hours felt long during testing, should it be configurable?"),
        ("faculty", "2026-11-13 10:10", "Configurable is good, but keep two hours as the default since that's what the lab asked for."),
        ("t1", "2026-11-14 15:22", "Starting the CSV download API. Planning ISO timestamps in UTC to match the data dictionary."),
    ],
    "tutoring": [
        ("t2", "2026-11-10 17:40", "Funder hours report draft is ready: hours by tutor, subject and neighborhood. Feedback welcome."),
        ("t0", "2026-11-10 18:05", "Match suggestion algorithm is in Review. It now weights availability overlap twice as much as distance."),
        ("t1", "2026-11-11 12:15", "Session logging form is next. Should tutors log topics as free text or pick from a list?"),
        ("t3", "2026-11-11 12:30", "Hannah mentioned free text plus subject tags, so we can still group them in the report."),
        ("faculty", "2026-11-12 15:00", "Good call to check with the sponsor. Please keep the family request form in plain language; that came up in the last review."),
        ("t3", "2026-11-13 09:45", "Got it. I'll start the Spanish translation once the English wording is final."),
    ],
    "rooms": [
        ("t3", "2026-11-11 10:20", "QR check-in works on Android and iOS. The scanner page needs camera permission, I added a short explanation screen."),
        ("t0", "2026-11-11 10:41", "Automatic no-show release is in Review. Rooms free up exactly 15 minutes after the start if nobody checks in."),
        ("t2", "2026-11-12 13:05", "Load test results: the booking flow handles 200 simultaneous requests before slowing down. Writing it up now."),
        ("t1", "2026-11-12 13:30", "Starting the staff usage reports. Tom wants bookings and no-shows by branch and hour of day."),
        ("faculty", "2026-11-14 09:15", "Strong sprint. For the final demo, show a full booking, a check-in and a no-show release in one flow."),
    ],
}
