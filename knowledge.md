# Project Knowledge

Guidelines that apply to every app in this project.

## Course enrollment eligibility

Also called: approved students; active students; course enrollment

Faculty course enrollment is limited to existing user accounts with role `student` and status `active` (approved). Accounts with `pending` or `rejected` status must not be enrolled by single-email or bulk enrollment. Existing disallowed enrollments are not automatically deleted by this rule.

## Email identity normalization

Also called: case insensitive email; bulk email parsing; duplicate accounts

UniFlow treats account email identity case-insensitively. Trim and lowercase email addresses for imports, account creation, login and faculty course matching; deduplicate mixed-case repeats in files. New account emails are stored lowercase. Never arbitrarily select among multiple pre-existing accounts with the same case-folded address; reject ambiguous identity operations without changing data. Bulk file parsing skips invalid address lines and reports their line numbers, while malformed file structure remains an error.
