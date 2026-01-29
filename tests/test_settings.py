"""Tests for Settings configuration."""

from __future__ import annotations

from pathlib import Path

import pytest

from xmpp_bot import Settings
from xmpp_bot.config.constants import (
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_KEEPALIVE_INTERVAL,
    DEFAULT_RESOURCE,
    DEFAULT_RETRY_DELAY,
    DEFAULT_SEND_DELAY,
)


class TestSettingsValidation:
    """Test Settings validation."""

    def test_valid_settings(self, valid_settings: Settings) -> None:
        """Test creating valid settings."""
        assert valid_settings.jid == "bot@example.com"
        assert valid_settings.password == "secret123"
        assert valid_settings.default_receiver == "user@example.com"
        assert valid_settings.base_url == "https://example.com"
        assert valid_settings.allowed_jids == frozenset(["user@example.com", "admin@example.com"])

    def test_minimal_settings(self, minimal_settings: Settings) -> None:
        """Test creating settings with minimal required fields."""
        assert minimal_settings.jid == "bot@example.com"
        assert minimal_settings.password == "secret"
        assert minimal_settings.default_receiver == "user@example.com"
        assert minimal_settings.base_url == ""
        assert minimal_settings.allowed_jids is None

    def test_default_values(self, minimal_settings: Settings) -> None:
        """Test that default values are applied."""
        assert minimal_settings.connect_timeout == DEFAULT_CONNECT_TIMEOUT
        assert minimal_settings.keepalive_interval == DEFAULT_KEEPALIVE_INTERVAL
        assert minimal_settings.retry_delay == DEFAULT_RETRY_DELAY
        assert minimal_settings.send_delay == DEFAULT_SEND_DELAY
        assert minimal_settings.resource == DEFAULT_RESOURCE
        assert minimal_settings.debug is False

    def test_missing_jid(self) -> None:
        """Test that missing JID raises ValueError."""
        with pytest.raises(ValueError, match="JID is required"):
            Settings(jid="", password="secret", default_receiver="user@example.com")

    def test_missing_password(self) -> None:
        """Test that missing password raises ValueError."""
        with pytest.raises(ValueError, match="Password is required"):
            Settings(jid="bot@example.com", password="", default_receiver="user@example.com")

    def test_missing_default_receiver(self) -> None:
        """Test that missing default_receiver raises ValueError."""
        with pytest.raises(ValueError, match="Default receiver is required"):
            Settings(jid="bot@example.com", password="secret", default_receiver="")

    def test_invalid_jid_format(self) -> None:
        """Test that invalid JID format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid JID format"):
            Settings(jid="invalid-jid", password="secret", default_receiver="user@example.com")

    def test_invalid_receiver_format(self) -> None:
        """Test that invalid receiver format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid JID format"):
            Settings(jid="bot@example.com", password="secret", default_receiver="invalid")


class TestSettingsProperties:
    """Test Settings property methods."""

    def test_jid_user(self, valid_settings: Settings) -> None:
        """Test extracting user from JID."""
        assert valid_settings.jid_user == "bot"

    def test_jid_domain(self, valid_settings: Settings) -> None:
        """Test extracting domain from JID."""
        assert valid_settings.jid_domain == "example.com"

    def test_full_jid_without_resource(self) -> None:
        """Test full JID when no resource in JID."""
        settings = Settings(
            jid="bot@example.com",
            password="secret",
            default_receiver="user@example.com",
            resource="mybot",
        )
        assert settings.full_jid == "bot@example.com/mybot"

    def test_full_jid_with_resource(self) -> None:
        """Test full JID when resource already in JID."""
        settings = Settings(
            jid="bot@example.com/existing",
            password="secret",
            default_receiver="user@example.com",
            resource="ignored",
        )
        assert settings.full_jid == "bot@example.com/existing"

    def test_is_jid_allowed_with_allowlist(self, valid_settings: Settings) -> None:
        """Test JID allowlist checking."""
        assert valid_settings.is_jid_allowed("user@example.com") is True
        assert valid_settings.is_jid_allowed("admin@example.com") is True
        assert valid_settings.is_jid_allowed("stranger@example.com") is False

    def test_is_jid_allowed_with_resource(self, valid_settings: Settings) -> None:
        """Test JID allowlist with resource suffix."""
        assert valid_settings.is_jid_allowed("user@example.com/resource") is True
        assert valid_settings.is_jid_allowed("stranger@example.com/resource") is False

    def test_is_jid_allowed_no_allowlist(self, minimal_settings: Settings) -> None:
        """Test that all JIDs are allowed when no allowlist."""
        assert minimal_settings.is_jid_allowed("anyone@anywhere.com") is True


class TestSettingsFromEnv:
    """Test Settings.from_env() method."""

    def test_from_env_file(self, tmp_path: Path) -> None:
        """Test loading settings from .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            """
XMPP_JID=envbot@example.com
XMPP_PASSWORD=envsecret
XMPP_DEFAULT_RECEIVER=envuser@example.com
XMPP_BASE_URL=https://env.example.com
XMPP_ALLOWED_JIDS=one@ex.com,two@ex.com
XMPP_CONNECT_TIMEOUT=45
XMPP_KEEPALIVE_INTERVAL=90
XMPP_RETRY_DELAY=10.0
XMPP_SEND_DELAY=0.5
XMPP_RESOURCE=env-resource
XMPP_DEBUG=true
"""
        )

        settings = Settings.from_env(env_file)

        assert settings.jid == "envbot@example.com"
        assert settings.password == "envsecret"
        assert settings.default_receiver == "envuser@example.com"
        assert settings.base_url == "https://env.example.com"
        assert settings.allowed_jids == frozenset(["one@ex.com", "two@ex.com"])
        assert settings.connect_timeout == 45
        assert settings.keepalive_interval == 90
        assert settings.retry_delay == 10.0
        assert settings.send_delay == 0.5
        assert settings.resource == "env-resource"
        assert settings.debug is True


class TestSettingsFromDict:
    """Test Settings.from_dict() method."""

    def test_from_dict(self) -> None:
        """Test creating settings from dictionary."""
        data = {
            "jid": "dictbot@example.com",
            "password": "dictsecret",
            "default_receiver": "dictuser@example.com",
            "base_url": "https://dict.example.com",
            "allowed_jids": ["one@ex.com", "two@ex.com"],
            "debug": True,
        }

        settings = Settings.from_dict(data)

        assert settings.jid == "dictbot@example.com"
        assert settings.password == "dictsecret"
        assert settings.default_receiver == "dictuser@example.com"
        assert settings.base_url == "https://dict.example.com"
        assert settings.allowed_jids == frozenset(["one@ex.com", "two@ex.com"])
        assert settings.debug is True

    def test_from_dict_with_string_allowed_jids(self) -> None:
        """Test creating settings with comma-separated allowed_jids string."""
        data = {
            "jid": "bot@example.com",
            "password": "secret",
            "default_receiver": "user@example.com",
            "allowed_jids": "one@ex.com,two@ex.com",
        }

        settings = Settings.from_dict(data)
        assert settings.allowed_jids == frozenset(["one@ex.com", "two@ex.com"])

    def test_frozen_settings(self, valid_settings: Settings) -> None:
        """Test that settings are immutable."""
        with pytest.raises(AttributeError):
            valid_settings.jid = "new@example.com"  # type: ignore[misc]
