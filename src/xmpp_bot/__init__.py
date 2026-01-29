"""XMPP Bot library using slixmpp."""

from .bot import AsyncMessageHandler, AsyncPresenceHandler, XmppBot
from .config import Settings
from .exceptions import (
    AccessDeniedError,
    AlreadyInitializedError,
    AuthenticationError,
    ConfigurationError,
    ConnectionError,
    HandlerError,
    HandlerExistsError,
    HandlerNotFoundError,
    NotInitializedError,
    SendError,
    XmppBotError,
)
from .handlers import HandlerRegistry, MessageHandler, PresenceHandler

__all__ = [
    "AccessDeniedError",
    "AlreadyInitializedError",
    "AsyncMessageHandler",
    "AsyncPresenceHandler",
    "AuthenticationError",
    "ConfigurationError",
    "ConnectionError",
    "HandlerError",
    "HandlerExistsError",
    "HandlerNotFoundError",
    "HandlerRegistry",
    "MessageHandler",
    "NotInitializedError",
    "PresenceHandler",
    "SendError",
    "Settings",
    "XmppBot",
    "XmppBotError",
]

__version__ = "0.1.0"
