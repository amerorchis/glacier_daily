"""Tests for the centralized Settings dataclass."""

import pytest

from shared.settings import ConfigError, Settings, get_settings, reset_settings

# All required fields for a valid Settings
REQUIRED_ENV = {
    "NPS": "test_nps",
    "DRIP_TOKEN": "test_drip",
    "DRIP_ACCOUNT": "test_account",
    "FTP_USERNAME": "test_ftp_user",
    "FTP_PASSWORD": "test_ftp_pass",
    "MAPBOX_TOKEN": "test_mapbox",
}


class TestSettingsFromEnv:
    """Tests for Settings.from_env()."""

    def test_all_required_present(self, monkeypatch):
        for key, val in REQUIRED_ENV.items():
            monkeypatch.setenv(key, val)

        s = Settings.from_env()
        assert s.NPS == "test_nps"
        assert s.DRIP_TOKEN == "test_drip"
        assert s.DRIP_ACCOUNT == "test_account"
        assert s.FTP_USERNAME == "test_ftp_user"
        assert s.FTP_PASSWORD == "test_ftp_pass"
        assert s.MAPBOX_TOKEN == "test_mapbox"

    def test_missing_single_required_var(self, monkeypatch):
        for key, val in REQUIRED_ENV.items():
            monkeypatch.setenv(key, val)
        monkeypatch.delenv("NPS")

        with pytest.raises(ConfigError, match="NPS"):
            Settings.from_env()

    def test_missing_multiple_required_vars(self, monkeypatch):
        # Set only some required vars, delete the rest
        monkeypatch.setenv("NPS", "test")
        monkeypatch.setenv("DRIP_TOKEN", "test")
        for var in ("DRIP_ACCOUNT", "FTP_USERNAME", "FTP_PASSWORD", "MAPBOX_TOKEN"):
            monkeypatch.delenv(var, raising=False)

        with pytest.raises(ConfigError) as exc_info:
            Settings.from_env()

        msg = str(exc_info.value)
        assert "DRIP_ACCOUNT" in msg
        assert "FTP_USERNAME" in msg
        assert "FTP_PASSWORD" in msg
        assert "MAPBOX_TOKEN" in msg

    def test_defaults_applied(self, monkeypatch):
        for key, val in REQUIRED_ENV.items():
            monkeypatch.setenv(key, val)
        # Remove optional vars so defaults are used
        for var in (
            "MAPBOX_ACCOUNT",
            "MAPBOX_STYLE",
            "FTP_SERVER",
            "ENVIRONMENT",
            "DRIP_CAMPAIGN_ID",
            "BC_TOKEN",
            "CACHE_PURGE",
        ):
            monkeypatch.delenv(var, raising=False)

        s = Settings.from_env()
        assert s.MAPBOX_ACCOUNT == "mapbox"
        assert s.MAPBOX_STYLE == "satellite-streets-v12"
        assert s.FTP_SERVER == "ftp.glacier.org"
        assert s.ENVIRONMENT == "development"
        assert s.DRIP_CAMPAIGN_ID == "169298893"
        assert s.BC_TOKEN == ""
        assert s.CACHE_PURGE == ""

    def test_env_overrides_defaults(self, monkeypatch):
        for key, val in REQUIRED_ENV.items():
            monkeypatch.setenv(key, val)
        monkeypatch.setenv("MAPBOX_ACCOUNT", "custom_account")
        monkeypatch.setenv("FTP_SERVER", "ftp.example.com")

        s = Settings.from_env()
        assert s.MAPBOX_ACCOUNT == "custom_account"
        assert s.FTP_SERVER == "ftp.example.com"

    def test_frozen(self, monkeypatch):
        for key, val in REQUIRED_ENV.items():
            monkeypatch.setenv(key, val)

        s = Settings.from_env()
        with pytest.raises(AttributeError):
            s.NPS = "changed"  # type: ignore[misc]


class TestGetSettings:
    """Tests for singleton access."""

    def test_caching(self, monkeypatch):
        for key, val in REQUIRED_ENV.items():
            monkeypatch.setenv(key, val)

        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_reset_clears_cache(self, monkeypatch):
        for key, val in REQUIRED_ENV.items():
            monkeypatch.setenv(key, val)

        s1 = get_settings()
        reset_settings()
        s2 = get_settings()
        assert s1 is not s2

    def test_reset_picks_up_new_env(self, monkeypatch):
        for key, val in REQUIRED_ENV.items():
            monkeypatch.setenv(key, val)

        s1 = get_settings()
        assert s1.NPS == "test_nps"

        monkeypatch.setenv("NPS", "updated_nps")
        reset_settings()
        s2 = get_settings()
        assert s2.NPS == "updated_nps"
