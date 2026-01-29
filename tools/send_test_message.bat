@echo off
echo Sending test message via XMPP Bot...
uv run python "%~dp0send_test_message.py"
pause
