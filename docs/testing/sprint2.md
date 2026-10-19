# UniFlow – Sprint 2 Test Checklist and Test Run

**Task:** T-10 (#43)  
**Sprint:** Sprint 2  
**Tester:** Keerthi  
**Status:** Not yet executed

## 1. Purpose

This document contains the test cases for Sprint 2 of the UniFlow project. The goal is to check that the main features work correctly and identify any problems before the sprint review.

## 2. Test Checklist

| Test ID | Feature | Test Steps | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|
| TC-01 | Admin dashboard | Sign in as Admin and open `/admin` | Admin dashboard opens | Not tested | Pending |
| TC-02 | Program Admin dashboard | Sign in as Program Admin and open `/program-admin` | Program Admin dashboard opens | Not tested | Pending |
| TC-03 | Faculty dashboard | Sign in as Faculty and open `/faculty` | Faculty dashboard opens | Not tested | Pending |
| TC-04 | Student dashboard | Sign in as Student and open `/student` | Student dashboard opens | Not tested | Pending |
| TC-05 | Sponsor dashboard | Sign in as Sponsor and open `/sponsor` | Sponsor dashboard opens | Not tested | Pending |
| TC-06 | Role security | Sign in as Student and try to open `/faculty` | Access is denied | Not tested | Pending |
| TC-07 | Logged-out access | Sign out and try to open `/admin` | User is redirected to sign-in or blocked | Not tested | Pending |
| TC-08 | Shared dashboard layout | Open each role dashboard | User name, role, app name, and logout are displayed | Not tested | Pending |
| TC-09 | Project access | Open the project list using an authorized account | Available projects are displayed correctly | Not tested | Pending |
| TC-10 | Project validation | Try to create a project with an empty title | Validation error is displayed | Not tested | Pending |
| TC-11 | File upload | Upload a valid file to an authorized project | File uploads successfully | Not tested | Pending |
| TC-12 | Invalid file upload | Try uploading a `.txt` file where it is not allowed | Upload is rejected with an error | Not tested | Pending |
| TC-13 | Project permissions | Try to access a project without permission | Access is denied | Not tested | Pending |
| TC-14 | Logout | Click Logout from a dashboard | User is signed out and protected pages are inaccessible | Not tested | Pending |

## 3. Automated Unit Tests

The following functions should be tested using pytest:

- `read_and_validate`: Test valid input, invalid input, and error handling.
- `parse_roster`: Add tests if the roster feature from T-11 is completed.

**Status:** Pending implementation and execution.

## 4. Sprint 2 Test Run

**Branch to test:** `develop`  
**Test environment:** UniFlow application  
**Execution date:** Not yet scheduled

**Test summary:**

- Total planned manual tests: 14
- Passed: 0
- Failed: 0
- Pending: 14

Tests will be executed when the dependent Sprint 2 features are ready and merged into `develop`.

## 5. Bug Reporting

If a test fails, create a separate GitHub issue containing:

- Test ID
- Description of the problem
- Steps to reproduce
- Expected result
- Actual result
- Screenshot or error message, if available

## 6. Final Status

**Sprint 2 testing is pending.**

This checklist will be updated with actual test results after execution. The task is complete when all required tests have been run on `develop`, all must-have tests pass, and failures have been reported.
