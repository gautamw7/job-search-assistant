import pytest

from backend.database.repository.provider_config import (
    insert_provider_config,
    get_provider_api_key,
    update_provider_config,
)


def test_provider_config_insert_and_get(temp_db_file):
    """Test inserting provider metadata and retrieving API key from keyring."""
    provider = "TEST_PROVIDER"
    cred_name = "TEST_API_KEY"
    api_key = "test_key_12345"

    # Insert provider config
    insert_provider_config(
        provider_name=provider,
        credential_name=cred_name,
        api_key=api_key,
        is_active=True,
    )

    # Verify metadata in SQLite
    import sqlite3

    conn = sqlite3.connect(str(temp_db_file))
    cursor = conn.cursor()
    cursor.execute(
        "SELECT provider_name, credential_name, is_active FROM provider_config WHERE credential_name = ?",
        (cred_name,),
    )
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == provider
    assert row[1] == cred_name
    assert row[2] == 1

    # Verify key retrieval via get_provider_api_key
    retrieved_key = get_provider_api_key(
        provider_name=provider,
        credential_name=cred_name,
    )
    assert retrieved_key == api_key


def test_provider_config_inactive(temp_db_file):
    """Test that retrieving an inactive provider raises an error."""
    provider = "INACTIVE_PROVIDER"
    cred_name = "INACTIVE_KEY"
    api_key = "inactive_key_999"

    insert_provider_config(
        provider_name=provider,
        credential_name=cred_name,
        api_key=api_key,
        is_active=False,
    )

    with pytest.raises(ValueError) as excinfo:
        get_provider_api_key(provider_name=provider, credential_name=cred_name)

    assert "is not active" in str(excinfo.value).lower()


def test_provider_config_not_found(temp_db_file):
    """Test retrieving a non-existent provider config raises an error."""
    with pytest.raises(ValueError) as excinfo:
        get_provider_api_key(provider_name="NON_EXISTENT", credential_name="NO_KEY")

    assert "not found" in str(excinfo.value).lower()


def test_update_provider_config(temp_db_file):
    """Test updating an existing provider config key."""
    provider = "UPDATE_PROVIDER"
    cred_name = "UPDATE_KEY"
    old_key = "old_secret_123"
    new_key = "new_secret_456"

    # Insert initial key
    insert_provider_config(
        provider_name=provider,
        credential_name=cred_name,
        api_key=old_key,
        is_active=True,
    )

    assert (
        get_provider_api_key(provider_name=provider, credential_name=cred_name)
        == old_key
    )

    # Update key
    update_provider_config(
        provider_name=provider,
        credential_name=cred_name,
        api_key=new_key,
    )

    assert (
        get_provider_api_key(provider_name=provider, credential_name=cred_name)
        == new_key
    )
