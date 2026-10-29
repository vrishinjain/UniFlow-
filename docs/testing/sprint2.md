# UniFlow – Sprint 2 Test Checklist and Test Run

**Task:** T-10 (#43)  
**Sprint:** Sprint 2  
**Tester:** Keerthi  
**Status:** Testing completed; branch verification pending  
**Pull Request:** #49

## 1. Purpose

This document records the Sprint 2 testing results for UniFlow. The tests cover US-1 (#29), US-2 (#30), and US-3 (#31).

The checklist includes role-based dashboards, sponsor project submissions, faculty project details, file downloads, and access restrictions.

All 22 manual tests were reported as passed by the tester. Eight automated project submission tests also passed.

## 2. Test Checklist

| Test ID | User Story | Feature | Test Steps | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|---|
| TC-01 | US-1 | Admin dashboard | Sign in as Admin | Redirected to `/admin` | Admin dashboard opened | Pass |
| TC-02 | US-1 | Program Admin dashboard | Sign in as Program Admin | Redirected to `/programadmin` | Program Admin dashboard opened | Pass |
| TC-03 | US-1 | Faculty dashboard | Sign in as Faculty | Redirected to `/faculty` | Faculty dashboard opened | Pass |
| TC-04 | US-1 | Student dashboard | Sign in as Student | Redirected to `/student` | Student dashboard opened | Pass |
| TC-05 | US-1 | Sponsor dashboard | Sign in as Sponsor | Redirected to `/sponsor` | Sponsor dashboard opened | Pass |
| TC-06 | US-1 | Dashboard information | Open each dashboard after signing in | User name, role, and logout button displayed | Dashboard information displayed | Pass |
| TC-07 | US-1 | Role protection | Sign in as Student and open `/faculty` | Redirected to `/student` | Access restricted | Pass |
| TC-08 | US-1 | Logged-out protection | Open `/admin` while logged out | Redirected to `/` | Redirected to login | Pass |
| TC-09 | US-1 | Logout | Sign in, log out, and reopen protected dashboard | Session cleared and redirected to `/` | Protected access blocked after logout | Pass |
| TC-10 | US-2 | Submit project button | Sign in as Sponsor and click Submit new project | Submission form opens | Form opened | Pass |
| TC-11 | US-2 | Required fields | Submit form with empty title or description | Validation error and submission blocked | Invalid submission blocked | Pass |
| TC-12 | US-2 | File upload limit | Attach up to three valid files | Up to three files accepted | Three files accepted | Pass |
| TC-13 | US-2 | File type validation | Upload `.txt` file | File rejected with error | Invalid file rejected | Pass |
| TC-14 | US-2 | File size validation | Upload file larger than 10 MB | File rejected with error | Oversized file rejected | Pass |
| TC-15 | US-2 | Too many files | Try attaching four files | Fourth file blocked | File limit enforced | Pass |
| TC-16 | US-2 | Project submission | Submit valid title and description | Project saved with status `submitted` and success message | Submission successful | Pass |
| TC-17 | US-2 | My projects list | Open Sponsor dashboard after submitting | Own projects show title, status, and date | Projects displayed | Pass |
| TC-18 | US-3 | Faculty project list | Sign in as Faculty and open project list | Submitted projects show title, sponsor, and date, newest first | Projects displayed | Pass |
| TC-19 | US-3 | Project details | Click a project in Faculty list | Full description and attachments displayed | Project details displayed | Pass |
| TC-20 | US-3 | File download | Download an attached file | Selected file downloads successfully | File downloaded | Pass |
| TC-21 | US-3 | Faculty access restriction | Sign in as Sponsor and open Faculty project page | Access blocked or redirected | Sponsor access blocked | Pass |
| TC-22 | US-3 | Student access restriction | Sign in as Student and open Faculty project page | Access blocked or redirected | Student access blocked | Pass |

## 3. Manual Test Execution

**Tester:** Keerthi  
**Execution date:** October 2026  
**Execution branch:** To be verified on `develop`

| Result | Count |
|---|---:|
| Passed | 22 |
| Failed | 0 |
| Pending | 0 |
| Total | 22 |

**Overall manual test result: PASS**

## 4. Automated Unit Tests

**Execution date:** October 22, 2026  
**Test file:** `scripts/test_project_submission.py`

**Command:**

`python -m unittest scripts.test_project_submission -v`

| Result | Count |
|---|---:|
| Passed | 8 |
| Failed | 0 |
| Errors | 0 |
| Total | 8 |

**Overall automated test result: PASS**

The automated tests covered project submission validation, attachment limits, file types, file signatures, authorization, rollback, and error handling.

Tests specifically for `read_and_validate` and `parse_roster` were not included in this run.

## 5. Bug Reporting

No failures were reported in the completed tests.

If any test fails during verification on `develop`, a GitHub bug issue will be created with the test ID, reproduction steps, expected result, actual result, and supporting evidence.

## 6. Sprint 2 Test Run Summary

**Manual tests:** 22 passed  
**Automated tests:** 8 passed  
**Total recorded tests:** 30 passed  
**Failed:** 0  
**Pending test cases:** 0  
**Verification on `develop`:** Pending confirmation  
**Final approval:** Pending

All recorded tests passed. Final T-10 approval requires confirming the must-have tests on the `develop` branch.
