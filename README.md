
# UniFlow-

UniFlow – university capstone/research project management platform (CS682).

## Running Tests

This project uses pytest for automated testing.

### 1. Install Dependencies

Open a terminal in the project folder and run:

```bash
python -m pip install -r requirements.txt
```

### 2. Configure the Test Database

Tests require a separate Neon test database.

Before running tests, confirm that the database URL belongs to the approved test branch, not the production database.

Set the `TEST_DATABASE_URL` environment variable.

**Mac / Linux:**

```bash
export TEST_DATABASE_URL='YOUR_TEST_DATABASE_URL'
```

**Windows PowerShell:**

```powershell
$env:TEST_DATABASE_URL = 'YOUR_TEST_DATABASE_URL'
```

Replace `YOUR_TEST_DATABASE_URL` with the actual connection string for the approved test database.

Never commit database passwords or connection strings to GitHub.

### 3. Run All Tests

Run the following command from the project root:

```bash
python -m pytest
```

### 4. Run a Specific Test

To run the initial pytest setup test:

```bash
python -m pytest tests/test_pytest_setup.py -v
```

### 5. Test Database Safety

The pytest configuration in `tests/conftest.py` checks that:

- `TEST_DATABASE_URL` is configured.
- The database URL is valid.
- `TEST_DATABASE_URL` is different from `REFLEX_DB_URL` when the application URL is available.

Tests stop if these checks fail.

These checks do not independently verify the Neon branch identity. Always confirm that the test URL belongs to the approved isolated test database before running database tests.

### 6. Test Fixtures

Shared test fixtures are maintained in `tests/conftest.py`.

Database fixtures should use only `TEST_DATABASE_URL` and clean up temporary test data after each test.

Application services that create their own database connections and commit transactions should not be used with rollback-only fixtures unless they are explicitly configured for safe test isolation.
