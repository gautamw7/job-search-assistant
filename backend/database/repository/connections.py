import os
import pandas as pd

from backend.database.sql_connection import create_connection
from backend.utils.logger import get_logger

logger = get_logger(__name__)

REQUIRED_COLUMN = "url"


def create_issue(dataframe: pd.DataFrame, index: int, issue: str) -> dict:
    return {
        "row": index + 5,
        "name": f"{dataframe.loc[index, 'first name']} {dataframe.loc[index, 'last name']}",
        "company": dataframe.loc[index, "company"],
        "position": dataframe.loc[index, "position"],
        "url": dataframe.loc[index, "url"],
        "issue": issue,
    }


def validate_csv_integrity(csv_file_path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    try:
        if not os.path.isfile(csv_file_path):
            raise ValueError(f"CSV file does not exist: {csv_file_path}")

        if not csv_file_path.lower().endswith(".csv"):
            raise ValueError(f"File is not a CSV file: {csv_file_path}")

        try:
            dataframe = pd.read_csv(csv_file_path, skiprows=3)
        except Exception as e:
            raise ValueError(f"Unable to read CSV file: {e}") from e

        dataframe.columns = dataframe.columns.str.strip().str.lower()

        if REQUIRED_COLUMN not in dataframe.columns:
            raise ValueError(f"Missing required column: {REQUIRED_COLUMN}")

        if dataframe.empty:
            raise ValueError("CSV file contains no data.")

        dataframe[REQUIRED_COLUMN] = (
            dataframe[REQUIRED_COLUMN].astype("string").str.strip().str.lower()
        )

        issues = []

        null_urls = dataframe[REQUIRED_COLUMN].isna()
        for index in dataframe[null_urls].index:
            issues.append(create_issue(dataframe, index, "Missing LinkedIn URL"))

        empty_urls = dataframe[REQUIRED_COLUMN].fillna("").eq("")
        for index in dataframe[empty_urls].index:
            if not null_urls[index]:
                issues.append(create_issue(dataframe, index, "Empty LinkedIn URL"))

        invalid_url_mask = (
            ~dataframe[REQUIRED_COLUMN]
            .fillna("")
            .str.startswith(
                "https://www.linkedin.com/in/",
                na=False,
            )
            & ~null_urls
            & ~empty_urls
        )
        for index in dataframe[invalid_url_mask].index:
            issues.append(create_issue(dataframe, index, "Invalid LinkedIn URL"))

        duplicate_mask = dataframe[REQUIRED_COLUMN].duplicated(keep="first")
        duplicate_mask &= ~null_urls
        duplicate_mask &= ~empty_urls
        for index in dataframe[duplicate_mask].index:
            issues.append(create_issue(dataframe, index, "Duplicate LinkedIn URL"))

        issue_dataframe = pd.DataFrame(
            issues,
            columns=["row", "url", "issue"],
        )

        invalid_row_mask = null_urls | empty_urls | invalid_url_mask | duplicate_mask

        valid_dataframe = dataframe[~invalid_row_mask].copy()

        if "email address" in valid_dataframe.columns:
            valid_dataframe["email address"] = (
                valid_dataframe["email address"]
                .astype("string")
                .str.strip()
                .str.lower()
            )

        return valid_dataframe, issue_dataframe

    except ValueError:
        raise

    except Exception as e:
        logger.error("Error validating CSV file: %s", e)
        raise ValueError(f"Error validating CSV file: {e}") from e


def get_existing_urls(table_name: str) -> set[str]:
    conn = None

    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT linkedin_url FROM {table_name}")

        return {row[0].strip().lower() for row in cursor.fetchall() if row[0]}

    except Exception as e:
        logger.error("Error retrieving URLs from '%s': %s", table_name, e)
        raise

    finally:
        if conn:
            conn.close()


def exclude_existing_connections(connections: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    existing_urls = get_existing_urls("connections")
    mask = connections["url"].isin(existing_urls)
    duplicate_count = int(mask.sum())

    return connections[~mask].copy(), duplicate_count


def exclude_existing_people(connections: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    existing_urls = get_existing_urls("people")
    mask = connections["url"].isin(existing_urls)
    existing_people_count = int(mask.sum())

    return connections[~mask].copy(), existing_people_count


def insert_connections_from_csv(csv_file_path: str) -> dict:
    conn = None

    try:
        dataframe, issue_dataframe = validate_csv_integrity(csv_file_path)

        rows_read = len(dataframe) + len(issue_dataframe)

        dataframe, existing_people_count = exclude_existing_people(dataframe)
        dataframe, existing_connections_count = exclude_existing_connections(dataframe)

        duplicate_count = existing_people_count + existing_connections_count

        if dataframe.empty:
            logger.info("No new connections to insert.")

            return {
                "status": "success",
                "rows_read": rows_read,
                "inserted_count": 0,
                "duplicate_count": duplicate_count,
                "existing_people_count": existing_people_count,
                "existing_connections_count": existing_connections_count,
                "issue_count": len(issue_dataframe),
                "issues": issue_dataframe,
                "message": "No new connections to insert.",
            }

        conn = create_connection()
        cursor = conn.cursor()

        for _, row in dataframe.iterrows():
            cursor.execute(
                """
                INSERT INTO connections (
                    linkedin_url,
                    first_name,
                    last_name,
                    company,
                    position,
                    email,
                    is_enriched
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["url"],
                    row.get("first name", ""),
                    row.get("last name", ""),
                    row.get("company", ""),
                    row.get("position", ""),
                    row.get("email address", ""),
                    0,
                ),
            )

        inserted_count = len(dataframe)
        conn.commit()

        logger.info("Successfully inserted %d connections.", inserted_count)

        return {
            "status": "success",
            "rows_read": rows_read,
            "inserted_count": inserted_count,
            "duplicate_count": duplicate_count,
            "existing_people_count": existing_people_count,
            "existing_connections_count": existing_connections_count,
            "issue_count": len(issue_dataframe),
            "issues": issue_dataframe,
            "message": "Connections imported successfully.",
        }

    except ValueError:
        raise

    except Exception as e:
        if conn:
            conn.rollback()

        logger.error("Error importing connections: %s", e)
        raise

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    csv_file_path = "backend/data/connections.csv"
    result = insert_connections_from_csv(csv_file_path)
    logger.info("Import result: %s", result)

    url_issues = [
        "Missing LinkedIn URL",
        "Empty LinkedIn URL",
        "Invalid LinkedIn URL",
        "Duplicate LinkedIn URL",
    ]
    if result["issue_count"] > 0 and any(
        issue in url_issues for issue in result["issues"]["issue"].unique()
    ):
        logger.info(
            "CRITICAL: Following rows have missing LinkedIn URLs and will not be imported into the database:"
        )
        for _, row in result["issues"].iterrows():
            if row["issue"] == "Missing LinkedIn URL":
                logger.warning(
                    "Row %s: URL='%s', Issue='%s'",
                    row["row"],
                    row["url"],
                    row["issue"],
                )
