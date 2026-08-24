import pytest
import pandas as pd
from pathlib import Path

from backend.database.repository.connections import (
    validate_csv_integrity,
    exclude_existing_connections,
    insert_connections_from_csv,
)


def test_validate_csv_integrity_missing_file():
    """Test that validating a non-existent CSV raises an error."""
    with pytest.raises(Exception) as excinfo:
        validate_csv_integrity("/nonexistent/path/to/connections.csv")
    assert "does not exist" in str(excinfo.value).lower()


def test_validate_csv_integrity_empty_csv():
    """Test that an empty CSV raises an error."""
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        # Write 3 dummy rows of LinkedIn export metadata before header
        f.write("Notes:\n")
        f.write("LinkedIn Export Metadata\n")
        f.write("\n")
        f.write("first name,last name,company,position,url\n")
        tmp_path = f.name
    try:
        with pytest.raises(Exception) as excinfo:
            validate_csv_integrity(tmp_path)
        assert (
            "no data" in str(excinfo.value).lower()
            or "empty" in str(excinfo.value).lower()
        )
    finally:
        Path(tmp_path).unlink()


def test_validate_csv_integrity_missing_url_column():
    """Test that CSV without required 'url' column raises an error."""
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        # Write 3 dummy rows of LinkedIn export metadata before header
        f.write("Notes:\n")
        f.write("LinkedIn Export Metadata\n")
        f.write("\n")
        f.write("first name,last name,company,position\n")
        f.write("John,Doe,Company,Engineer\n")
        tmp_path = f.name
    try:
        with pytest.raises(Exception) as excinfo:
            validate_csv_integrity(tmp_path)
        assert "missing required column" in str(excinfo.value).lower()
    finally:
        Path(tmp_path).unlink()


def test_validate_csv_integrity_valid_csv():
    """Test that a valid CSV with proper LinkedIn URLs passes validation."""
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        # Write 3 dummy rows of LinkedIn export metadata before header
        f.write("Notes:\n")
        f.write("LinkedIn Export Metadata\n")
        f.write("\n")
        f.write("first name,last name,company,position,url\n")
        f.write(
            "John,Doe,Acme Inc,Software Engineer,https://www.linkedin.com/in/johndoe\n"
        )
        f.write(
            "Jane,Smith,Globex Corp,Data Scientist,https://www.linkedin.com/in/janesmith\n"
        )
        tmp_path = f.name
    try:
        valid_df, issue_df = validate_csv_integrity(tmp_path)
        assert len(valid_df) == 2
        assert len(issue_df) == 0
        # Columns will include 'email address' only if it was in the CSV; our test CSV doesn't have it
        expected_cols = ["first name", "last name", "company", "position", "url"]
        for col in expected_cols:
            assert col in list(valid_df.columns), f"Missing column: {col}"
    finally:
        Path(tmp_path).unlink()


def test_validate_csv_integrity_invalid_urls():
    """Test that invalid LinkedIn URLs are caught as issues."""
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        # Write 3 dummy rows of LinkedIn export metadata before header
        f.write("Notes:\n")
        f.write("LinkedIn Export Metadata\n")
        f.write("\n")
        f.write("first name,last name,company,position,url\n")
        f.write("John,Doe,Acme Inc,Engineer,not-a-url\n")
        f.write(
            "Jane,Smith,Globex Corp,Scientist,https://www.linkedin.com/in/janesmith\n"
        )
        tmp_path = f.name
    try:
        valid_df, issue_df = validate_csv_integrity(tmp_path)
        assert len(valid_df) == 1  # Only Jane is valid
        assert len(issue_df) == 1
        assert "invalid linkedin url" in issue_df.iloc[0]["issue"].lower()
    finally:
        Path(tmp_path).unlink()


