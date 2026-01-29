"""Tests for XmppBot class."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from xmpp_bot import Settings, XmppBot
from xmpp_bot.exceptions import (
    AlreadyInitializedError,
    NotInitializedError,
)


class TestSingleton:
    """Test singleton pattern."""

    async def test_get_instance_returns_same_instance(self) -> None:
        """Test that get_instance always returns the same instance."""
        bot1 = XmppBot.get_instance()
        bot2 = XmppBot.get_instance()
        assert bot1 is bot2

    async def test_reset_instance(
        self, mock_slixmpp_modules: dict[str, Any], valid_settings: Settings
    ) -> None:
        """Test that reset_instance creates a new instance."""
        bot1 = XmppBot.get_instance()
        # Directly set state for testing
        bot1._settings = valid_settings
        bot1._client = mock_slixmpp_modules["client"]
        bot1._initialized = True
        bot1._connected = True
        bot1._session_started = True

        await XmppBot.reset_instance()
        bot2 = XmppBot.get_instance()

        assert bot1 is not bot2
        assert not bot2.is_initialized


class TestInitialization:
    """Test bot initialization."""

    async def test_initialize_already_initialized(
        self, bot_instance: XmppBot, valid_settings: Settings
    ) -> None:
        """Test that double initialization raises error."""
        with pytest.raises(AlreadyInitializedError):
            await bot_instance.initialize(settings=valid_settings)


class TestMessaging:
    """Test message sending."""

    async def test_send_message(
        self, bot_instance: XmppBot, mock_slixmpp_modules: dict[str, Any]
    ) -> None:
        """Test sending a message to default receiver."""
        await bot_instance.send_message("Hello!")
        mock_slixmpp_modules["client"].send_message.assert_called()

    async def test_send_message_not_initialized(self) -> None:
        """Test that sending without initialization raises error."""
        bot = XmppBot.get_instance()
        with pytest.raises(NotInitializedError):
            await bot.send_message("Hello!")

    async def test_reply_to_user(
        self, bot_instance: XmppBot, mock_slixmpp_modules: dict[str, Any]
    ) -> None:
        """Test sending a direct message."""
        await bot_instance.reply_to_user("Reply!", "other@example.com")
        mock_slixmpp_modules["client"].send_message.assert_called()

    async def test_send_url(
        self, bot_instance: XmppBot, mock_slixmpp_modules: dict[str, Any]
    ) -> None:
        """Test sending a URL."""
        await bot_instance.send_url("/path/to/resource")
        mock_slixmpp_modules["client"].send_message.assert_called()

    def test_send_message_sync_legacy(
        self, bot_instance: XmppBot, mock_slixmpp_modules: dict[str, Any]
    ) -> None:
        """Test legacy sync send method."""
        bot_instance.send_message_sync("Hello!")
        mock_slixmpp_modules["client"].send_message.assert_called()


class TestHandlers:
    """Test handler management."""

    async def test_add_message_handler(self, bot_instance: XmppBot) -> None:
        """Test adding a message handler."""
        handler = AsyncMock()
        bot_instance.add_message_handler("test", handler)
        assert "test" in bot_instance._async_message_handlers

    async def test_remove_message_handler(self, bot_instance: XmppBot) -> None:
        """Test removing a message handler."""
        handler = AsyncMock()
        bot_instance.add_message_handler("test", handler)
        bot_instance.remove_message_handler("test")
        assert "test" not in bot_instance._async_message_handlers

    async def test_add_presence_handler(self, bot_instance: XmppBot) -> None:
        """Test adding a presence handler."""
        handler = AsyncMock()
        bot_instance.add_presence_handler("test", handler)
        assert "test" in bot_instance._async_presence_handlers

    async def test_remove_presence_handler(self, bot_instance: XmppBot) -> None:
        """Test removing a presence handler."""
        handler = AsyncMock()
        bot_instance.add_presence_handler("test", handler)
        bot_instance.remove_presence_handler("test")
        assert "test" not in bot_instance._async_presence_handlers


class TestDisconnect:
    """Test bot disconnect."""

    async def test_disconnect(
        self, mock_slixmpp_modules: dict[str, Any], valid_settings: Settings
    ) -> None:
        """Test disconnecting the bot."""
        bot = XmppBot.get_instance()
        bot._settings = valid_settings
        bot._client = mock_slixmpp_modules["client"]
        bot._initialized = True
        bot._connected = True
        bot._session_started = True

        bot.disconnect()

        assert not bot.is_initialized
        assert not bot.is_connected

    async def test_disconnect_not_initialized(self) -> None:
        """Test that disconnect when not initialized is safe."""
        bot = XmppBot.get_instance()
        bot.disconnect()  # Should not raise

    async def test_shutdown_alias(
        self, mock_slixmpp_modules: dict[str, Any], valid_settings: Settings
    ) -> None:
        """Test that shutdown is an alias for disconnect."""
        bot = XmppBot.get_instance()
        bot._settings = valid_settings
        bot._client = mock_slixmpp_modules["client"]
        bot._initialized = True
        bot._connected = True

        bot.shutdown()

        assert not bot.is_initialized


class TestSettings:
    """Test settings access."""

    async def test_settings_property(
        self, bot_instance: XmppBot, valid_settings: Settings
    ) -> None:
        """Test accessing settings after initialization."""
        assert bot_instance.settings == valid_settings

    async def test_settings_not_initialized(self) -> None:
        """Test that accessing settings without initialization raises error."""
        bot = XmppBot.get_instance()
        with pytest.raises(NotInitializedError):
            _ = bot.settings
