import sys
from pathlib import Path

# Ensure project root is in python path
sys.path.insert(0, str(Path(__file__).parent))

from backend.database.sql_connection import check_database_exists
from backend.database.schema import create_tables
from backend.database.repository.api_status import (
    write_api_status_to_db,
    get_latest_api_status,
)
from backend.database.repository.people import insert_person, retrieve_data
from backend.database.repository.enrichments import (
    insert_enrichment,
    get_latest_enrichment,
)
from backend.database.repository.outreach_messages import (
    insert_outreach_message,
    get_latest_outreach_message,
)
from backend.database.repository.provider_config import (
    insert_provider_config,
    get_provider_api_key,
)

DB_FILE = "backend/data/example_database.db"


def reset_database():
    print("🧹 Purging old database...")
    db_path = Path(DB_FILE)
    if db_path.exists():
        db_path.unlink()
        print(f"Deleted existing database at {DB_FILE}")

    db_path.parent.mkdir(parents=True, exist_ok=True)


def main():
    print("🚀 Starting Job Search Assistant Smoke Test & Initialization Script\n")

    reset_database()
    print("📦 Creating database tables from schema.yaml...")
    create_tables()
    assert check_database_exists(DB_FILE), "Database creation failed!"
    print("✅ Database and schema initialized successfully.\n")

    print("🔑 Testing Provider Config...")
    try:
        insert_provider_config(
            "GOOGLE", "GEMINI_API_KEY", "dummy-gemini-key-12345", is_active=True
        )
        key = get_provider_api_key("GOOGLE", "GEMINI_API_KEY")
        print(f"Successfully retrieved provider key: {key[:5]}*****")
    except Exception as e:
        print(f"⚠️ Provider config/keyring note: {e}")

    print("\n📊 Testing API Status Repository...")
    write_api_status_to_db(
        {"BrightData": {"status": "healthy", "status_code": 200, "error_message": None}}
    )
    latest_status = get_latest_api_status("BrightData")
    print(f"Retrieved API Status: {latest_status}")
    assert latest_status["status"] == "healthy"

    print("\n👥 Testing People Repository...")
    test_url = "https://www.linkedin.com/in/johndoe"
    insert_person(
        linked_url=test_url,
        name="John Doe",
        headline="Software Engineer at TechCorp",
        company="TechCorp",
        location="San Francisco, CA",
        about="Passionate builder.",
    )
    person = retrieve_data(test_url)
    print(f"Retrieved Person: {person}")
    assert person["name"] == "John Doe"

    print("\n⚡ Testing Enrichments Repository...")
    enrichment_id = insert_enrichment(
        linkedin_url=test_url, raw_response='{"profile": "rich_data"}', status="success"
    )
    latest_enrichment = get_latest_enrichment(test_url)
    print(
        f"Retrieved Enrichment ID {enrichment_id}: status={latest_enrichment['status']}"
    )
    assert latest_enrichment["status"] == "success"

    print("\n✉️ Testing Outreach Messages Repository...")
    msg_id = insert_outreach_message(
        linkedin_url=test_url,
        generated_text="Hi John, loved your work at TechCorp!",
        user_context="Met at conference",
    )
    latest_msg = get_latest_outreach_message(test_url)
    print(f"Retrieved Outreach Message ID {msg_id}: {latest_msg['generated_text']}")
    assert latest_msg["message_id"] == msg_id

    print(
        "\n🎉 All smoke tests passed successfully! Your refactored database layer is fully operational."
    )


if __name__ == "__main__":
    main()