def test_validate_csv_integrity_duplicates():
    """Test that duplicate URLs are caught as issues."""
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        # Write 3 dummy rows of LinkedIn export metadata before header
        f.write("Notes:\n")
        f.write("LinkedIn Export Metadata\n")
        f.write("\n")
        f.write("first name,last name,company,position,url\n")
        f.write("John,Doe,Acme Inc,Engineer,https://www.linkedin.com/in/johndoe\n")
        f.write("Jane,Doe,Acme Inc,Manager,https://www.linkedin.com/in/johndoe\n")
        tmp_path = f.name
    try:
        valid_df, issue_df = validate_csv_integrity(tmp_path)
        assert len(valid_df) == 1  # First one kept
        assert len(issue_df) == 1
        assert "duplicate linkedin url" in issue_df.iloc[0]["issue"].lower()
    finally:
        Path(tmp_path).unlink()


def test_exclude_existing_connections(temp_db_file):
    """Test that existing connections are excluded from insertion."""
    import sqlite3

    # Pre-populate connections table
    conn = sqlite3.connect(str(temp_db_file))
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO connections (linkedin_url, first_name, last_name, company, position, is_enriched)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (
            "https://www.linkedin.com/in/existing",
            "Existing",
            "User",
            "OldCo",
            "OldRole",
            0,
        ),
    )
    conn.commit()
    conn.close()

    # Create a dataframe with one existing and one new
    df = pd.DataFrame(
        [
            {
                "url": "https://www.linkedin.com/in/existing",
                "first name": "Existing",
                "last name": "User",
                "company": "OldCo",
                "position": "OldRole",
            },
            {
                "url": "https://www.linkedin.com/in/newuser",
                "first name": "New",
                "last name": "User",
                "company": "NewCo",
                "position": "NewRole",
            },
        ]
    )

    filtered_df, dup_count = exclude_existing_connections(df)
    assert dup_count == 1
    assert len(filtered_df) == 1
    assert filtered_df.iloc[0]["url"] == "https://www.linkedin.com/in/newuser"


def test_insert_connections_from_csv_integration(temp_db_file):
    """Integration test: insert connections from CSV and verify in database."""
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        # Write 3 dummy rows of LinkedIn export metadata before header
        f.write("Notes:\n")
        f.write("LinkedIn Export Metadata\n")
        f.write("\n")
        f.write("first name,last name,company,position,url\n")
        f.write(
            "Alice,Johnson,TestCorp,Data Analyst,https://www.linkedin.com/in/alicejohnson\n"
        )
        f.write(
            "Bob,Williams,DemoInc,ML Engineer,https://www.linkedin.com/in/bobwilliams\n"
        )
        tmp_path = f.name
    try:
        result = insert_connections_from_csv(tmp_path)
        assert result["status"] == "success"
        assert result["inserted_count"] == 2
        assert result["duplicate_count"] == 0
        assert result["issue_count"] == 0

        # Verify in database
        import sqlite3

        conn = sqlite3.connect(str(temp_db_file))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM connections")
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 2
    finally:
        Path(tmp_path).unlink()


def test_insert_connections_from_csv_skips_existing(temp_db_file):
    """Test that re-importing same CSV does not duplicate."""
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        # Write 3 dummy rows of LinkedIn export metadata before header
        f.write("Notes:\n")
        f.write("LinkedIn Export Metadata\n")
        f.write("\n")
        f.write("first name,last name,company,position,url\n")
        f.write(
            "Alice,Johnson,TestCorp,Data Analyst,https://www.linkedin.com/in/alicejohnson\n"
        )
        tmp_path = f.name
    try:
        # First import
        result1 = insert_connections_from_csv(tmp_path)
        assert result1["inserted_count"] == 1

        # Second import
        result2 = insert_connections_from_csv(tmp_path)
        assert result2["inserted_count"] == 0
        assert result2["duplicate_count"] == 1
        assert result2["existing_connections_count"] == 1
    finally:
        Path(tmp_path).unlink()


def test_insert_real_connections_csv(temp_db_file):
    """Test importing the real connections.csv if it exists."""
    real_csv = "backend/data/connections.csv"
    if not Path(real_csv).exists():
        pytest.skip("Real connections.csv not found")

    result = insert_connections_from_csv(real_csv)
    assert result["status"] == "success"
    assert result["inserted_count"] >= 0  # Could be 0 if already imported
    # Note: we can't assert exact count because it may have been imported before
