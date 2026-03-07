"""Tests for XMPP bot auto-reconnection behavior."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from xmpp_bot import Settings, XmppBot
from xmpp_bot.config.constants import MAX_RECONNECT_DELAY


class TestAutoReconnect:
    """Test auto-reconnection on unexpected disconnect."""

    async def test_unexpected_disconnect_triggers_reconnect(
        self, bot_instance: XmppBot, mock_slixmpp_modules: dict[str, Any]
    ) -> None:
        """Test that an unexpected disconnect schedules auto-reconnect."""
        with patch.object(
            bot_instance, "_auto_reconnect", new_callable=AsyncMock
        ) as mock_reconnect:
            bot_instance._on_disconnected({})
            # Yield control so ensure_future-scheduled task runs
            await asyncio.sleep(0)

            assert not bot_instance.is_connected
            mock_reconnect.assert_awaited_once()

    async def test_intentional_disconnect_no_reconnect(
        self, bot_instance: XmppBot, mock_slixmpp_modules: dict[str, Any]
    ) -> None:
        """Test that intentional disconnect does not trigger reconnect."""
        with patch.object(
            bot_instance, "_auto_reconnect", new_callable=AsyncMock
        ) as mock_reconnect:
            bot_instance._disconnect_requested = True
            bot_instance._on_disconnected({})

            assert not bot_instance.is_connected
            mock_reconnect.assert_not_awaited()

    async def test_disconnect_method_sets_flag(
        self, mock_slixmpp_modules: dict[str, Any], valid_settings: Settings
    ) -> None:
        """Test that disconnect() sets _disconnect_requested."""
        bot = XmppBot.get_instance()
        bot._settings = valid_settings
        bot._client = mock_slixmpp_modules["client"]
        bot._initialized = True
        bot._connected = True
        bot._session_started = True

        bot.disconnect()

        assert bot._disconnect_requested is True


def _make_mock_client() -> MagicMock:
    """Create a mock ClientXMPP with standard attributes."""
    mock_client = MagicMock()
    mock_client.connect.return_value = None
    mock_client.add_event_handler = MagicMock()
    mock_client.register_plugin = MagicMock()
    mock_client.__getitem__ = MagicMock(return_value=MagicMock())
    return mock_client


class TestExponentialBackoff:
    """Test exponential backoff for reconnection delays."""

    async def test_first_reconnect_uses_retry_delay(
        self, bot_instance: XmppBot, valid_settings: Settings
    ) -> None:
        """Test first reconnect attempt uses retry_delay from settings."""
        assert bot_instance._reconnect_delay == 0

        with (
            patch("xmpp_bot.bot.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            patch("xmpp_bot.bot.ClientXMPP") as mock_client_class,
        ):
            mock_client_class.return_value = _make_mock_client()

            # Simulate auth failure to exit reconnect quickly
            bot_instance._auth_error = "fail"

            await bot_instance._auto_reconnect()

            mock_sleep.assert_any_call(valid_settings.retry_delay)
            assert bot_instance._reconnect_delay == valid_settings.retry_delay

    async def test_backoff_doubles_on_subsequent_attempts(
        self, bot_instance: XmppBot, valid_settings: Settings
    ) -> None:
        """Test that delay doubles on each subsequent attempt."""
        bot_instance._reconnect_delay = valid_settings.retry_delay  # 5.0

        with (
            patch("xmpp_bot.bot.asyncio.sleep", new_callable=AsyncMock),
            patch("xmpp_bot.bot.ClientXMPP") as mock_client_class,
        ):
            mock_client_class.return_value = _make_mock_client()
            bot_instance._auth_error = "fail"

            await bot_instance._auto_reconnect()

            expected_delay = valid_settings.retry_delay * 2  # 10.0
            assert bot_instance._reconnect_delay == expected_delay

    async def test_backoff_caps_at_max(self, bot_instance: XmppBot) -> None:
        """Test that backoff delay is capped at MAX_RECONNECT_DELAY."""
        bot_instance._reconnect_delay = MAX_RECONNECT_DELAY

        with (
            patch("xmpp_bot.bot.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            patch("xmpp_bot.bot.ClientXMPP") as mock_client_class,
        ):
            mock_client_class.return_value = _make_mock_client()
            bot_instance._auth_error = "fail"

            await bot_instance._auto_reconnect()

            mock_sleep.assert_any_call(MAX_RECONNECT_DELAY)
            assert bot_instance._reconnect_delay == MAX_RECONNECT_DELAY


class TestReconnectSuccess:
    """Test successful reconnection behavior."""

    async def test_backoff_resets_on_success(
        self, bot_instance: XmppBot, valid_settings: Settings
    ) -> None:
        """Test that backoff delay resets to 0 on successful reconnect."""
        bot_instance._reconnect_delay = 40.0

        with (
            patch("xmpp_bot.bot.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            patch("xmpp_bot.bot.ClientXMPP") as mock_client_class,
        ):
            mock_client_class.return_value = _make_mock_client()

            async def simulate_session_start(delay: float) -> None:
                if delay == 0.1:
                    bot_instance._session_started = True

            mock_sleep.side_effect = simulate_session_start

            await bot_instance._auto_reconnect()

            assert bot_instance._reconnect_delay == 0
            assert bot_instance._connected is True

    async def test_auth_failure_stops_reconnection(self, bot_instance: XmppBot) -> None:
        """Test that auth failure during reconnect stops reconnection."""
        bot_instance._reconnect_delay = 0
        bot_instance._connected = False

        with (
            patch("xmpp_bot.bot.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            patch("xmpp_bot.bot.ClientXMPP") as mock_client_class,
        ):
            mock_client_class.return_value = _make_mock_client()

            async def simulate_auth_failure(delay: float) -> None:
                if delay == 0.1:
                    bot_instance._auth_error = "Authentication failed"

            mock_sleep.side_effect = simulate_auth_failure

            await bot_instance._auto_reconnect()

            assert bot_instance._connected is False


class TestReconnectRetryAfterTimeout:
    """Test that reconnection retries after timeout or exception."""

    async def test_timeout_schedules_another_reconnect(
        self, bot_instance: XmppBot, valid_settings: Settings
    ) -> None:
        """Verify that when reconnection times out, another _auto_reconnect() is scheduled."""
        bot_instance._reconnect_delay = 0
        bot_instance._connected = False

        with (
            patch("xmpp_bot.bot.asyncio.sleep", new_callable=AsyncMock),
            patch("xmpp_bot.bot.ClientXMPP") as mock_client_class,
            patch("xmpp_bot.bot.asyncio.get_event_loop") as mock_loop,
            patch("xmpp_bot.bot.asyncio.ensure_future") as mock_ensure_future,
        ):
            mock_client_class.return_value = _make_mock_client()

            # First call returns 0 (start_time), second call returns beyond timeout
            mock_loop.return_value.time.side_effect = [
                0,
                valid_settings.connect_timeout + 1,
            ]

            await bot_instance._auto_reconnect()

            # Should have scheduled another reconnect attempt
            mock_ensure_future.assert_called_once()
            assert bot_instance._connected is False

    async def test_exception_schedules_another_reconnect(
        self, bot_instance: XmppBot, valid_settings: Settings
    ) -> None:
        """Verify that when reconnection raises an exception, another _auto_reconnect() is scheduled."""
        bot_instance._reconnect_delay = 0
        bot_instance._connected = False

        with (
            patch("xmpp_bot.bot.asyncio.sleep", new_callable=AsyncMock),
            patch("xmpp_bot.bot.ClientXMPP") as mock_client_class,
            patch("xmpp_bot.bot.asyncio.ensure_future") as mock_ensure_future,
        ):
            mock_client_class.side_effect = RuntimeError("connection refused")

            await bot_instance._auto_reconnect()

            mock_ensure_future.assert_called_once()
            assert bot_instance._connected is False

    async def test_auth_failure_does_not_retry(
        self, bot_instance: XmppBot, valid_settings: Settings
    ) -> None:
        """Verify that auth failure stops reconnection (no retry scheduled)."""
        bot_instance._reconnect_delay = 0
        bot_instance._connected = False

        with (
            patch("xmpp_bot.bot.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            patch("xmpp_bot.bot.ClientXMPP") as mock_client_class,
            patch("xmpp_bot.bot.asyncio.ensure_future") as mock_ensure_future,
        ):
            mock_client_class.return_value = _make_mock_client()

            async def simulate_auth_failure(delay: float) -> None:
                if delay == 0.1:
                    bot_instance._auth_error = "Authentication failed"

            mock_sleep.side_effect = simulate_auth_failure

            await bot_instance._auto_reconnect()

            mock_ensure_future.assert_not_called()
            assert bot_instance._connected is False


class TestKeepAliveConfig:
    """Test XEP-0199 ping and whitespace keepalive configuration."""

    async def test_connect_registers_xep_0199(self, valid_settings: Settings) -> None:
        """Test that _connect registers the xep_0199 plugin."""
        bot = XmppBot.get_instance()
        bot._settings = valid_settings

        mock_xep = MagicMock()
        mock_client = _make_mock_client()
        mock_client.__getitem__ = MagicMock(return_value=mock_xep)

        with (
            patch("xmpp_bot.bot.ClientXMPP", return_value=mock_client),
            patch("xmpp_bot.bot.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            patch("xmpp_bot.bot.asyncio.get_event_loop") as mock_loop,
        ):
            mock_loop.return_value.time.return_value = 0

            async def set_session(delay: float) -> None:
                if delay == 0.1:
                    bot._session_started = True

            mock_sleep.side_effect = set_session

            await bot._connect()

        mock_client.register_plugin.assert_any_call("xep_0199")
        mock_xep.enable_keepalive.assert_called_once_with(
            interval=valid_settings.keepalive_interval,
            timeout=valid_settings.connect_timeout,
        )

    async def test_connect_sets_whitespace_keepalive(self, valid_settings: Settings) -> None:
        """Test that _connect configures whitespace keepalive interval."""
        bot = XmppBot.get_instance()
        bot._settings = valid_settings

        mock_client = _make_mock_client()

        with (
            patch("xmpp_bot.bot.ClientXMPP", return_value=mock_client),
            patch("xmpp_bot.bot.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            patch("xmpp_bot.bot.asyncio.get_event_loop") as mock_loop,
        ):
            mock_loop.return_value.time.return_value = 0

            async def set_session(delay: float) -> None:
                if delay == 0.1:
                    bot._session_started = True

            mock_sleep.side_effect = set_session

            await bot._connect()

        assert mock_client.whitespace_keepalive_interval == valid_settings.keepalive_interval
