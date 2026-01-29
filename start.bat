@echo off
echo Starting XMPP Bot...
uv run python -c "from xmpp_bot import XmppBot; bot = XmppBot.get_instance(); bot.initialize(); print('Bot connected successfully!'); bot.send_message_sync('Bot started!'); bot.shutdown()"
pause
