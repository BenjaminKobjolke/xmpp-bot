"""Pytest fixtures for XMPP bot tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from xmpp_bot import Settings, XmppBot


@pytest.fixture
def valid_settings() -> Settings:
    """Create valid settings for testing."""
    return Settings(
        jid="bot@example.com",
        password="secret123",
        default_receiver="user@example.com",
        base_url="https://example.com",
        allowed_jids=frozenset(["user@example.com", "admin@example.com"]),
        connect_timeout=30,
        keepalive_interval=60,
        retry_delay=5.0,
        send_delay=0.1,
        resource="test-bot",
        debug=False,
    )


@pytest.fixture
def minimal_settings() -> Settings:
    """Create minimal valid settings."""
    return Settings(
        jid="bot@example.com",
        password="secret",
        default_receiver="user@example.com",
    )


@pytest.fixture
def mock_slixmpp_client() -> Generator[MagicMock, None, None]:
    """Mock the slixmpp.ClientXMPP class."""
    with patch("xmpp_bot.bot.ClientXMPP") as mock_client_class:
        mock_client = MagicMock()
        mock_client.connect.return_value = None
        mock_client.disconnect.return_value = None
        mock_client.send_presence.return_value = None
        mock_client.send_message.return_value = None
        mock_client.get_roster = AsyncMock(return_value=None)
        mock_client.process.return_value = None
        mock_client.add_event_handler = MagicMock()
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_slixmpp_modules() -> Generator[dict[str, Any], None, None]:
    """Mock slixmpp module components."""
    with patch("xmpp_bot.bot.ClientXMPP") as mock_client_class:
        mock_client = MagicMock()
        mock_client.connect.return_value = None
        mock_client.disconnect.return_value = None
        mock_client.send_presence.return_value = None
        mock_client.send_message.return_value = None
        mock_client.get_roster = AsyncMock(return_value=None)
        mock_client.process.return_value = None

        # Store event handlers for triggering
        event_handlers: dict[str, list[Any]] = {}

        def add_event_handler(event: str, handler: Any) -> None:
            if event not in event_handlers:
                event_handlers[event] = []
            event_handlers[event].append(handler)

        mock_client.add_event_handler = MagicMock(side_effect=add_event_handler)
        mock_client_class.return_value = mock_client

        yield {
            "client_class": mock_client_class,
            "client": mock_client,
            "event_handlers": event_handlers,
        }


@pytest.fixture
async def bot_instance(
    mock_slixmpp_modules: dict[str, Any], valid_settings: Settings
) -> AsyncGenerator[XmppBot, None]:
    """Create a bot instance with mocked slixmpp."""
    await XmppBot.reset_instance()
    bot = XmppBot.get_instance()

    # Trigger session_start after connect is called
    async def simulate_connection() -> None:
        # Find session_start handler and call it
        handlers = mock_slixmpp_modules["event_handlers"]
        if "session_start" in handlers:
            for handler in handlers["session_start"]:
                if callable(handler):
                    result = handler({})
                    if hasattr(result, "__await__"):
                        await result

    # Patch the _connect method to also trigger session_start
    original_connect = bot._connect

    async def patched_connect() -> None:
        await original_connect()

    with patch.object(bot, "_connect", patched_connect):
        # Directly set internal state for testing
        bot._settings = valid_settings
        bot._client = mock_slixmpp_modules["client"]
        bot._initialized = True
        bot._connected = True
        bot._session_started = True

    yield bot
    bot.disconnect()
    await XmppBot.reset_instance()


@pytest.fixture(autouse=True)
async def reset_bot_singleton() -> AsyncGenerator[None, None]:
    """Reset the bot singleton before and after each test."""
    await XmppBot.reset_instance()
    yield
    await XmppBot.reset_instance()
