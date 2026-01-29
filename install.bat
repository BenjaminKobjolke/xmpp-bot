@echo off
echo Installing xmpp-bot...
uv sync --all-extras
echo.
echo Installation complete!
echo.
echo Next steps:
echo 1. Copy .env.example to .env
echo 2. Edit .env with your XMPP credentials
echo 3. Run start.bat to test connection
pause
