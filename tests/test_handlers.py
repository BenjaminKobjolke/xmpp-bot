"""Tests for handler registry."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from xmpp_bot import HandlerRegistry
from xmpp_bot.exceptions import HandlerExistsError, HandlerNotFoundError


class TestHandlerRegistry:
    """Test HandlerRegistry class."""

    @pytest.fixture
    def registry(self) -> HandlerRegistry:
        """Create a fresh handler registry."""
        return HandlerRegistry()

    @pytest.fixture
    def message_handler(self) -> MagicMock:
        """Create a mock message handler."""
        return MagicMock()

    @pytest.fixture
    def presence_handler(self) -> MagicMock:
        """Create a mock presence handler."""
        return MagicMock()


class TestMessageHandlers(TestHandlerRegistry):
    """Test message handler management."""

    def test_add_message_handler(
        self, registry: HandlerRegistry, message_handler: MagicMock
    ) -> None:
        """Test adding a message handler."""
        registry.add_message_handler("test", message_handler)
        assert registry.has_message_handler("test")
        assert message_handler in registry.get_message_handlers()

    def test_add_duplicate_message_handler(
        self, registry: HandlerRegistry, message_handler: MagicMock
    ) -> None:
        """Test that adding duplicate handler raises error."""
        registry.add_message_handler("test", message_handler)
        with pytest.raises(HandlerExistsError):
            registry.add_message_handler("test", message_handler)

    def test_remove_message_handler(
        self, registry: HandlerRegistry, message_handler: MagicMock
    ) -> None:
        """Test removing a message handler."""
        registry.add_message_handler("test", message_handler)
        registry.remove_message_handler("test")
        assert not registry.has_message_handler("test")

    def test_remove_nonexistent_message_handler(self, registry: HandlerRegistry) -> None:
        """Test that removing nonexistent handler raises error."""
        with pytest.raises(HandlerNotFoundError):
            registry.remove_message_handler("nonexistent")

    def test_get_message_handlers(
        self, registry: HandlerRegistry, message_handler: MagicMock
    ) -> None:
        """Test getting all message handlers."""
        handler2 = MagicMock()
        registry.add_message_handler("first", message_handler)
        registry.add_message_handler("second", handler2)

        handlers = registry.get_message_handlers()
        assert len(handlers) == 2
        assert message_handler in handlers
        assert handler2 in handlers


class TestPresenceHandlers(TestHandlerRegistry):
    """Test presence handler management."""

    def test_add_presence_handler(
        self, registry: HandlerRegistry, presence_handler: MagicMock
    ) -> None:
        """Test adding a presence handler."""
        registry.add_presence_handler("test", presence_handler)
        assert registry.has_presence_handler("test")
        assert presence_handler in registry.get_presence_handlers()

    def test_add_duplicate_presence_handler(
        self, registry: HandlerRegistry, presence_handler: MagicMock
    ) -> None:
        """Test that adding duplicate handler raises error."""
        registry.add_presence_handler("test", presence_handler)
        with pytest.raises(HandlerExistsError):
            registry.add_presence_handler("test", presence_handler)

    def test_remove_presence_handler(
        self, registry: HandlerRegistry, presence_handler: MagicMock
    ) -> None:
        """Test removing a presence handler."""
        registry.add_presence_handler("test", presence_handler)
        registry.remove_presence_handler("test")
        assert not registry.has_presence_handler("test")

    def test_remove_nonexistent_presence_handler(self, registry: HandlerRegistry) -> None:
        """Test that removing nonexistent handler raises error."""
        with pytest.raises(HandlerNotFoundError):
            registry.remove_presence_handler("nonexistent")


class TestClearHandlers(TestHandlerRegistry):
    """Test clearing all handlers."""

    def test_clear(
        self,
        registry: HandlerRegistry,
        message_handler: MagicMock,
        presence_handler: MagicMock,
    ) -> None:
        """Test clearing all handlers."""
        registry.add_message_handler("msg", message_handler)
        registry.add_presence_handler("pres", presence_handler)

        registry.clear()

        assert not registry.has_message_handler("msg")
        assert not registry.has_presence_handler("pres")
        assert len(registry.get_message_handlers()) == 0
        assert len(registry.get_presence_handlers()) == 0
