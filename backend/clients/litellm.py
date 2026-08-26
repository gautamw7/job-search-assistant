from time import perf_counter
import litellm
import requests

from backend.utils.logger import get_logger
from backend.database.repository.provider_config import get_provider_api_key
from backend.workflows.prompts import orchestrate_regeneration_prompt

logger = get_logger(__name__)


class LiteLLMClient:
    """
    LiteLLMClient is a client for interacting with LLMs via LiteLLM.
    """

    def __init__(self):
        """
        Initialize the LiteLLMClient with the secure API key.
        """
        self._api_key = get_provider_api_key(
            provider_name="GEMINI", credential_name="GEMINI_API_KEY"
        )
        self._health_check_url = "https://api.gemini.com/v1/pubticker/btcusd"
        self._header = {"Authorization": f"Bearer {self._api_key}"}

        logger.info("LiteLLMClient initialized with secure API key.")

    def check_health(self) -> dict:
        """
        Check the health status of the Gemini API.
        Returns:
            dict: A dictionary containing the health status information.
        """
        try:
            response = requests.get(
                self._health_check_url, headers=self._header, timeout=10
            )
            is_healthy = "healthy" if response.status_code == 200 else "unhealthy"
            return {
                "status": is_healthy,
                "status_code": response.status_code,
                "error_message": response.text if response.status_code != 200 else None,
            }
        except requests.exceptions.RequestException as exc:
            logger.error("Error checking Gemini health: %s", exc)
            return {
                "status": "unhealthy",
                "status_code": None,
                "error_message": "Error checking Gemini health. Exception: " + str(exc),
            }

    def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "gemini/gemini-2.5-flash",
    ) -> str:
        """
        Generates text using LiteLLM with system and user prompts.
        """
        start_time = perf_counter()
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            response = litellm.completion(
                model=model, messages=messages, api_key=self._api_key
            )
            duration_ms = (perf_counter() - start_time) * 1000
            logger.info(f"LLM Response generated in {duration_ms:.2f}ms using {model}")
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error in LLM generation: {e}")
            raise RuntimeError(f"Error in LLM generation: {e}")

    def regenerate_response(
        self, linkedin_url: str, user_note: str, message_personalization: dict
    ) -> str:
        """
        Regenerate the outreach message for a given LinkedIn URL based on the provided user note.
        """
        logger.info("Regenerating outreach message for LinkedIn URL: %s", linkedin_url)
        # This will raise exceptions if resources/prompts can't be fetched or built
        prompt_data = orchestrate_regeneration_prompt(
            linkedin_url, user_note, message_personalization
        )

        system_prompt = prompt_data.get("system_prompt", "")
        user_prompt = prompt_data.get("user_prompt", "")

        return self.generate_response(
            system_prompt=system_prompt, user_prompt=user_prompt
        )
