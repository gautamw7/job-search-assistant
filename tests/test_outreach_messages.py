from backend.database.repository.outreach_messages import (
    insert_outreach_message,
    get_latest_outreach_message_by_linkedin_url,
)


class TestOutreachMessagesRepository:
    def test_insert_outreach_message(self, temp_db_file):
        """Test inserting an outreach message."""
        linkedin_url = "https://www.linkedin.com/in/testuser"
        generated_text = "Hello, I came across your profile and would love to connect!"
        final_text = "Hello, I came across your profile and would love to connect! Let's discuss opportunities."
        user_context = "User is interested in collaboration."

        result = insert_outreach_message(
            linkedin_url, generated_text, final_text, user_context
        )
        assert result["status"] == "success"
        assert result["message"] == "Outreach message record inserted successfully."

    def test_insert_outreach_message_minimal(self, temp_db_file):
        """Test inserting an outreach message with only required fields."""
        linkedin_url = "https://www.linkedin.com/in/testuser"
        generated_text = "Hello, I came across your profile and would love to connect!"

        result = insert_outreach_message(linkedin_url, generated_text)
        assert result["status"] == "success"

    def test_get_latest_outreach_message(self, temp_db_file):
        """Test retrieving the latest outreach message for a LinkedIn URL."""
        linkedin_url = "https://www.linkedin.com/in/testuser"

        # Insert first message
        insert_outreach_message(
            linkedin_url,
            "First message text",
            "First final text",
            "Context 1",
        )

        # Insert second message (should be "latest")
        insert_outreach_message(
            linkedin_url,
            "Second message text",
            "Second final text",
            "Context 2",
        )

        result = get_latest_outreach_message_by_linkedin_url(linkedin_url)
        assert result["status"] == "success"
        # The second message should be the latest
        # Result structure: (message_id, linkedin_url, generated_text, final_text, user_context, generated_at, finalized_at)
        data = result["result"]

        assert data[1] == linkedin_url.lower()
        assert "Second message text" in data[2]  # generated_text column

    def test_get_latest_outreach_message_not_found(self, temp_db_file):
        """Test retrieving message for non-existent LinkedIn URL."""
        result = get_latest_outreach_message_by_linkedin_url(
            "https://www.linkedin.com/in/nonexistent"
        )
        assert result["status"] == "failure"
        assert "No outreach message record found" in result["message"]

    def test_url_normalization(self, temp_db_file):
        """Test that LinkedIn URLs are normalized (lowercase, trimmed)."""
        # Test with mixed case and trailing whitespace
        linkedin_url = "https://www.linkedin.com/in/TestUser  "
        generated_text = "Hello!"

        insert_outreach_message(linkedin_url, generated_text)

        result = get_latest_outreach_message_by_linkedin_url(linkedin_url)
        assert result["status"] == "success"

        # Verify the stored URL is normalized
        data = result["result"]
        assert data[1] == linkedin_url.strip().lower()
