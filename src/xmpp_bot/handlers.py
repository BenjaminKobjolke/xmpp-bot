"""Handler registry for XMPP message and presence handlers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from .config.constants import (
    ERR_HANDLER_EXISTS,
    ERR_HANDLER_NOT_FOUND,
    LOG_HANDLER_REGISTERED,
    LOG_HANDLER_REMOVED,
)
from .exceptions import HandlerExistsError, HandlerNotFoundError

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)


@runtime_checkable
class MessageHandler(Protocol):
    """Protocol for message handlers."""

    def __call__(self, sender: str, message: str, stanza: Any) -> None:
        """Handle an incoming message.

        Args:
            sender: The JID of the message sender.
            message: The message body text.
            stanza: The raw XMPP message stanza.
        """
        ...


@runtime_checkable
class PresenceHandler(Protocol):
    """Protocol for presence handlers."""

    def __call__(
        self, sender: str, presence_type: str | None, status: str | None, stanza: Any
    ) -> None:
        """Handle an incoming presence update.

        Args:
            sender: The JID of the presence sender.
            presence_type: The type of presence (available, unavailable, etc.).
            status: The status message, if any.
            stanza: The raw XMPP presence stanza.
        """
        ...


class HandlerRegistry:
    """Registry for message and presence handlers."""

    def __init__(self) -> None:
        """Initialize the handler registry."""
        self._message_handlers: dict[str, MessageHandler] = {}
        self._presence_handlers: dict[str, PresenceHandler] = {}

    def add_message_handler(self, name: str, handler: MessageHandler) -> None:
        """Register a message handler.

        Args:
            name: Unique name for the handler.
            handler: Callable that handles messages.

        Raises:
            HandlerExistsError: If a handler with this name already exists.
        """
        if name in self._message_handlers:
            raise HandlerExistsError(ERR_HANDLER_EXISTS.format(name=name))
        self._message_handlers[name] = handler
        logger.debug(LOG_HANDLER_REGISTERED.format(name=name))

    def remove_message_handler(self, name: str) -> None:
        """Remove a message handler.

        Args:
            name: Name of the handler to remove.

        Raises:
            HandlerNotFoundError: If no handler with this name exists.
        """
        if name not in self._message_handlers:
            raise HandlerNotFoundError(ERR_HANDLER_NOT_FOUND.format(name=name))
        del self._message_handlers[name]
        logger.debug(LOG_HANDLER_REMOVED.format(name=name))

    def add_presence_handler(self, name: str, handler: PresenceHandler) -> None:
        """Register a presence handler.

        Args:
            name: Unique name for the handler.
            handler: Callable that handles presence updates.

        Raises:
            HandlerExistsError: If a handler with this name already exists.
        """
        if name in self._presence_handlers:
            raise HandlerExistsError(ERR_HANDLER_EXISTS.format(name=name))
        self._presence_handlers[name] = handler
        logger.debug(LOG_HANDLER_REGISTERED.format(name=name))

    def remove_presence_handler(self, name: str) -> None:
        """Remove a presence handler.

        Args:
            name: Name of the handler to remove.

        Raises:
            HandlerNotFoundError: If no handler with this name exists.
        """
        if name not in self._presence_handlers:
            raise HandlerNotFoundError(ERR_HANDLER_NOT_FOUND.format(name=name))
        del self._presence_handlers[name]
        logger.debug(LOG_HANDLER_REMOVED.format(name=name))

    def get_message_handlers(self) -> list[MessageHandler]:
        """Get all registered message handlers.

        Returns:
            List of message handler callables.
        """
        return list(self._message_handlers.values())

    def get_presence_handlers(self) -> list[PresenceHandler]:
        """Get all registered presence handlers.

        Returns:
            List of presence handler callables.
        """
        return list(self._presence_handlers.values())

    def has_message_handler(self, name: str) -> bool:
        """Check if a message handler is registered.

        Args:
            name: Name of the handler.

        Returns:
            True if the handler exists.
        """
        return name in self._message_handlers

    def has_presence_handler(self, name: str) -> bool:
        """Check if a presence handler is registered.

        Args:
            name: Name of the handler.

        Returns:
            True if the handler exists.
        """
        return name in self._presence_handlers

    def clear(self) -> None:
        """Remove all handlers."""
        self._message_handlers.clear()
        self._presence_handlers.clear()
