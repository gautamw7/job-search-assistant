"""
Objective:
1. Establish a connection to the database.
2. If the database doesn't exist, create it.
"""

import os
import sqlite3
from sqlite3 import Error
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def check_database_exists(db_file: str) -> bool:
    """Check if the database file exists."""
    try:
        if os.path.exists(db_file):
            logger.info("Database file exists: %s", db_file)
            return True
        else:
            logger.info("Database file does not exist: %s", db_file)
            return False
    except Error as e:
        logger.error("Error checking database existence: %s", e)
        return False


def create_connection():
    """Create a database connection to the SQLite database specified by db_file."""
    conn = None
    try:
        db_file = os.getenv("DATABASE_FILE", "backend/data/example_database.db")
        conn = sqlite3.connect(db_file)
        logger.info("Successfully connected to the database: %s", db_file)
    except Error as e:
        logger.error("Error creating database connection: %s", e)
    return conn


if __name__ == "__main__":
    db_file = "backend/data/example_database.db"
    if not check_database_exists(db_file):
        logger.info("Database does not exist. Creating database: %s", db_file)
        from backend.database.schema import create_tables

        create_tables(db_file)
        conn = create_connection()

    logger.info("Database connection established successfully.")
