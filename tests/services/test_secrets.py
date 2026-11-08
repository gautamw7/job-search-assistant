from unittest.mock import patch

from app.services import secrets


def test_key_goes_to_keyring_only_when_keyring_works(tmp_path):
    with (
        patch.object(secrets, "SECRETS_FILE", tmp_path / "secrets.json"),
        patch("app.services.secrets.keyring.set_password") as kr,
    ):
        secrets.set_secure_key("gemini", "k" * 12)
    kr.assert_called_once()
    assert not (tmp_path / "secrets.json").exists()  # no plaintext copy


def test_file_fallback_only_when_keyring_fails(tmp_path):
    path = tmp_path / "secrets.json"
    with (
        patch.object(secrets, "SECRETS_FILE", path),
        patch("app.services.secrets.keyring.set_password", side_effect=RuntimeError),
    ):
        secrets.set_secure_key("gemini", "k" * 12)
    assert path.exists()
