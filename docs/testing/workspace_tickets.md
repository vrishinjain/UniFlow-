# Workspace tickets — item 2

## Implemented diff

- Extended the existing workspace services with pure field/ID validation and transactional ticket creation, content editing, deletion, and status moves. The existing database schema and project models are unchanged.
- Each mutation authorizes the current actor, locks the project and actor, rechecks permissions, validates project-scoped targets and links, authorizes immediately before the write, and returns a freshly authorized snapshot from the same transaction. Transaction failures propagate; a commit must succeed before a result is returned.
- Content editing does not change status or creation metadata. Status moves update only status and the update timestamp. Creation always uses To Do and the server-resolved actor as creator.
- Added create/edit forms, a three-line actions menu, and a separate destructive confirmation. Failed validation/mutations preserve the dialog and submitted fields. No optimistic ticket updates are used.
- Added enterprise drag handles and whole-column drop targets, including empty columns. Ticket and column identifiers have distinct prefixes. Dropping on a card reaches its enclosing column; the handler also supports scoped ticket-target resolution. The draggable wrapper only surrounds the handle, not menu/form controls.
- A keyboard user can press Enter/Space on a handle, Tab to a column's Move here button, and press Enter/Space to move through the same persistent status handler. Pressing the selected handle again cancels pickup. Every card also has a labeled native status select for screen-reader, touch, and other non-pointer use.
- Added pending-write guards, session/route/request checks before and after asynchronous work, and private-state clearing on login/project/access changes. Assignee filtering now works without destroying the loaded snapshot and survives mutation refreshes when the selected member remains eligible.
- Added an opt-in wide layout used only by the workspace, and reduced the board minimum width to four 240px columns plus gaps. The board owns horizontal overflow. Other role pages retain their existing layout and navigation.
- Switched the existing entry-point app to the enterprise app required by its drag-and-drop components.
- No milestone creation/editing, milestone table, or milestone filter was added. Existing same-project milestones are selectable in the ticket form.

## Public service signatures

All mutation functions return `WorkspaceSnapshot`. Actor IDs must come from the application's server-side session, never browser fields.

- `validate_ticket_id(value: object, label: str = "Ticket", optional: bool = False) -> int | None`
- `validate_ticket_fields(title: object, description: object, priority: object, assignee: object = None, milestone: object = None) -> TicketFields`
- `create_ticket(actor_id: int, project_id: int, title: object, description: object, priority: object, assignee: object = None, milestone: object = None) -> WorkspaceSnapshot`
- `update_ticket(actor_id: int, project_id: int, ticket_id: int, title: object, description: object, priority: object, assignee: object = None, milestone: object = None) -> WorkspaceSnapshot`
- `delete_ticket(actor_id: int, project_id: int, ticket_id: int) -> WorkspaceSnapshot`
- `move_ticket(actor_id: int, project_id: int, ticket_id: int, status: str) -> WorkspaceSnapshot`

Validation trims title/description, requires nonempty strings with limits of 200/20,000 characters, rejects null characters, and restricts priority to Low/Medium/High/Urgent. Optional link IDs accept None or an empty string. IDs reject booleans, floats, signed/whitespace/Unicode representations, zero, negatives, and bigint overflow. Link eligibility is checked separately against current persisted project membership inside the transaction.

## Event signatures for validation

- `open_create()`
- `open_edit(ticket_id: str)`
- `open_delete(ticket_id: str)`
- `toggle_menu(ticket_id: str)`
- `close_dialog()` and `dialog_changed(opened: bool)`
- `submit_ticket(form_data: dict[str, Any])`
- `confirm_delete()`
- `change_status(ticket_id: str, status: str)`
- `drop_ticket(item: dict[str, Any], target: str)` — item.id is ticket:<id>; target is column:<status> or ticket:<id>.
- `keyboard_pickup(ticket_id: str)` and `keyboard_drop(status: str)`
- `mutate_ticket(request: int, route_id: str, path: str, operation: str, ticket_id: str, status: str)` — background worker, guarded by the current pending operation and session; not a browser actor/role API.

## Safe checks

Run `python -m scripts.test_workspace_tickets` for pure validation, malformed-input service guards, signatures, source-boundary checks, and component construction. It does not connect to a database or invoke any valid mutation. It uses no fixture writes or mocked service implementation.

Run `python -m scripts.test_workspace_static` for the existing syntax/component checks. These scripts are standalone unittest/static checks, not pytest database fixtures. Do not run the repository's write-capable integration fixtures against the connected application database.

These checks were added but not executed by the builder in this phase. No database mutations, including rollback-only mutations, were executed during implementation.

## Operator acceptance checks (only with explicit write authorization)

Use an isolated authorized test environment for interactive mutation tests. Do not seed or change the connected application's data for builder validation.

1. For each allowed role, create a ticket, reload, and confirm To Do, trimmed fields, priority, links, and creator identity. Unassigned and No milestone remain empty selections when editing.
2. Edit a ticket created/assigned to another eligible member. Move it while another edit form is open; saving that form must not change its current status or creation metadata.
3. Reject inactive/password-change-required/non-team assignees and foreign-project milestones. Test membership revocation between opening and saving.
4. Supply foreign-project ticket IDs to edit/delete/move services using an authorized actor for the selected project; confirm a generic missing-target error and no change to either project.
5. Open Delete ticket from the menu; confirm there is no deletion until the separate destructive action is pressed. Cancel retains the ticket. Confirm and reload verifies deletion.
6. Drag via the handle into every column, including an empty column and onto another card. Confirm persisted status after reload. Repeated drops during a pending move must not cause repeated writes.
7. Perform keyboard pickup/drop and use each native status select. Check focus trapping, required labels, live feedback, cancel behavior, and screen-reader announcement of dialogs.
8. Keep an assignee filter active during CRUD/moves; confirm it remains selected after refresh and Clear filter still restores all cards.
9. Interrupt database availability during save/move. The form remains populated on failure; cards are never moved optimistically. A failed move attempts a database refetch and reports failure if refresh is unavailable.
10. Navigate to another project or sign out while a dialog or write is active. No previous project's dialog or asynchronous snapshot may appear on the next route/session. Denied access clears private workspace state.
11. At wide desktop widths all four columns fit. At smaller widths only the board scrolls horizontally. Role navigation is unchanged.
