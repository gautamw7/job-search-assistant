from backend.database.sql_connection import create_connection
from backend.utils.logger import get_logger
from backend.utils.helper import url_normalize

logger = get_logger(__name__)


def insert_outreach_message(
    linkedin_url: str,
    generated_text: str,
    final_text: str = None,
    user_context: str = None,
) -> dict:
    """
    Inserts a new outreach message record into the database.

    Args:
        linkedin_url: The LinkedIn URL of the person.
        generated_text: The generated outreach message text.
        final_text: Optional finalized text if the user has edited it.
        user_context: Optional context provided by the user.

    Returns:
        A dictionary containing the result of the insertion operation.
    """
    try:
        linkedin_url_normalized = url_normalize(
            linkedin_url
        )  # Normalize the LinkedIn URL

        conn = create_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO outreach_messages (linkedin_url, generated_text, final_text, user_context)
            VALUES (?, ?, ?, ?)
        """,
            (linkedin_url_normalized, generated_text, final_text, user_context),
        )

        conn.commit()
        logger.info(
            f"Outreach message record inserted for linkedin_url: {linkedin_url_normalized}"
        )
        return {
            "status": "success",
            "message": "Outreach message record inserted successfully.",
        }
    except Exception as e:
        logger.error(f"Error inserting outreach message record: {e}")
        return {
            "status": "failure",
            "message": f"Error inserting outreach message record: {e}",
        }
    finally:
        if conn:
            conn.close()


def get_latest_outreach_message_by_linkedin_url(linkedin_url: str) -> dict:
    """
    Get the latest outreach message record for a given linkedin_url.
    """
    try:
        linkedin_url_normalized = url_normalize(
            linkedin_url
        )  # Normalize the LinkedIn URL

        conn = create_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM outreach_messages
            WHERE linkedin_url = ?
            ORDER BY
                CASE
                    WHEN finalized_at IS NOT NULL
                        AND finalized_at > generated_at
                    THEN finalized_at
                    ELSE generated_at
                END DESC,
                message_id DESC
            LIMIT 1
        """,
            (linkedin_url_normalized,),
        )

        outreach_message_data = cursor.fetchone()

        if outreach_message_data is None:
            logger.info(
                f"No outreach message record found for linkedin_url: {linkedin_url_normalized}"
            )
            return {"status": "failure", "message": "No outreach message record found."}

        logger.info(
            f"Latest outreach message record retrieved for linkedin_url: {linkedin_url_normalized}"
        )
        return {
            "result": outreach_message_data,
            "status": "success",
            "message": "Latest outreach message record retrieved successfully.",
        }
    except Exception as e:
        logger.error(f"Error retrieving latest outreach message record: {e}")
        return {
            "status": "failure",
            "message": f"Error retrieving latest outreach message record: {e}",
        }
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    # Example usage
    linkedin_url = "https://www.linkedin.com/in/example-profile/"
    generated_text = "Hello, I came across your profile and would love to connect!"
    final_text = "Hello, I came across your profile and would love to connect! Let's discuss potential opportunities."
    user_context = "User is interested in collaboration."

    # Insert a new outreach message
    insert_result = insert_outreach_message(
        linkedin_url, generated_text, final_text, user_context
    )
    print(insert_result)

    # Retrieve the latest outreach message for the given LinkedIn URL
    latest_message_result = get_latest_outreach_message_by_linkedin_url(linkedin_url)
    print(latest_message_result)
