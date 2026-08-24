from backend.database.sql_connection import create_connection
from backend.utils.helper import url_normalize
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def insert_enrichment(
    linkedin_url: str, raw_response: str, status: str, error_message: str = None
) -> dict:
    """
    Inserts a new enrichment record into the database.

    Args:
        linkedin_url: The LinkedIn URL of the person.
        raw_response: The raw response data from the enrichment provider.
        status: The status of the enrichment process (e.g., 'success', 'failure').
        error_message: Optional error message if the enrichment failed.

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
            INSERT INTO enrichments (linkedin_url, provider_name, raw_response, status, error_message)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                linkedin_url_normalized,
                "BRIGHTDATA",
                raw_response,
                status,
                error_message,
            ),
        )

        conn.commit()
        logger.info(
            f"Enrichment record inserted for linkedin_url: {linkedin_url_normalized}"
        )
        return {
            "status": "success",
            "message": "Enrichment record inserted successfully.",
        }
    except Exception as e:
        logger.error(f"Error inserting enrichment record: {e}")
        return {
            "status": "failure",
            "message": f"Error inserting enrichment record: {e}",
        }
    finally:
        if conn:
            conn.close()


def get_latest_enrichment_by_linkedin_url(linkedin_url: str) -> dict:
    """
    Get the latest enrichment record for a given linkedin_url.
    """
    try:
        linkedin_url_normalized = url_normalize(
            linkedin_url
        )  # Normalize the LinkedIn URL

        conn = create_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM enrichments
            WHERE linkedin_url = ?
            ORDER BY created_at DESC,  enrichment_id DESC
            LIMIT 1
        """,
            (linkedin_url_normalized,),
        )

        enrichment_data = cursor.fetchone()

        if enrichment_data is None:
            logger.info(
                f"No enrichment record found for linkedin_url: {linkedin_url_normalized}"
            )
            return {
                "status": "failure",
                "message": f"No enrichment record found for linkedin_url: {linkedin_url_normalized}",
            }

        enrichment_dict = {
            "enrichment_id": enrichment_data[0],
            "linkedin_url": enrichment_data[1],
            "provider_name": enrichment_data[2],
            "raw_response": enrichment_data[3],
            "status": enrichment_data[4],
            "error_message": enrichment_data[5],
            "created_at": enrichment_data[6],
        }

        return {
            "result": enrichment_dict,
            "status": "success",
            "message": "Latest enrichment record retrieved successfully.",
        }
    except Exception as e:
        logger.error(f"Error retrieving latest enrichment record: {e}")
        return {
            "status": "failure",
            "message": f"Error retrieving latest enrichment record: {e}",
        }
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    # Example usage
    linkedin_url = "https://www.linkedin.com/in/example"
    raw_response = '{"example": "data"}'
    status = "success"

    # Insert an enrichment record
    insert_result = insert_enrichment(linkedin_url, raw_response, status)
    print(insert_result)

    # Retrieve the latest enrichment record
    retrieve_result = get_latest_enrichment_by_linkedin_url(linkedin_url)
    print(retrieve_result)
