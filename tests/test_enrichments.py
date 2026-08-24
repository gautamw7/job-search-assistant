from backend.database.repository.enrichments import (
    insert_enrichment,
    get_latest_enrichment_by_linkedin_url,
)


class TestEnrichmentsRepository:
    def test_insert_enrichment(self, temp_db_file):
        """Test inserting an enrichment record."""
        linkedin_url = "https://www.linkedin.com/in/testuser"
        raw_response = '{"name": "Test User", "headline": "Software Engineer"}'
        status = "success"
        error_message = None

        result = insert_enrichment(linkedin_url, raw_response, status, error_message)
        assert result["status"] == "success"
        assert result["message"] == "Enrichment record inserted successfully."

    def test_insert_enrichment_with_error(self, temp_db_file):
        """Test inserting an enrichment record with error."""
        linkedin_url = "https://www.linkedin.com/in/testuser"
        raw_response = ""
        status = "failure"
        error_message = "API timeout"

        result = insert_enrichment(linkedin_url, raw_response, status, error_message)
        assert result["status"] == "success"

    def test_get_latest_enrichment(self, temp_db_file):
        """Test retrieving the latest enrichment record for a LinkedIn URL."""
        linkedin_url = "https://www.linkedin.com/in/testuser"

        # Insert first enrichment
        insert_enrichment(
            linkedin_url,
            '{"name": "Test User", "headline": "Junior Engineer"}',
            "success",
            None,
        )

        # Insert second enrichment (should be "latest")
        insert_enrichment(
            linkedin_url,
            '{"name": "Test User", "headline": "Senior Engineer"}',
            "success",
            None,
        )

        result = get_latest_enrichment_by_linkedin_url(linkedin_url)

        assert result["status"] == "success"

        data = result["result"]

        assert data["linkedin_url"] == linkedin_url.lower()
        assert "Senior Engineer" in data["raw_response"]
        assert data["status"] == "success"

    def test_get_latest_enrichment_not_found(self, temp_db_file):
        """Test retrieving enrichment for non-existent LinkedIn URL."""
        result = get_latest_enrichment_by_linkedin_url(
            "https://www.linkedin.com/in/nonexistent"
        )
        assert result["status"] == "failure"
        assert "No enrichment record found" in result["message"]

    def test_url_normalization(self, temp_db_file):
        """Test that LinkedIn URLs are normalized (lowercase, trimmed)."""
        linkedin_url = "https://www.linkedin.com/in/TestUser  "
        raw_response = '{"test": "data"}'
        status = "success"

        insert_enrichment(linkedin_url, raw_response, status)

        result = get_latest_enrichment_by_linkedin_url(linkedin_url)
        assert result["status"] == "success"

        # Verify the stored URL is normalized
        data = result["result"]
        assert data["linkedin_url"] == linkedin_url.strip().lower()

    def test_multiple_urls_separate_records(self, temp_db_file):
        """Test that enrichments for different URLs are stored separately."""
        urls = [
            "https://www.linkedin.com/in/user1",
            "https://www.linkedin.com/in/user2",
            "https://www.linkedin.com/in/user3",
        ]

        for i, url in enumerate(urls):
            insert_enrichment(url, f'{{"data": "{i}"}}', "success", None)

        for i, url in enumerate(urls):
            result = get_latest_enrichment_by_linkedin_url(url)

            assert result["status"] == "success"

            data = result["result"]

            assert f'"data": "{i}"' in data["raw_response"]
