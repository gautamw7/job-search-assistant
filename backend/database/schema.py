import os
from backend.utils.logger import get_logger
from backend.utils.config import load_config
from backend.database.sql_connection import create_connection

logger = get_logger(__name__)


def check_table_exists(table_name: str) -> bool:
    """Check if a specific table exists in the database."""
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';"
        )
        return cursor.fetchone() is not None
    except Exception as e:
        logger.error("Error checking table existence: %s", e)
        return False
    finally:
        conn.close()


def create_tables():
    """Create tables in the database based on the provided schema."""
    try:
        conn = create_connection()
        cursor = conn.cursor()
        schema_path = os.getenv("SCHEMA", "backend/config/schema.yaml")
        schema = load_config(schema_path)
        logger.info("Loaded schema from %s", schema_path)

        tables_created = []
        for table_name, table_schema in schema.items():
            # Check if the table exists
            if not check_table_exists(table_name):
                columns = ", ".join(
                    [f"{col} {dtype}" for col, dtype in table_schema.items()]
                )
                create_table_sql = f"CREATE TABLE {table_name} ({columns});"

                cursor.execute(create_table_sql)
                tables_created.append(table_name)

                logger.info("Table created: %s", table_name)

        if tables_created:
            logger.info("Tables created successfully: %s", ", ".join(tables_created))

        else:
            logger.info("No new tables were created. All tables already exist.")

        conn.commit()
    except Exception as e:
        logger.error("Error creating tables: %s", e)
    finally:
        conn.close()


if __name__ == "__main__":
    db_file = "backend/data/example_database.db"
    from backend.database.sql_connection import create_connection
    from backend.utils.config import load_config

    create_tables()
