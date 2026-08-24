from backend.database.sql_connection import create_connection
from backend.utils.logger import get_logger
from backend.utils.helper import url_normalize

logger = get_logger(__name__)


def retrieve_all_people():
    """
    Retrieves all persons from the database.

    Returns:
        A list of dictionaries containing information about all persons.
    """
    try:
        conn = create_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM people")
        rows = cursor.fetchall()

        # Convert rows to a list of dictionaries
        people_list = []
        for row in rows:
            person_dict = {
                "linkedin_url": row[0],
                "name": row[1],
                "headline": row[2],
                "company": row[3],
                "location": row[4],
                "about": row[5],
                "connected": row[6],
                "created_at": row[7],
            }
            people_list.append(person_dict)
        if not people_list:
            logger.info("No people found in the database.")
            return {
                "result": [],
                "status": "success",
                "message": "Query ran successfully. No people found in the database.",
            }

        return {
            "result": people_list,
            "status": "success",
            "message": "People retrieved successfully.",
        }
    except Exception as e:
        logger.error(f"Error retrieving all people: {e}")
        return {"status": "failure", "message": f"Error retrieving all people: {e}"}
    finally:
        if conn:
            conn.close()


def retrieve_data(linked_url: str):
    """
    Retrieves a person's information from the database using their LinkedIn URL.

    Args:
        linked_url: The LinkedIn URL of the person to be retrieved.
    """
    try:
        linked_url_normalized = url_normalize(linked_url)  # Normalize the LinkedIn URL

        conn = create_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM people WHERE linkedin_url = ?", (linked_url_normalized,)
        )
        person_data = cursor.fetchone()

        if not person_data:
            logger.info(f"No person found with LinkedIn URL: {linked_url_normalized}")
            return {
                "status": "failure",
                "message": f"No person found with LinkedIn URL: {linked_url_normalized}",
            }

        return {
            "result": person_data,
            "status": "success",
            "message": "Person retrieved successfully.",
        }

    except Exception as e:
        logger.error(f"Error retrieving person with LinkedIn URL {linked_url}: {e}")
        return {
            "status": "failure",
            "message": f"Error retrieving person with LinkedIn URL {linked_url}: {e}",
        }
    finally:
        if conn:
            conn.close()


def update_person(linked_url: str, details_to_update: dict):
    """
    Updates an existing person's information in the database.

    Args:
        linked_url: The LinkedIn URL of the person to be updated.
        details_to_update: A dictionary containing the details to be updated.
    """
    try:
        linked_url_normalized = url_normalize(linked_url)  # Normalize the LinkedIn URL

        conn = create_connection()
        cursor = conn.cursor()

        set_clause = ", ".join([f"{key} = ?" for key in details_to_update.keys()])
        values = list(details_to_update.values())

        values.append(
            linked_url_normalized
        )  # Add the LinkedIn URL to the end of the values list

        cursor.execute(f"UPDATE people SET {set_clause} WHERE linkedin_url = ?", values)
        if cursor.rowcount == 0:
            logger.info(
                f"No person found with LinkedIn URL: {linked_url_normalized}. Cannot update."
            )
            return {
                "status": "failure",
                "message": f"No person found with LinkedIn URL: {linked_url_normalized}. Cannot update.",
            }

        conn.commit()
        return {
            "status": "success",
            "message": f"Person with LinkedIn URL {linked_url_normalized} updated successfully.",
        }

    except Exception as e:
        logger.error(f"Error updating person with LinkedIn URL {linked_url}: {e}")
        return {
            "status": "failure",
            "message": f"Error updating person with LinkedIn URL {linked_url}: {e}",
        }

    finally:
        if conn:
            conn.close()


def delete_person(linkedin_url: str):
    """
    Deletes a person from the database using their LinkedIn URL.

    Args:
        conn: The database connection object.
        linkedin_url: The LinkedIn URL of the person to be deleted.
    """
    try:
        linkedin_url_normalized = url_normalize(
            linkedin_url
        )  # Normalize the LinkedIn URL

        conn = create_connection()
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM people WHERE linkedin_url = ?", (linkedin_url_normalized,)
        )

        if cursor.rowcount == 0:
            logger.info(
                f"No person found with LinkedIn URL: {linkedin_url_normalized}. Cannot delete."
            )
            return {
                "status": "failure",
                "message": f"No person found with LinkedIn URL: {linkedin_url_normalized}. Cannot delete.",
            }

        conn.commit()
        return {
            "status": "success",
            "message": f"Person with LinkedIn URL {linkedin_url_normalized} deleted successfully.",
        }

    except Exception as e:
        logger.error(f"Error deleting person with LinkedIn URL {linkedin_url}: {e}")
        return {
            "status": "failure",
            "message": f"Error deleting person with LinkedIn URL {linkedin_url}: {e}",
        }

    finally:
        if conn:
            conn.close()


def insert_person(linked_url: str):
    """
    Inserts a new person into the database.

    Args:
        conn: The database connection object.
    Returns:
        The ID of the newly inserted person.
    """
    conn = None
    try:
        linked_url_normalized = url_normalize(linked_url)  # Normalize the LinkedIn URL

        if retrieve_data(linked_url_normalized)["status"] == "success":
            logger.info(
                f"Person with LinkedIn URL {linked_url_normalized} already exists. Cannot insert."
            )
            return {
                "status": "failure",
                "message": f"Person with LinkedIn URL {linked_url_normalized} already exists. Cannot insert.",
            }

        conn = create_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO people (linkedin_url) VALUES (?)", (linked_url_normalized,)
        )
        conn.commit()
        return {
            "status": "success",
            "message": f"Person with LinkedIn URL {linked_url_normalized} inserted successfully.",
        }

    except Exception as e:
        logger.error(f"Error inserting person with LinkedIn URL {linked_url}: {e}")
        return {
            "status": "failure",
            "message": f"Error inserting person with LinkedIn URL {linked_url}: {e}",
        }

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    # Example usage
    linkedin_url = "https://www.linkedin.com/in/example-profile"
    insert_result = insert_person(linkedin_url)
    print(insert_result)
    conn = create_connection()
    cursor = conn.cursor()
    print(
        f"Current people in the database: {cursor.execute('SELECT * FROM people').fetchall()}"
    )

    retrieve_result = retrieve_data(linkedin_url)
    print(retrieve_result)

    update_result = update_person(
        linkedin_url, {"name": "Updated Name", "headline": "Updated Headline"}
    )
    print(update_result)
    print(
        f"Current people in the database after update: {cursor.execute('SELECT * FROM people').fetchall()}"
    )

    delete_result = delete_person(linkedin_url)
    print(delete_result)
    print(
        f"Current people in the database after deletion: {cursor.execute('SELECT * FROM people').fetchall()}"
    )
