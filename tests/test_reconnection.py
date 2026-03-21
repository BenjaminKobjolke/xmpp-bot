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
            # Flag must be set synchronously before the coroutine runs
            assert bot_instance._reconnecting is True
            assert bot_instance._reconnect_task is not None
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
    mock_client.del_event_handler = MagicMock()
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
        bot_instance._reconnecting = True

        with (
            patch("xmpp_bot.bot.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            patch("xmpp_bot.bot.ClientXMPP") as mock_client_class,
        ):
            mock_client_class.return_value = _make_mock_client()

            async def simulate_auth_failure(delay: float) -> None:
                if delay == 0.1:
                    bot_instance._auth_error = "fail"

            mock_sleep.side_effect = simulate_auth_failure

            await bot_instance._auto_reconnect()

            mock_sleep.assert_any_call(valid_settings.retry_delay)
            assert bot_instance._reconnect_delay == valid_settings.retry_delay

    async def test_backoff_doubles_on_subsequent_attempts(
        self, bot_instance: XmppBot, valid_settings: Settings
    ) -> None:
        """Test that delay doubles on each subsequent attempt."""
        bot_instance._reconnect_delay = valid_settings.retry_delay  # 5.0
        bot_instance._reconnecting = True

        with (
            patch("xmpp_bot.bot.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            patch("xmpp_bot.bot.ClientXMPP") as mock_client_class,
        ):
            mock_client_class.return_value = _make_mock_client()

            async def simulate_auth_failure(delay: float) -> None:
                if delay == 0.1:
                    bot_instance._auth_error = "fail"

            mock_sleep.side_effect = simulate_auth_failure

            await bot_instance._auto_reconnect()

            expected_delay = valid_settings.retry_delay * 2  # 10.0
            assert bot_instance._reconnect_delay == expected_delay

    async def test_backoff_caps_at_max(self, bot_instance: XmppBot) -> None:
        """Test that backoff delay is capped at MAX_RECONNECT_DELAY."""
        bot_instance._reconnect_delay = MAX_RECONNECT_DELAY
        bot_instance._reconnecting = True

        with (
            patch("xmpp_bot.bot.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            patch("xmpp_bot.bot.ClientXMPP") as mock_client_class,
        ):
            mock_client_class.return_value = _make_mock_client()

            async def simulate_auth_failure(delay: float) -> None:
                if delay == 0.1:
                    bot_instance._auth_error = "fail"

            mock_sleep.side_effect = simulate_auth_failure

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
        bot_instance._reconnecting = True

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
        bot_instance._reconnecting = True

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

    async def test_timeout_retries_via_loop(
        self, bot_instance: XmppBot, valid_settings: Settings
    ) -> None:
        """Verify that when reconnection times out, the loop retries."""
        bot_instance._reconnect_delay = 0
        bot_instance._connected = False
        bot_instance._reconnecting = True

        call_count = 0

        with (
            patch("xmpp_bot.bot.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            patch("xmpp_bot.bot.ClientXMPP") as mock_client_class,
            patch("xmpp_bot.bot.asyncio.get_event_loop") as mock_loop,
        ):
            mock_client_class.return_value = _make_mock_client()

            # First iteration: times out. Second iteration: succeeds.
            time_values = iter([
                0, valid_settings.connect_timeout + 1,  # 1st attempt: timeout
                0, 1,  # 2nd attempt: start_time, then check (within timeout)
            ])
            mock_loop.return_value.time.side_effect = lambda: next(time_values)

            async def simulate_session_on_second(delay: float) -> None:
                nonlocal call_count
                if delay == 0.1:
                    call_count += 1
                    if call_count >= 2:
                        bot_instance._session_started = True

            mock_sleep.side_effect = simulate_session_on_second

            await bot_instance._auto_reconnect()

            assert mock_client_class.call_count == 2
            assert bot_instance._connected is True
            assert bot_instance._reconnecting is False

    async def test_exception_retries_via_loop(
        self, bot_instance: XmppBot, valid_settings: Settings
    ) -> None:
        """Verify that when reconnection raises an exception, the loop retries."""
        bot_instance._reconnect_delay = 0
        bot_instance._connected = False
        bot_instance._reconnecting = True

        with (
            patch("xmpp_bot.bot.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            patch("xmpp_bot.bot.ClientXMPP") as mock_client_class,
            patch("xmpp_bot.bot.asyncio.get_event_loop") as mock_loop,
        ):
            second_client = _make_mock_client()
            mock_client_class.side_effect = [
                RuntimeError("connection refused"),
                second_client,
            ]

            mock_loop.return_value.time.return_value = 0

            async def simulate_session(delay: float) -> None:
                if delay == 0.1:
                    bot_instance._session_started = True

            mock_sleep.side_effect = simulate_session

            await bot_instance._auto_reconnect()

            assert mock_client_class.call_count == 2
            assert bot_instance._connected is True
            assert bot_instance._reconnecting is False

    async def test_auth_failure_does_not_retry(
        self, bot_instance: XmppBot, valid_settings: Settings
    ) -> None:
        """Verify that auth failure stops reconnection (no retry)."""
        bot_instance._reconnect_delay = 0
        bot_instance._connected = False
        bot_instance._reconnecting = True

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

            assert mock_client_class.call_count == 1
            assert bot_instance._connected is False
            assert bot_instance._reconnecting is False


class TestReconnectGuard:
    """Test that concurrent reconnect attempts are prevented."""

    async def test_concurrent_reconnect_prevented(
        self, bot_instance: XmppBot, mock_slixmpp_modules: dict[str, Any]
    ) -> None:
        """Test that _on_disconnected does not spawn reconnect when already reconnecting."""
        bot_instance._reconnecting = True

        with patch.object(
            bot_instance, "_auto_reconnect", new_callable=AsyncMock
        ) as mock_reconnect:
            bot_instance._on_disconnected({})
            await asyncio.sleep(0)

            mock_reconnect.assert_not_awaited()

    async def test_reconnecting_flag_cleared_on_success(
        self, bot_instance: XmppBot, valid_settings: Settings
    ) -> None:
        """Test that _reconnecting is cleared after successful reconnect."""
        bot_instance._reconnect_delay = 0
        bot_instance._connected = False
        bot_instance._reconnecting = True

        with (
            patch("xmpp_bot.bot.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            patch("xmpp_bot.bot.ClientXMPP") as mock_client_class,
            patch("xmpp_bot.bot.asyncio.get_event_loop") as mock_loop,
        ):
            mock_client_class.return_value = _make_mock_client()
            mock_loop.return_value.time.return_value = 0

            async def simulate_session(delay: float) -> None:
                if delay == 0.1:
                    bot_instance._session_started = True

            mock_sleep.side_effect = simulate_session

            await bot_instance._auto_reconnect()

            assert bot_instance._reconnecting is False
            assert bot_instance._connected is True

    async def test_reconnecting_flag_cleared_on_auth_failure(
        self, bot_instance: XmppBot, valid_settings: Settings
    ) -> None:
        """Test that _reconnecting is cleared after auth failure."""
        bot_instance._reconnect_delay = 0
        bot_instance._reconnecting = True

        with (
            patch("xmpp_bot.bot.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            patch("xmpp_bot.bot.ClientXMPP") as mock_client_class,
        ):
            mock_client_class.return_value = _make_mock_client()

            async def simulate_auth_failure(delay: float) -> None:
                if delay == 0.1:
                    bot_instance._auth_error = "fail"

            mock_sleep.side_effect = simulate_auth_failure

            await bot_instance._auto_reconnect()

            assert bot_instance._reconnecting is False


class TestReconnectTaskTracking:
    """Test asyncio.Task-based reconnect tracking."""

    async def test_multiple_disconnect_events_single_reconnect(
        self, bot_instance: XmppBot, mock_slixmpp_modules: dict[str, Any]
    ) -> None:
        """Test that 40 rapid disconnect events only spawn one reconnect."""
        with patch.object(
            bot_instance, "_auto_reconnect", new_callable=AsyncMock
        ) as mock_reconnect:
            # Simulate 40 disconnect events fired synchronously
            for _ in range(40):
                bot_instance._on_disconnected({})

            await asyncio.sleep(0)

            # Only one reconnect should have been scheduled
            mock_reconnect.assert_awaited_once()
            assert bot_instance._reconnecting is True

    async def test_cancelled_error_during_reconnect(
        self, bot_instance: XmppBot, valid_settings: Settings
    ) -> None:
        """Test that CancelledError during sleep clears reconnecting flag."""
        bot_instance._reconnect_delay = 0
        bot_instance._reconnecting = True

        with patch("xmpp_bot.bot.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = asyncio.CancelledError()

            await bot_instance._auto_reconnect()

            assert bot_instance._reconnecting is False
            assert bot_instance._reconnect_task is None

    async def test_disconnect_cancels_reconnect_task(
        self, mock_slixmpp_modules: dict[str, Any], valid_settings: Settings
    ) -> None:
        """Test that disconnect() cancels any running reconnect task."""
        bot = XmppBot.get_instance()
        bot._settings = valid_settings
        bot._client = mock_slixmpp_modules["client"]
        bot._initialized = True
        bot._connected = True

        mock_task = MagicMock(spec=asyncio.Task)
        bot._reconnect_task = mock_task
        bot._reconnecting = True

        bot.disconnect()

        mock_task.cancel.assert_called_once()
        assert bot._reconnect_task is None
        assert bot._reconnecting is False

    async def test_cleanup_client_removes_event_handlers(
        self, bot_instance: XmppBot, mock_slixmpp_modules: dict[str, Any]
    ) -> None:
        """Test that _cleanup_client removes event handlers before disconnecting."""
        mock_client = mock_slixmpp_modules["client"]
        mock_client.del_event_handler = MagicMock()

        bot_instance._cleanup_client()

        # Verify del_event_handler was called for critical events
        calls = mock_client.del_event_handler.call_args_list
        event_names = [call[0][0] for call in calls]
        assert "disconnected" in event_names
        assert "session_start" in event_names
        assert "message" in event_names

    async def test_reconnecting_flag_set_synchronously(
        self, bot_instance: XmppBot, mock_slixmpp_modules: dict[str, Any]
    ) -> None:
        """Test that _reconnecting is True immediately after _on_disconnected, before yielding."""
        with patch.object(
            bot_instance, "_auto_reconnect", new_callable=AsyncMock
        ):
            bot_instance._on_disconnected({})
            # Check BEFORE yielding - flag must already be True
            assert bot_instance._reconnecting is True
            assert bot_instance._reconnect_task is not None


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
