"""Exception hierarchy for the XMPP bot."""


class XmppBotError(Exception):
    """Base exception for all XMPP bot errors."""


class ConfigurationError(XmppBotError):
    """Raised when there's a configuration problem."""


class ConnectionError(XmppBotError):
    """Raised when there's a connection problem."""


class AuthenticationError(ConnectionError):
    """Raised when authentication fails."""


class NotInitializedError(XmppBotError):
    """Raised when the bot is used before initialization."""


class AlreadyInitializedError(XmppBotError):
    """Raised when trying to initialize an already initialized bot."""


class SendError(XmppBotError):
    """Raised when sending a message fails."""


class HandlerError(XmppBotError):
    """Raised when there's a handler-related error."""


class HandlerExistsError(HandlerError):
    """Raised when trying to register a handler that already exists."""


class HandlerNotFoundError(HandlerError):
    """Raised when trying to remove a handler that doesn't exist."""


class AccessDeniedError(XmppBotError):
    """Raised when a JID is not allowed to interact with the bot."""
