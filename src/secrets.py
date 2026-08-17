"""Secret Manager integration with Google Cloud Secret Manager and environment fallback."""

import os
import logging
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("fitforge.secrets")


class SecretManager:
    """
    Manages API keys and credentials with support for Google Cloud Secret Manager
    and transparent fallback to local environment variables and .env.
    """

    _cache: Dict[str, str] = {}

    @classmethod
    def get_secret(
        cls,
        secret_name: str,
        default: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Retrieve secret value from Secret Manager or environment variables.

        Args:
            secret_name: Name of secret (e.g. 'GEMINI_API_KEY', 'VERTEX_API_KEY').
            default: Default fallback value if not found.
            project_id: Optional GCP project ID for Cloud Secret Manager.

        Returns:
            Secret value as string or default.
        """
        # Check in-memory cache first
        if secret_name in cls._cache:
            return cls._cache[secret_name]

        # 1. Attempt Google Cloud Secret Manager if client is available and project is set
        gcp_project = project_id or os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
        if gcp_project:
            try:
                from google.cloud import secretmanager
                client = secretmanager.SecretManagerServiceClient()
                name = f"projects/{gcp_project}/secrets/{secret_name}/versions/latest"
                response = client.access_secret_version(request={"name": name})
                secret_val = response.payload.data.decode("UTF-8").strip()
                if secret_val:
                    cls._cache[secret_name] = secret_val
                    logger.info(f"Retrieved '{secret_name}' from GCP Secret Manager.")
                    return secret_val
            except ImportError:
                # google-cloud-secret-manager not installed, proceed to env fallback
                pass
            except Exception as e:
                logger.debug(f"Cloud Secret Manager lookup failed for '{secret_name}': {e}. Falling back to env.")

        # 2. Fallback to environment variables / .env
        env_val = os.getenv(secret_name)
        if env_val:
            cls._cache[secret_name] = env_val
            return env_val

        return default

    @classmethod
    def get_gemini_api_key(cls, default: Optional[str] = None) -> Optional[str]:
        """Convenience method to retrieve Gemini API key."""
        return cls.get_secret("GEMINI_API_KEY", default=default)

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the cached secrets."""
        cls._cache.clear()
