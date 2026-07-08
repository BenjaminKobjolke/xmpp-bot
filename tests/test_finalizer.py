"""Tests for neutralizing slixmpp's XMLStream.__del__ finalizer on discarded clients.

slixmpp's ``XMLStream.__del__`` calls ``self._run_out_filters.cancel()``, which schedules
on the event loop. When a client abandoned during reconnect churn is garbage-collected
after the loop has stopped/closed, that raises an (ignored but noisy)
``RuntimeError: Event loop is closed``. ``_neutralize_stream_finalizer`` disarms it while
the loop is still alive.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from xmpp_bot.bot import _neutralize_stream_finalizer


class TestNeutralizeStreamFinalizer:
    """Test _neutralize_stream_finalizer()."""

    def test_cancels_and_clears_filter_task(self) -> None:
        """It cancels the outgoing-filter task and clears it so __del__ is a no-op."""
        client = MagicMock()
        fake_task = MagicMock()
        client._run_out_filters = fake_task

        _neutralize_stream_finalizer(client)

        fake_task.cancel.assert_called_once()
        assert client._run_out_filters is None

    def test_none_client_is_noop(self) -> None:
        """Passing None must not raise."""
        _neutralize_stream_finalizer(None)

    def test_missing_filter_task_is_noop(self) -> None:
        """A client with no outgoing-filter task must not raise or call cancel."""
        client = MagicMock()
        client._run_out_filters = None

        _neutralize_stream_finalizer(client)

        assert client._run_out_filters is None

    def test_cancel_failure_is_suppressed(self) -> None:
        """A failing cancel() must be swallowed (finalizer disarm is best-effort)."""
        client = MagicMock()
        fake_task = MagicMock()
        fake_task.cancel.side_effect = RuntimeError("Event loop is closed")
        client._run_out_filters = fake_task

        _neutralize_stream_finalizer(client)  # must not raise

        assert client._run_out_filters is None
