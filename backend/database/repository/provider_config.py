import keyring
from backend.database.sql_connection import create_connection
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def insert_provider_config(
    provider_name: str, credential_name: str, api_key: str, is_active: bool = True
):
    """
    Add a new provider configuration to the database.
    """
    try:
        conn = create_connection()
        cursor = conn.cursor()

        # Store the API key securely using keyring
        keyring.set_password(
            "JOB_SEARCH_ASSISTANT_KEYRING_SERVICE", credential_name, api_key
        )
        logger.info(
            "API_KEY for provider '%s' stored securely in keyring.", credential_name
        )

        # Insert the provider configuration into the database
        cursor.execute(
            "INSERT INTO provider_config (provider_name, credential_name, is_active) VALUES (?, ?, ?)",
            (provider_name, credential_name, int(is_active)),
        )
        logger.info(
            "Provider configuration for '%s' inserted into the database.", provider_name
        )
        conn.commit()
    except Exception as e:
        logger.error(
            "Error inserting provider configuration for '%s': %s", provider_name, e
        )
        raise ValueError(
            f"Error inserting provider configuration for '{provider_name}': {e}"
        )
    finally:
        conn.close()


def get_provider_api_key(provider_name: str, credential_name: str) -> str:
    """
    Retrieve the API_KEY for the given provider after checking if the provider is active in the database.
    If the provider is not active or the API_KEY is invalid, raise an appropriate exception.
    """
    try:
        conn = create_connection()
        cursor = conn.cursor()

        # Check if the provider is active in the database
        cursor.execute(
            "SELECT is_active FROM provider_config WHERE credential_name = ?",
            (credential_name,),
        )
        result = cursor.fetchone()

        if result is None:
            logger.info("Provider '%s' not found in the database.", credential_name)
            raise ValueError(f"Provider '{credential_name}' not found in the database.")

        is_active = result[0]
        if not is_active:
            logger.info("Provider '%s' is not active.", credential_name)
            raise ValueError(f"Provider '{credential_name}' is not active.")

        # Retrieve the API key securely using keyring
        api_key = keyring.get_password(
            "JOB_SEARCH_ASSISTANT_KEYRING_SERVICE", credential_name
        )
        if api_key is None:
            logger.error(
                "API_KEY for provider '%s' is invalid or not found.", credential_name
            )
            raise ValueError(
                f"API_KEY for provider '{credential_name}' is invalid or not found."
            )

        return api_key
    except Exception as e:
        logger.error(
            "Error retrieving API_KEY for provider '%s': %s", credential_name, e
        )
        raise
    finally:
        conn.close()


def update_provider_config(provider_name: str, credential_name: str, api_key: str):
    """
    Update an existing provider configuration in the database.
    """
    try:
        conn = create_connection()
        cursor = conn.cursor()

        # Update the API key securely using keyring
        keyring.set_password(
            "JOB_SEARCH_ASSISTANT_KEYRING_SERVICE", credential_name, api_key
        )
        logger.info(
            "API_KEY for provider '%s' updated securely in keyring.", credential_name
        )

        # Update the provider configuration in the database.
        cursor.execute(
            "UPDATE provider_config SET updated_at = CURRENT_TIMESTAMP WHERE provider_name = ? AND credential_name = ?",
            (provider_name, credential_name),
        )
        logger.info(
            "Provider configuration for '%s' updated in the database.", provider_name
        )
        conn.commit()
    except Exception as e:
        logger.error(
            "Error updating provider configuration for '%s': %s", provider_name, e
        )
        raise ValueError(
            f"Error updating provider configuration for '{provider_name}': {e}"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    sql_db = "backend/data/example_database.db"
    from backend.database.sql_connection import check_database_exists

    if not check_database_exists(sql_db):
        from backend.database.schema import create_tables

        create_tables()  # Create the tables if they don't exist

    # Example usage
    try:
        import os

        logger.info("TESTING PROVIDER CONFIG")
        os.environ["BRIGHTDATA_API_KEY"] = "9548f5eb-6524-48b7-97de-b090df63cd85"
        insert_provider_config(
            provider_name="GOOGLE",
            credential_name="GEMINI_API_KEY",
            api_key=os.getenv("GEMINI_API_KEY"),
        )
        insert_provider_config(
            provider_name="BRIGHTDATA",
            credential_name="BRIGHTDATA_API_KEY",
            api_key=os.getenv("BRIGHTDATA_API_KEY"),
        )

        if get_provider_api_key(
            provider_name="GOOGLE", credential_name="GEMINI_API_KEY"
        ):
            print(
                f"Crendential for: 'GEMINI_API_KEY' by provider 'GOOGLE' inserted successfully are {get_provider_api_key(provider_name='GOOGLE', credential_name='GEMINI_API_KEY')}"
            )

        if get_provider_api_key(
            provider_name="BRIGHTDATA", credential_name="BRIGHTDATA_API_KEY"
        ):
            print(
                f"Credential for: 'BRIGHTDATA_API_KEY' by provider 'BRIGHTDATA' inserted successfully are {get_provider_api_key(provider_name='BRIGHTDATA', credential_name='BRIGHTDATA_API_KEY')}"
            )

    except ValueError:
        logger.error("Error: {ve}")
