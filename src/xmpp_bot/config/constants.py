"""String constants for the XMPP bot."""

# Environment variable names
ENV_JID = "XMPP_JID"
ENV_PASSWORD = "XMPP_PASSWORD"
ENV_DEFAULT_RECEIVER = "XMPP_DEFAULT_RECEIVER"
ENV_BASE_URL = "XMPP_BASE_URL"
ENV_ALLOWED_JIDS = "XMPP_ALLOWED_JIDS"
ENV_CONNECT_TIMEOUT = "XMPP_CONNECT_TIMEOUT"
ENV_KEEPALIVE_INTERVAL = "XMPP_KEEPALIVE_INTERVAL"
ENV_RETRY_DELAY = "XMPP_RETRY_DELAY"
ENV_SEND_DELAY = "XMPP_SEND_DELAY"
ENV_RESOURCE = "XMPP_RESOURCE"
ENV_DEBUG = "XMPP_DEBUG"

# Default values
DEFAULT_CONNECT_TIMEOUT = 30
DEFAULT_KEEPALIVE_INTERVAL = 60
DEFAULT_RETRY_DELAY = 5.0
DEFAULT_SEND_DELAY = 0.1
DEFAULT_RESOURCE = "xmpp-bot"
DEFAULT_DEBUG = False

# Error messages
ERR_JID_REQUIRED = "JID is required"
ERR_PASSWORD_REQUIRED = "Password is required"
ERR_DEFAULT_RECEIVER_REQUIRED = "Default receiver is required"
ERR_INVALID_JID = "Invalid JID format: {jid}"
ERR_CONNECT_FAILED = "Failed to connect to XMPP server"
ERR_AUTH_FAILED = "Authentication failed for {jid}"
ERR_NOT_INITIALIZED = "Bot is not initialized. Call initialize() first."
ERR_ALREADY_INITIALIZED = "Bot is already initialized"
ERR_NOT_CONNECTED = "Not connected to XMPP server"
ERR_SEND_FAILED = "Failed to send message to {recipient}"
ERR_HANDLER_EXISTS = "Handler '{name}' already registered"
ERR_HANDLER_NOT_FOUND = "Handler '{name}' not found"

# Log messages
LOG_CONNECTING = "Connecting to XMPP server as {jid}..."
LOG_CONNECTED = "Connected to XMPP server"
LOG_AUTH_SUCCESS = "Authentication successful"
LOG_DISCONNECTING = "Disconnecting from XMPP server..."
LOG_DISCONNECTED = "Disconnected from XMPP server"
LOG_SENDING_MESSAGE = "Sending message to {recipient}"
LOG_MESSAGE_SENT = "Message sent to {recipient}"
LOG_MESSAGE_RECEIVED = "Message received from {sender}"
LOG_PRESENCE_RECEIVED = "Presence received from {sender}: {status}"
LOG_HANDLER_REGISTERED = "Handler '{name}' registered"
LOG_HANDLER_REMOVED = "Handler '{name}' removed"
LOG_KEEPALIVE_SENT = "Keepalive presence sent"
LOG_RECONNECTING = "Reconnecting to XMPP server..."
LOG_SUBSCRIPTION_APPROVED = "Subscription request approved for {jid}"

# Presence types
PRESENCE_AVAILABLE = "available"
PRESENCE_UNAVAILABLE = "unavailable"
PRESENCE_SUBSCRIBE = "subscribe"
PRESENCE_SUBSCRIBED = "subscribed"
PRESENCE_UNSUBSCRIBE = "unsubscribe"
PRESENCE_UNSUBSCRIBED = "unsubscribed"

# Message types
MESSAGE_CHAT = "chat"
MESSAGE_GROUPCHAT = "groupchat"
MESSAGE_NORMAL = "normal"
