"""
Centralized configuration for the Glacier Daily Update system.

Uses a frozen dataclass to provide typed, validated access to all
environment-based settings. Modules should use ``get_settings()``
instead of reading ``os.environ`` directly.
"""

import dataclasses
import logging
import os

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclasses.dataclass(frozen=True)
class Settings:
    """All environment-based configuration for the Glacier Daily Update system.

    Required fields (no default) will cause ``ConfigError`` if missing
    from the environment when ``from_env()`` is called.
    """

    # --- Required: core API keys ---
    NPS: str
    DRIP_TOKEN: str
    DRIP_ACCOUNT: str
    FTP_USERNAME: str
    FTP_PASSWORD: str
    MAPBOX_TOKEN: str

    # --- Service keys (default "" — modules degrade gracefully) ---
    BC_TOKEN: str = ""
    BC_STORE_HASH: str = ""
    FLICKR_KEY: str = ""
    FLICKR_SECRET: str = ""
    GLACIERNPS_UID: str = ""
    SUNSETHUE_KEY: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    NOTICES_SPREADSHEET_ID: str = ""

    # --- Optional with meaningful defaults ---
    MAPBOX_ACCOUNT: str = "mapbox"
    MAPBOX_STYLE: str = "satellite-streets-v12"
    FTP_SERVER: str = "ftp.glacier.org"
    ENVIRONMENT: str = "development"
    DRIP_CAMPAIGN_ID: str = "169298893"

    # --- Optional: Cloudflare ---
    CACHE_PURGE: str = ""
    ZONE_ID: str = ""

    # --- Optional: Canary email verification ---
    CANARY_EMAIL: str = ""
    CANARY_IMAP_PASSWORD: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        """Build a ``Settings`` instance from ``os.environ``.

        This is a **pure** function — it only reads ``os.environ`` and
        never loads files.  Call ``get_settings()`` instead for the
        full workflow (load env file, then build Settings).

        For each field, the value is read from the environment variable
        with the same name. Fields that have a default in the dataclass
        use that default when the environment variable is unset or empty.

        Raises:
            ConfigError: If any required field (no default) is missing
                from the environment.
        """

        fields = dataclasses.fields(cls)
        kwargs: dict[str, str] = {}
        missing: list[str] = []

        for f in fields:
            env_val = os.environ.get(f.name)

            if f.default is not dataclasses.MISSING:
                # Optional field — use env value if non-empty, else default.
                # Empty strings in env files are treated as unset
                # so that the dataclass default is applied.
                if env_val:
                    kwargs[f.name] = env_val
                else:
                    kwargs[f.name] = f.default
            else:
                # Required field — must be present in env
                if env_val is None:
                    missing.append(f.name)
                else:
                    kwargs[f.name] = env_val

        if missing:
            raise ConfigError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        return cls(**kwargs)


# ---------------------------------------------------------------------------
# Singleton access
# ---------------------------------------------------------------------------

_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the application settings singleton.

    On the first call, loads ``config.env`` (machine-local config like
    ENVIRONMENT) and ``email.env`` (secrets, decrypted from
    ``email.enc.env`` on the Pi) and then constructs a ``Settings``
    from ``os.environ``.  Subsequent calls return the cached instance.

    ``load_dotenv`` uses ``override=False`` by default, so pre-existing
    env vars (e.g. those set by CI workflows or test fixtures) are
    never overwritten.
    """
    global _settings
    if _settings is None:
        try:
            from dotenv import load_dotenv

            load_dotenv("config.env")
            load_dotenv("email.env")
        except Exception:
            logger.debug("Could not load env files; relying on existing env vars")
        _settings = Settings.from_env()
    return _settings


def reset_settings() -> None:
    """Clear the cached settings so the next ``get_settings()`` re-reads
    from the environment.  Intended for use in tests."""
    global _settings
    _settings = None
