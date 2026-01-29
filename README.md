# XMPP Bot

A Python XMPP bot library using xmpppy for sending and receiving messages.

## Installation

```bash
# Using uv (recommended)
uv sync --all-extras

# Or using the install script (Windows)
install.bat
```

## Configuration

Copy `.env.example` to `.env` and configure:

```env
XMPP_JID=bot@xmpp.domain.tld
XMPP_PASSWORD=secret
XMPP_DEFAULT_RECEIVER=user@xmpp.domain.tld
XMPP_BASE_URL=https://your-server.com
XMPP_ALLOWED_JIDS=admin@xmpp.domain.tld,user@xmpp.domain.tld
XMPP_CONNECT_TIMEOUT=30
XMPP_KEEPALIVE_INTERVAL=60
XMPP_RETRY_DELAY=5.0
XMPP_SEND_DELAY=0.1
XMPP_RESOURCE=xmpp-bot
XMPP_DEBUG=False
```

## Usage

### Basic Usage

```python
from xmpp_bot import XmppBot

# Get singleton instance
bot = XmppBot.get_instance()

# Initialize from .env file
bot.initialize()

# Send a message to default receiver
bot.send_message_sync("Hello!")

# Send to specific user
bot.reply_to_user("Direct message", "user@example.com")

# Send a URL
bot.send_url_sync("/path/to/resource")

# Cleanup
bot.shutdown()
```

### With Custom Settings

```python
from xmpp_bot import XmppBot, Settings

settings = Settings(
    jid="bot@example.com",
    password="secret",
    default_receiver="user@example.com",
    base_url="https://example.com",
    allowed_jids=frozenset(["user@example.com"]),
)

bot = XmppBot.get_instance()
bot.initialize(settings=settings)
```

### Message Handlers

```python
from xmpp_bot import XmppBot

def echo_handler(sender: str, message: str, stanza) -> None:
    bot = XmppBot.get_instance()
    bot.reply_to_user(f"Echo: {message}", sender)

bot = XmppBot.get_instance()
bot.initialize()

# Register handler
bot.add_message_handler("echo", echo_handler)

# Start receiving messages
bot.start_receiving()

# ... your application logic ...

# Stop receiving
bot.stop_receiving()

# Remove handler
bot.remove_message_handler("echo")

bot.shutdown()
```

### Presence Handlers

```python
def presence_handler(sender: str, presence_type: str | None, status: str | None, stanza) -> None:
    print(f"{sender} is now {presence_type}: {status}")

bot.add_presence_handler("status", presence_handler)
```

## Features

- **Singleton pattern** - Single bot instance across your application
- **Thread-safe** - Background workers for sending and receiving
- **Auto-reconnection** - Automatically reconnects on connection loss
- **Keepalive** - Periodic presence pings to maintain connection
- **Access control** - Optional JID allowlist for security
- **Auto-subscription** - Automatically approves subscription requests

## Development

```bash
# Install with dev dependencies
uv sync --all-extras

# Run tests
uv run pytest -v

# Run linter
uv run ruff check src/ tests/

# Run type checker
uv run mypy src/
```

## Project Structure

```
xmpp-bot/
├── src/xmpp_bot/
│   ├── __init__.py       # Public API
│   ├── bot.py            # Core bot class
│   ├── exceptions.py     # Exception hierarchy
│   ├── handlers.py       # Handler registry
│   └── config/
│       ├── constants.py  # String constants
│       └── settings.py   # Settings dataclass
├── tests/
│   ├── conftest.py       # Pytest fixtures
│   ├── test_bot.py
│   ├── test_handlers.py
│   └── test_settings.py
└── tools/
    └── tests.bat
```

## License

MIT
