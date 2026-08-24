import os
from backend.database.sql_connection import create_connection, check_database_exists
from backend.database.schema import check_table_exists


def test_database_creation_and_connection(temp_db_file):
    """Test that the database is created, table exists, and connection is established."""
    assert check_database_exists(str(temp_db_file)) is True

    conn = create_connection()
    assert conn is not None
    conn.close()


def test_tables_created(temp_db_file):
    """Test that all required tables are created by default."""
    from backend.utils.config import load_config

    schema_path = os.getenv("SCHEMA", "backend/config/schema.yaml")
    schema = load_config(schema_path)

    # Assert that all tables defined in schema are present
    for table_name in schema.keys():
        assert check_table_exists(table_name) is True
