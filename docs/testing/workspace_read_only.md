# Read-only project workspace (plan item 1)

## Change inventory

- Added `UniFlow_/workspace_services.py`: real read-only SQL queries, reusable current-account/project authorization and deduplicated project-team helpers, typed snapshot records.
- Added `UniFlow_/states/workspace_state.py`: private-session identity, background reads, route/session/request guards, access clearing, retries and reauthorized assignee filtering.
- Added `UniFlow_/components/workspace.py`: role-specific existing dashboard shells, title/team, clearable assignee select, four horizontally scrollable board columns, actual ticket labels and empty/denied/error/loading surfaces.
- Modified `UniFlow_/components/student.py`: linked the assigned project title; retained the separate existing workspace action and its URL; both clear old workspace state on activation. The card remains a section, not a nested anchor.
- Modified `UniFlow_/states/login_state.py`: locally imports and clears WorkspaceState with dashboard access on logout/re-login.
- Modified `UniFlow_/UniFlow_.py`: imports and registers the workspace at `/project/[project_id]/workspace` with `WorkspaceState.load_workspace`.
- Added `scripts/test_workspace_static.py`: syntax and component-construction checks only. Run as `python -m scripts.test_workspace_static` from the project root. It invokes no workspace handlers or database services and uses no mocks.

No ticket/milestone creation, editing, deletion, drag-and-drop, milestone-management UI, faculty/admin entry links, sample records, schema changes, provisioning, or live database tests are included.

## Service interfaces for subsequent read-only runtime tests

- `get_workspace(actor_id: int, project_id: int) -> WorkspaceSnapshot`
- `authorize_workspace(connection: Connection, actor_id: int, project_id: int) -> WorkspaceActor`
- `get_workspace_team(connection: Connection, actor_id: int, project_id: int) -> list[WorkspaceMember]`

The helpers use the caller's connection so later mutations can reauthorize on their own transaction. `get_workspace` opens its own connection and performs SELECTs only. It rejects bool, zero, negative, noninteger and out-of-range IDs with ValueError; valid but nonexistent/unauthorized identities or projects raise PermissionError. Database/configuration failures propagate to the state, which displays a generic retryable message without SQL details.

`WorkspaceSnapshot` always supplies `id`, `title`, `team`, `tickets`, `milestones`, `can_edit_milestones`, and `actor_role`. Entity IDs inside the snapshot are strings to preserve bigint identities in browser controls. Missing ticket assignee/milestone IDs and absent milestone due dates use empty strings. Each member supplies `id`, `full_name`, `role`, `role_label`, `option_label`; option labels include role and ID to distinguish duplicate names. Each ticket supplies `id`, `title`, `description`, `status`, `priority`, `assignee`, `assignee_label`, `milestone`, `milestone_label`. Each milestone supplies `id`, `title`, `description`, `due_date` (ISO date or empty string).

## State interfaces

- `load_workspace()` clears access and starts a read using current route parameters.
- `set_assignee(assignee: str)` starts a freshly authorized read; unknown/ineligible values become all assignees. Selecting the current value also clears it.
- `clear_assignee()` clears the filter with a freshly authorized read.
- `clear_workspace()` clears private content before the assigned-project links navigate.
- `fetch_workspace(request: int, route_id: str, path: str, assignee: str)` is a background handler; it reads actor identity only from LoginState's backend session field. Its arguments grant no authority. A stale request/route/session cannot publish results.
- `_clear_access()` clears sensitive fields and invalidates in-flight requests; login/logout invokes this helper.
- Computed `authorized`, `visible_tickets`, and `board_columns` support rendering only, not authorization decisions.

## Read-only acceptance checks (not executed against live data)

1. Assigned active password-ready student, associated active password-ready faculty (either linkage), and active password-ready system admin receive existing project data. Admin's `can_edit_milestones` is false; associated faculty's is true.
2. Sponsors, unassigned students, unrelated faculty, inactive/password-not-ready users, nonexistent actors/projects and invalid IDs never receive title/team/tickets.
3. No-login and denied routes display Access denied, not a persistent Verifying access message.
4. Project team is deduplicated across courses and contains only the eligible union, not enrollment-only students or sponsors. Names, roles and IDs appear, not email addresses.
5. Ticket milestone labels come only from a milestone belonging to the same project. A former/ineligible assignee is labeled without reading an unrelated person's name.
6. An empty project has four genuine empty status columns and no fabricated records. A filter with no matches explains that condition separately.
7. Switching projects, clearing filters, retrying, signing out or signing in as another user cannot restore a stale load. Every filter operation reloads through authorization.
8. The title and existing workspace action navigate to the same registered route; faculty/admin navigation is unchanged.

The static script is provided for execution by the runtime/test runner; no live database tests or mutations were run during this edit.
