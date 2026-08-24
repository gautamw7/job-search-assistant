import os
import tempfile
import shutil
from pathlib import Path

import pytest

# We need to set the DATABASE_FILE environment variable before importing the modules
# that use it, because they read it at module level or function call time.
# However, we can set it in the fixture and then reload the modules if necessary.
# For simplicity, we will set the environment variable and then import the modules
# in the test functions after the fixture has set it.

# Alternatively, we can have the fixture return the path and let the test set it.
# But note that the module-level code in sql_connection.py uses os.getenv at import time.
# To avoid that, we can set the environment variable before importing the modules in the test.

# Since we are using pytest, we can use an autouse fixture that sets the environment variable
# before each test and then tears it down.

# However, note that some modules might have already been imported by the time the fixture runs.
# To be safe, we will set the environment variable in the fixture and then reload the modules
# that depend on it. But for simplicity, let's assume we set the environment variable before
# importing the modules in the test functions.

# We'll create a fixture that gives a temporary database file path and sets the environment variable.


@pytest.fixture
def temp_db_file():
    """Create a temporary database file and set the DATABASE_FILE environment variable."""
    # Create a temporary directory
    tmp_dir = tempfile.mkdtemp()
    db_file = Path(tmp_dir) / "test_database.db"

    # Set the environment variable
    old_db_file = os.environ.get("DATABASE_FILE")
    os.environ["DATABASE_FILE"] = str(db_file)

    # Create the tables by calling create_tables
    from backend.database.schema import create_tables

    create_tables()

    yield db_file

    # Teardown: remove the temporary directory and restore the environment variable
    shutil.rmtree(tmp_dir)
    if old_db_file is not None:
        os.environ["DATABASE_FILE"] = old_db_file
    else:
        # If it wasn't set, remove it
        os.environ.pop("DATABASE_FILE", None)


# Another fixture that gives a database connection
@pytest.fixture
def db_connection(temp_db_file):
    """Return a database connection to the temporary database."""
    from backend.database.sql_connection import create_connection

    conn = create_connection()
    yield conn
    conn.close()
