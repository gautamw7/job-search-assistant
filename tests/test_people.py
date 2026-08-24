from backend.database.repository.people import (
    retrieve_all_people,
    retrieve_data,
    update_person,
    delete_person,
    insert_person,
)


class TestPeopleRepository:
    def test_insert_and_retrieve_person(self, temp_db_file):
        """Test inserting a person and retrieving by LinkedIn URL."""
        linkedin_url = "https://www.linkedin.com/in/testuser"

        # Insert person
        insert_result = insert_person(linkedin_url)
        assert insert_result["status"] == "success"
        assert "inserted successfully" in insert_result["message"]

        # Retrieve person
        retrieve_result = retrieve_data(linkedin_url)
        assert retrieve_result["status"] == "success"
        assert (
            retrieve_result["result"][0] == linkedin_url.lower()
        )  # linkedin_url is first column

    def test_insert_duplicate_person_fails(self, temp_db_file):
        """Test that inserting the same person twice fails."""
        linkedin_url = "https://www.linkedin.com/in/testuser"

        # First insert
        insert_result1 = insert_person(linkedin_url)
        assert insert_result1["status"] == "success"

        # Second insert should fail
        insert_result2 = insert_person(linkedin_url)
        assert insert_result2["status"] == "failure"
        assert "already exists" in insert_result2["message"]

    def test_retrieve_nonexistent_person(self, temp_db_file):
        """Test retrieving a person that doesn't exist."""
        retrieve_result = retrieve_data("https://www.linkedin.com/in/nonexistent")
        assert retrieve_result["status"] == "failure"
        assert "No person found" in retrieve_result["message"]

    def test_update_person(self, temp_db_file):
        """Test updating a person's details."""
        linkedin_url = "https://www.linkedin.com/in/testuser"
        insert_person(linkedin_url)  # Insert first

        # Update person
        update_result = update_person(
            linkedin_url,
            {"name": "Test User", "headline": "Software Engineer"},
        )
        assert update_result["status"] == "success"
        assert "updated successfully" in update_result["message"]

    def test_update_nonexistent_person(self, temp_db_file):
        """Test updating a person that doesn't exist."""
        update_result = update_person(
            "https://www.linkedin.com/in/nonexistent",
            {"name": "Test User"},
        )
        assert update_result["status"] == "failure"
        assert "No person found" in update_result["message"]

    def test_delete_person(self, temp_db_file):
        """Test deleting a person."""
        linkedin_url = "https://www.linkedin.com/in/testuser"
        insert_person(linkedin_url)  # Insert first

        # Delete person
        delete_result = delete_person(linkedin_url)
        assert delete_result["status"] == "success"
        assert "deleted successfully" in delete_result["message"]

        # Verify it's gone
        retrieve_result = retrieve_data(linkedin_url)
        assert retrieve_result["status"] == "failure"

    def test_delete_nonexistent_person(self, temp_db_file):
        """Test deleting a person that doesn't exist."""
        delete_result = delete_person("https://www.linkedin.com/in/nonexistent")
        assert delete_result["status"] == "failure"
        assert "No person found" in delete_result["message"]

    def test_retrieve_all_people_empty(self, temp_db_file):
        """Test retrieving all people when table is empty."""
        all_people = retrieve_all_people()
        assert all_people["status"] == "success"
        assert all_people["result"] == []

    def test_retrieve_all_people_with_data(self, temp_db_file):
        """Test retrieving all people when table has data."""
        urls = [
            "https://www.linkedin.com/in/user1",
            "https://www.linkedin.com/in/user2",
            "https://www.linkedin.com/in/user3",
        ]
        for url in urls:
            insert_result = insert_person(url)
            assert insert_result["status"] == "success"

        all_people = retrieve_all_people()
        assert all_people["status"] == "success"
        assert len(all_people["result"]) == 3
        # Check that all URLs are in the result (normalized to lowercase)
        returned_urls = [person["linkedin_url"] for person in all_people["result"]]
        for url in urls:
            assert url.lower() in returned_urls
