from unittest.mock import patch, MagicMock
from backend.database.repository.api_status import (
    check_brightdata_api,
    check_gemini_health,
    get_latest_api_status,
    write_api_status_to_db,
    is_status_stale,
    get_api_health,
)


class TestAPIStatusRepository:
    def test_write_and_get_latest_api_status(self, temp_db_file):
        """Test writing and retrieving API status from database."""
        status_info = {
            "status": "healthy",
            "status_code": 200,
            "response_time_ms": 150.5,
            "error_message": None,
        }
        write_api_status_to_db({"BRIGHTDATA": status_info})

        # Retrieve the latest status
        latest = get_latest_api_status("BRIGHTDATA")
        assert latest is not None
        assert latest["provider_name"] == "BRIGHTDATA"
        assert latest["status"] == "healthy"
        assert latest["status_code"] == 200
        assert latest["response_time_ms"] == 150.5
        assert latest["error_message"] is None

    def test_get_latest_api_status_not_found(self, temp_db_file):
        """Test retrieving status for non-existent provider."""
        latest = get_latest_api_status("NONEXISTENT")
        assert latest is None

    def test_is_status_stale(self, temp_db_file):
        """Test checking if status is stale."""
        import time

        # Fresh status (timestamp = now)
        fresh_status = {"timestamp": time.time()}
        assert is_status_stale(fresh_status, max_age_minutes=60) is False

        # Stale status (timestamp = 2 hours ago)
        stale_status = {"timestamp": time.time() - 7200}  # 2 hours ago
        assert is_status_stale(stale_status, max_age_minutes=60) is True

        # Edge case: no timestamp
        assert is_status_stale({}, max_age_minutes=60) is True
        assert is_status_stale(None, max_age_minutes=60) is True

    @patch("backend.database.repository.api_status.get_provider_api_key")
    @patch("backend.database.repository.api_status.requests.post")
    @patch("backend.database.repository.api_status.requests.get")
    def test_check_brightdata_api_healthy(
        self, mock_get, mock_post, mock_get_key, temp_db_file
    ):
        """Test Bright Data API health check when healthy."""
        # Mock API key retrieval
        mock_get_key.return_value = "test_api_key"

        # Mock trigger response
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"snapshot_id": "test_snapshot_123"}
        mock_post.return_value = mock_post_response

        # Mock progress response
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"status": "ready"}
        mock_get.return_value = mock_get_response

        result = check_brightdata_api()
        assert result["status"] == "healthy"
        assert result["status_code"] == 200
        assert result["snapshot_id"] == "test_snapshot_123"
        assert result["error_message"] is None

    @patch("backend.database.repository.api_status.get_provider_api_key")
    @patch("backend.database.repository.api_status.requests.post")
    def test_check_brightdata_api_unhealthy_trigger_failed(
        self, mock_post, mock_get_key, temp_db_file
    ):
        """Test Bright Data API health check when trigger fails."""
        mock_get_key.return_value = "test_api_key"
        mock_post_response = MagicMock()
        mock_post_response.status_code = 401
        mock_post_response.text = "Unauthorized"
        mock_post.return_value = mock_post_response

        result = check_brightdata_api()
        assert result["status"] == "unhealthy"
        assert result["status_code"] == 401
        assert "Unauthorized" in result["error_message"]

    @patch("backend.database.repository.api_status.get_provider_api_key")
    @patch("backend.database.repository.api_status.requests.post")
    def test_check_brightdata_api_exception(
        self, mock_post, mock_get_key, temp_db_file
    ):
        """Test Bright Data API health check when request exception occurs."""
        import requests

        mock_get_key.return_value = "test_api_key"
        mock_post.side_effect = requests.exceptions.RequestException("Connection error")

        result = check_brightdata_api()
        assert result["status"] == "unhealthy"
        assert result["status_code"] is None
        assert "Connection error" in result["error_message"]

    @patch("backend.database.repository.api_status.get_provider_api_key")
    @patch("backend.database.repository.api_status.requests.get")
    def test_check_gemini_health(self, mock_get, mock_get_key, temp_db_file):
        """Test Gemini API health check."""
        mock_get_key.return_value = "test_api_key"
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get.return_value = mock_get_response

        result = check_gemini_health()
        assert result["status"] == "healthy"
        assert result["status_code"] == 200
        assert result["error_message"] is None

    @patch("backend.database.repository.api_status.get_provider_api_key")
    @patch("backend.database.repository.api_status.requests.get")
    def test_check_gemini_health_unhealthy(self, mock_get, mock_get_key, temp_db_file):
        """Test Gemini API health check when unhealthy."""
        mock_get_key.return_value = "test_api_key"
        mock_get_response = MagicMock()
        mock_get_response.status_code = 500
        mock_get_response.text = "Internal Server Error"
        mock_get.return_value = mock_get_response

        result = check_gemini_health()
        assert result["status"] == "unhealthy"
        assert result["status_code"] == 500
        assert "Internal Server Error" in result["error_message"]

    @patch("backend.database.repository.api_status.check_brightdata_api")
    @patch("backend.database.repository.api_status.check_gemini_health")
    @patch("backend.database.repository.api_status.get_latest_api_status")
    @patch("backend.database.repository.api_status.write_api_status_to_db")
    def test_get_api_health(
        self, mock_write, mock_get_latest, mock_gemini, mock_brightdata, temp_db_file
    ):
        """Test get_api_health orchestrates checks correctly."""
        # Mock latest status as None (first check)
        mock_get_latest.return_value = None
        mock_brightdata.return_value = {"status": "healthy", "provider": "Bright Data"}
        mock_gemini.return_value = {"status": "healthy", "provider": "Gemini"}

        result = get_api_health()
        assert "Bright Data" in result
        assert "Gemini" in result
        assert result["Bright Data"]["status"] == "healthy"
        assert result["Gemini"]["status"] == "healthy"
        # Should write to DB since we got new statuses
        mock_write.assert_called_once()

    @patch("backend.database.repository.api_status.get_latest_api_status")
    @patch("backend.database.repository.api_status.check_brightdata_api")
    @patch("backend.database.repository.api_status.check_gemini_health")
    def test_get_api_health_uses_cached_when_healthy_and_fresh(
        self, mock_gemini, mock_brightdata, mock_get_latest, temp_db_file
    ):
        """Test get_api_health uses cached status when healthy and fresh."""
        import time

        mock_get_latest.return_value = {
            "status": "healthy",
            "timestamp": time.time(),  # Fresh timestamp
        }

        result = get_api_health()
        # Should not call the check functions
        mock_brightdata.assert_not_called()
        mock_gemini.assert_not_called()
        assert result["Bright Data"]["status"] == "healthy"
