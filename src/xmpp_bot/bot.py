"""Core XMPP bot implementation using slixmpp."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from slixmpp import ClientXMPP
from slixmpp.stanza import Message, Presence

from .config.constants import (
    ERR_ALREADY_INITIALIZED,
    ERR_AUTH_FAILED,
    ERR_NOT_INITIALIZED,
    ERR_SEND_FAILED,
    LOG_AUTH_SUCCESS,
    LOG_CONNECTED,
    LOG_CONNECTING,
    LOG_DISCONNECTED,
    LOG_DISCONNECTING,
    LOG_MESSAGE_RECEIVED,
    LOG_MESSAGE_SENT,
    LOG_PRESENCE_RECEIVED,
    LOG_SENDING_MESSAGE,
    LOG_SUBSCRIPTION_APPROVED,
)
from .config.settings import Settings
from .exceptions import (
    AlreadyInitializedError,
    AuthenticationError,
    ConnectionError,
    NotInitializedError,
    SendError,
)
from .handlers import HandlerRegistry

if TYPE_CHECKING:
    from slixmpp.jid import JID

logger = logging.getLogger(__name__)

# Type alias for async handlers
AsyncMessageHandler = Callable[[str, str, Message], Awaitable[None]]
AsyncPresenceHandler = Callable[[str, str | None, str | None, Presence], Awaitable[None]]


class XmppBot:
    """Singleton XMPP bot for sending and receiving messages using slixmpp."""

    _instance: XmppBot | None = None
    _lock: asyncio.Lock | None = None
    _init_done: bool

    def __new__(cls) -> XmppBot:
        """Ensure only one instance exists."""
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._init_done = False
            cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> XmppBot:
        """Get the singleton instance.

        Returns:
            The singleton XmppBot instance.
        """
        return cls()

    @classmethod
    async def reset_instance(cls) -> None:
        """Reset the singleton instance. Used for testing."""
        if cls._instance is not None:
            with contextlib.suppress(Exception):
                cls._instance.disconnect()
            cls._instance = None

    def __init__(self) -> None:
        """Initialize instance variables (only runs once due to singleton)."""
        if hasattr(self, "_init_done") and self._init_done:
            return
        self._init_done = True

        self._settings: Settings | None = None
        self._client: ClientXMPP | None = None
        self._initialized: bool = False
        self._connected: bool = False
        self._session_started: bool = False
        self._auth_error: str | None = None

        self._handlers = HandlerRegistry()
        self._async_message_handlers: dict[str, AsyncMessageHandler] = {}
        self._async_presence_handlers: dict[str, AsyncPresenceHandler] = {}

    @property
    def settings(self) -> Settings:
        """Get the current settings.

        Returns:
            The Settings instance.

        Raises:
            NotInitializedError: If the bot is not initialized.
        """
        if self._settings is None:
            raise NotInitializedError(ERR_NOT_INITIALIZED)
        return self._settings

    @property
    def is_initialized(self) -> bool:
        """Check if the bot is initialized."""
        return self._initialized

    @property
    def is_connected(self) -> bool:
        """Check if the bot is connected."""
        return self._connected

    async def initialize(
        self,
        settings: Settings | None = None,
        env_path: str | Path | None = None,
    ) -> None:
        """Initialize and connect the bot.

        Args:
            settings: Optional Settings instance. If not provided, loads from env.
            env_path: Optional path to .env file.

        Raises:
            AlreadyInitializedError: If already initialized.
            ConnectionError: If connection fails.
            AuthenticationError: If authentication fails.
        """
        if self._initialized:
            raise AlreadyInitializedError(ERR_ALREADY_INITIALIZED)

        if settings is None:
            settings = Settings.from_env(env_path)
        self._settings = settings

        if settings.debug:
            logging.basicConfig(level=logging.DEBUG)

        await self._connect()
        self._initialized = True

    async def _connect(self) -> None:
        """Establish connection to the XMPP server."""
        assert self._settings is not None

        logger.info(LOG_CONNECTING.format(jid=self._settings.jid))

        self._client = ClientXMPP(
            self._settings.full_jid,
            self._settings.password,
        )

        # Register event handlers
        self._client.add_event_handler("session_start", self._on_session_start)
        self._client.add_event_handler("message", self._on_message)
        self._client.add_event_handler("presence_subscribe", self._on_presence_subscribe)
        self._client.add_event_handler("presence", self._on_presence)
        self._client.add_event_handler("failed_auth", self._on_failed_auth)
        self._client.add_event_handler("disconnected", self._on_disconnected)

        # Reset state
        self._session_started = False
        self._auth_error = None

        # Connect (non-blocking)
        self._client.connect()

        # Wait for session to start or auth to fail
        timeout = self._settings.connect_timeout
        start_time = asyncio.get_event_loop().time()

        while not self._session_started and self._auth_error is None:
            await asyncio.sleep(0.1)
            if asyncio.get_event_loop().time() - start_time > timeout:
                self._client.disconnect()
                raise ConnectionError(f"Connection timed out after {timeout} seconds")

        if self._auth_error:
            raise AuthenticationError(ERR_AUTH_FAILED.format(jid=self._settings.jid))

        logger.info(LOG_CONNECTED)
        logger.info(LOG_AUTH_SUCCESS)
        self._connected = True

    async def _on_session_start(self, event: dict[str, Any]) -> None:
        """Handle session start event."""
        assert self._client is not None
        self._client.send_presence()
        await self._client.get_roster()  # type: ignore[no-untyped-call]
        self._session_started = True

    def _on_failed_auth(self, event: dict[str, Any]) -> None:
        """Handle failed authentication."""
        self._auth_error = "Authentication failed"

    def _on_disconnected(self, event: dict[str, Any]) -> None:
        """Handle disconnection."""
        self._connected = False
        self._session_started = False
        logger.info(LOG_DISCONNECTED)

    async def _on_message(self, msg: Message) -> None:
        """Handle incoming messages."""
        if msg["type"] not in ("chat", "normal"):
            return

        body = msg["body"]
        if not body:
            return

        sender_jid: JID = msg["from"]
        sender = str(sender_jid)
        bare_sender = sender_jid.bare

        assert self._settings is not None
        if not self._settings.is_jid_allowed(bare_sender):
            logger.warning(f"Message from unauthorized JID: {bare_sender}")
            return

        logger.debug(LOG_MESSAGE_RECEIVED.format(sender=sender))

        # Call sync handlers (legacy support)
        for sync_handler in self._handlers.get_message_handlers():
            try:
                sync_handler(sender, body, msg)
            except Exception as e:
                logger.exception(f"Error in message handler: {e}")

        # Call async handlers
        for async_handler in self._async_message_handlers.values():
            try:
                await async_handler(sender, body, msg)
            except Exception as e:
                logger.exception(f"Error in async message handler: {e}")

    def _on_presence_subscribe(self, presence: Presence) -> None:
        """Handle subscription requests - auto-approve."""
        assert self._client is not None
        sender = str(presence["from"])
        ptype: Literal["subscribed"] = "subscribed"
        self._client.send_presence(pto=sender, ptype=ptype)
        logger.info(LOG_SUBSCRIPTION_APPROVED.format(jid=sender))

    async def _on_presence(self, presence: Presence) -> None:
        """Handle incoming presence updates."""
        sender = str(presence["from"])
        presence_type = presence["type"]
        status = presence["status"]

        logger.debug(LOG_PRESENCE_RECEIVED.format(sender=sender, status=status))

        # Call sync handlers (legacy support)
        for sync_handler in self._handlers.get_presence_handlers():
            try:
                sync_handler(sender, presence_type, status, presence)
            except Exception as e:
                logger.exception(f"Error in presence handler: {e}")

        # Call async handlers
        for async_handler in self._async_presence_handlers.values():
            try:
                await async_handler(sender, presence_type, status, presence)
            except Exception as e:
                logger.exception(f"Error in async presence handler: {e}")

    def add_message_handler(
        self,
        name: str,
        handler: AsyncMessageHandler,
    ) -> None:
        """Register an async message handler.

        Args:
            name: Unique name for the handler.
            handler: Async callable that handles messages.
        """
        self._async_message_handlers[name] = handler

    def remove_message_handler(self, name: str) -> None:
        """Remove a message handler.

        Args:
            name: Name of the handler to remove.
        """
        if name in self._async_message_handlers:
            del self._async_message_handlers[name]
        else:
            self._handlers.remove_message_handler(name)

    def add_presence_handler(
        self,
        name: str,
        handler: AsyncPresenceHandler,
    ) -> None:
        """Register an async presence handler.

        Args:
            name: Unique name for the handler.
            handler: Async callable that handles presence updates.
        """
        self._async_presence_handlers[name] = handler

    def remove_presence_handler(self, name: str) -> None:
        """Remove a presence handler.

        Args:
            name: Name of the handler to remove.
        """
        if name in self._async_presence_handlers:
            del self._async_presence_handlers[name]
        else:
            self._handlers.remove_presence_handler(name)

    async def send_message(self, message: str) -> None:
        """Send a message to the default receiver.

        Args:
            message: The message text to send.

        Raises:
            NotInitializedError: If the bot is not initialized.
            SendError: If sending fails.
        """
        if not self._initialized:
            raise NotInitializedError(ERR_NOT_INITIALIZED)

        assert self._settings is not None
        await self.reply_to_user(message, self._settings.default_receiver)

    async def reply_to_user(self, message: str, jid: str) -> None:
        """Send a direct message to a specific JID.

        Args:
            message: The message text to send.
            jid: The recipient's JID.

        Raises:
            NotInitializedError: If the bot is not initialized.
            SendError: If sending fails.
        """
        if not self._initialized:
            raise NotInitializedError(ERR_NOT_INITIALIZED)

        if not self._connected or not self._client:
            raise SendError(ERR_SEND_FAILED.format(recipient=jid))

        logger.debug(LOG_SENDING_MESSAGE.format(recipient=jid))

        try:
            mtype: Literal["chat"] = "chat"
            self._client.send_message(
                mto=jid,  # type: ignore[arg-type]
                mbody=message,
                mtype=mtype,
            )
            logger.debug(LOG_MESSAGE_SENT.format(recipient=jid))
        except Exception as e:
            logger.error(f"Send failed: {e}")
            raise SendError(ERR_SEND_FAILED.format(recipient=jid)) from e

    async def flush(self, timeout: float = 5.0) -> None:
        """Wait for pending outgoing messages to be written to the network.

        Args:
            timeout: Maximum time to wait in seconds.
        """
        if not self._client or not self._connected:
            return

        transport = getattr(self._client, "transport", None)
        if transport is None:
            return

        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            buf_size = getattr(transport, "get_write_buffer_size", lambda: 0)()
            if buf_size == 0:
                return
            await asyncio.sleep(0.05)

    async def send_url(self, path: str) -> None:
        """Send a URL constructed from base_url and path.

        Args:
            path: The path to append to base_url.

        Raises:
            NotInitializedError: If the bot is not initialized.
        """
        if not self._initialized:
            raise NotInitializedError(ERR_NOT_INITIALIZED)

        assert self._settings is not None
        url = f"{self._settings.base_url.rstrip('/')}/{path.lstrip('/')}"
        await self.send_message(url)

    def run_forever(self) -> None:
        """Run the bot's event loop forever.

        This blocks until disconnect() is called or the connection is lost.
        """
        if not self._initialized:
            raise NotInitializedError(ERR_NOT_INITIALIZED)

        loop = asyncio.get_event_loop()
        loop.run_forever()

    def disconnect(self) -> None:
        """Disconnect the bot and release resources."""
        if not self._initialized:
            return

        logger.info(LOG_DISCONNECTING)

        if self._client and self._connected:
            with contextlib.suppress(Exception):
                self._client.disconnect()

        self._connected = False
        self._initialized = False
        self._session_started = False
        self._client = None
        self._handlers.clear()
        self._async_message_handlers.clear()
        self._async_presence_handlers.clear()

        logger.info(LOG_DISCONNECTED)

    # Legacy sync API aliases for backward compatibility
    def send_message_sync(self, message: str) -> None:
        """Legacy sync wrapper - sends message using current event loop.

        Deprecated: Use `await send_message()` instead.
        """
        if not self._initialized:
            raise NotInitializedError(ERR_NOT_INITIALIZED)

        assert self._settings is not None
        if self._client:
            mtype: Literal["chat"] = "chat"
            self._client.send_message(
                mto=self._settings.default_receiver,  # type: ignore[arg-type]
                mbody=message,
                mtype=mtype,
            )

    def shutdown(self) -> None:
        """Legacy alias for disconnect().

        Deprecated: Use `disconnect()` instead.
        """
        self.disconnect()
