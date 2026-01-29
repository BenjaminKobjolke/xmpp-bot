"""Send a test message via XMPP Bot."""

import asyncio

from xmpp_bot import XmppBot
from xmpp_bot.exceptions import AuthenticationError, ConnectionError, XmppBotError


async def main() -> None:
    """Send a test message."""
    bot = XmppBot.get_instance()
    await bot.initialize()
    await bot.send_message("Test message from XMPP Bot")
    await asyncio.sleep(1)
    bot.disconnect()
    print("Test message sent successfully!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except AuthenticationError as e:
        print(f"Authentication failed: {e}")
        print("Please check your JID and password in .env file.")
    except ConnectionError as e:
        print(f"Connection failed: {e}")
        print("Please check your XMPP server address and ensure it is reachable.")
    except XmppBotError as e:
        print(f"Bot error: {e}")
        print("Please check your configuration in .env file.")
