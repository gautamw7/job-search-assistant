from pathlib import Path
from yaml import safe_load as yaml_safe_load


def test_schema_yaml_loads_successfully():
    """Test that the schema YAML file can be loaded and has the expected structure."""
    schema_path = Path("backend/config/schema.yaml")
    assert schema_path.exists(), f"Schema file not found at {schema_path}"

    with open(schema_path) as f:
        schema = yaml_safe_load(f)

    expected_tables = [
        "user_profile",
        "provider_config",
        "connections",
        "people",
        "enrichments",
        "outreach_messages",
        "api_status",
    ]

    for table in expected_tables:
        assert table in schema, f"Table '{table}' not found in schema"

    # Verify user_profile has required columns
    up_schema = schema["user_profile"]
    assert "personality_markdown" in up_schema
    assert "resume_markdown" in up_schema

    # Verify people table has linkedin_url as primary key concept
    people_schema = schema["people"]
    assert "linkedin_url" in people_schema

    # Verify connections table
    conn_schema = schema["connections"]
    assert "linkedin_url" in conn_schema
    assert "is_enriched" in conn_schema


def test_schema_column_types(temp_db_file):
    """Test that column types are valid SQLite types."""
    from backend.utils.config import load_config

    schema_path = "backend/config/schema.yaml"
    schema = load_config(schema_path)

    for table_name, columns in schema.items():
        for col_name, col_def in columns.items():
            # The column definition is a string like "TEXT NOT NULL" or just "TEXT"
            # We check if it contains valid type keywords
            col_def_upper = (
                col_def.upper() if isinstance(col_def, str) else str(col_def).upper()
            )
            found = False
            for keyword in ["TEXT", "INTEGER", "REAL", "TIMESTAMP", "BOOLEAN"]:
                if keyword in col_def_upper:
                    found = True
                    break
            assert found, (
                f"Column '{col_name}' in table '{table_name}' has invalid type: {col_def}"
            )
            # Check it doesn't contain invalid types
            invalid = {"VARCHAR", "CHAR", "BLOB", "NUMERIC", "DECIMAL"}
            for inv in invalid:
                assert inv.upper() not in col_def_upper, (
                    f"Invalid column type '{inv}' used in {table_name}.{col_name}"
                )
