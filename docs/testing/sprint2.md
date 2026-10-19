# UniFlow – Sprint 2 Test Checklist and Test Run

**Task:** T-10 (#43)
**Sprint:** Sprint 2
**Tester:** Keerthi
**Status:** Not yet executed
**Pull Request:** #49

## 1. Purpose

This document contains the test cases for Sprint 2 of the UniFlow project. The tests are based on the acceptance criteria for US-1 (#29), US-2 (#30), and US-3 (#31).

All tests are currently pending. Actual results will be recorded after the features are available and the tests are executed on the develop branch.

## 2. Test Checklist

| Test ID | User Story | Feature | Test Steps | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|---|
| TC-01 | US-1 | Admin dashboard | Sign in as Admin | User is redirected to `/admin` | Not tested | Pending |
| TC-02 | US-1 | Program Admin dashboard | Sign in as Program Admin | User is redirected to `/program-admin` | Not tested | Pending |
| TC-03 | US-1 | Faculty dashboard | Sign in as Faculty | User is redirected to `/faculty` | Not tested | Pending |
| TC-04 | US-1 | Student dashboard | Sign in as Student | User is redirected to `/student` | Not tested | Pending |
| TC-05 | US-1 | Sponsor dashboard | Sign in as Sponsor | User is redirected to `/sponsor` | Not tested | Pending |
| TC-06 | US-1 | Dashboard information | Open each dashboard after signing in | User name, role, and logout button are displayed | Not tested | Pending |
| TC-07 | US-1 | Role protection | Sign in as Student and open `/faculty` | User is redirected to `/student` | Not tested | Pending |
| TC-08 | US-1 | Logged-out protection | While logged out, open `/admin` | User is redirected to `/login` | Not tested | Pending |
| TC-09 | US-1 | Logout | Sign in, click Logout, and try opening a protected dashboard | Session is cleared and user returns to `/login` | Not tested | Pending |
| TC-10 | US-2 | Submit project button | Sign in as Sponsor and click Submit new project | Project submission form opens | Not tested | Pending |
| TC-11 | US-2 | Required fields | Submit the project form with an empty title or description | Validation error appears and submission is blocked | Not tested | Pending |
| TC-12 | US-2 | File upload limit | Attach up to three valid files to a project | Up to three files are accepted | Not tested | Pending |
| TC-13 | US-2 | File type validation | Upload a `.txt` file | File is rejected with an error; only PDF, DOCX, and PPTX are accepted | Not tested | Pending |
| TC-14 | US-2 | File size validation | Upload a file larger than 10 MB | File is rejected with an error | Not tested | Pending |
| TC-15 | US-2 | Too many files | Try attaching four files | Upload is rejected or blocked because the limit is three files | Not tested | Pending |
| TC-16 | US-2 | Project submission | Submit a project with valid title and description | Project is saved with status `submitted` and a success message appears | Not tested | Pending |
| TC-17 | US-2 | My projects list | Open the Sponsor dashboard after submitting a project | Sponsor's own projects show title, status, and submitted date | Not tested | Pending |
| TC-18 | US-3 | Faculty project list | Sign in as Faculty and open the project list | All submitted projects display title, sponsor name, and submitted date, newest first | Not tested | Pending |
| TC-19 | US-3 | Project details | Click a project in the Faculty project list | Detail page shows the full description and attached file list | Not tested | Pending |
| TC-20 | US-3 | File download | Click the download option for an attached file | The selected file downloads successfully | Not tested | Pending |
| TC-21 | US-3 | Faculty access restriction | Sign in as Sponsor and try to open a Faculty project page | Access is blocked or redirected | Not tested | Pending |
| TC-22 | US-3 | Student access restriction | Sign in as Student and try to open a Faculty project page | Access is blocked or redirected | Not tested | Pending |

## 3. Test Execution

**Environment:** UniFlow application on the `develop` branch
**Execution date:** Not yet scheduled
**Tester:** Keerthi
**Overall result:** Pending

| Result | Count |
|---|---:|
| Passed | 0 |
| Failed | 0 |
| Pending | 22 |

The checklist will be executed when the required Sprint 2 features are available. Each test will be updated with its actual result and a Pass or Fail status.

## 4. Automated Unit Tests

Automated tests are planned for:

- `read_and_validate`
- `parse_roster`, if T-11 is ready

**Status:** Pending implementation and execution.

## 5. Bug Reporting

For every failed test, create a GitHub issue with:

- Test ID and related user story
- Steps to reproduce the problem
- Expected result
- Actual result
- Screenshot or error details, when available

Link the bug issue to T-10 (#43) and update the corresponding test result.

## 6. Sprint 2 Test Run Summary

**Test checklist:** Prepared
**Test execution:** Pending
**Automated unit tests:** Pending
**Bug reports:** To be created if failures occur
**Final approval:** Pending

The T-10 task will be considered complete after the required tests are run on `develop`, actual results are recorded, and all must-have tests pass.
