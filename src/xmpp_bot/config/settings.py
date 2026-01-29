"""Settings configuration for the XMPP bot."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .constants import (
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_DEBUG,
    DEFAULT_KEEPALIVE_INTERVAL,
    DEFAULT_RESOURCE,
    DEFAULT_RETRY_DELAY,
    DEFAULT_SEND_DELAY,
    ENV_ALLOWED_JIDS,
    ENV_BASE_URL,
    ENV_CONNECT_TIMEOUT,
    ENV_DEBUG,
    ENV_DEFAULT_RECEIVER,
    ENV_JID,
    ENV_KEEPALIVE_INTERVAL,
    ENV_PASSWORD,
    ENV_RESOURCE,
    ENV_RETRY_DELAY,
    ENV_SEND_DELAY,
    ERR_DEFAULT_RECEIVER_REQUIRED,
    ERR_INVALID_JID,
    ERR_JID_REQUIRED,
    ERR_PASSWORD_REQUIRED,
)

# JID validation pattern (basic validation)
JID_PATTERN = re.compile(r"^[^@]+@[^@/]+(?:/[^@]+)?$")


def _validate_jid(jid: str, field_name: str = "JID") -> None:
    """Validate a JID format."""
    if not JID_PATTERN.match(jid):
        raise ValueError(ERR_INVALID_JID.format(jid=jid))


def _parse_bool(value: str | None, default: bool = False) -> bool:
    """Parse a string value to boolean."""
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "on")


def _parse_allowed_jids(value: str | None) -> frozenset[str] | None:
    """Parse comma-separated JIDs into a frozenset."""
    if not value:
        return None
    jids = [jid.strip() for jid in value.split(",") if jid.strip()]
    if not jids:
        return None
    for jid in jids:
        _validate_jid(jid, "allowed JID")
    return frozenset(jids)


@dataclass(frozen=True)
class Settings:
    """Immutable settings for the XMPP bot."""

    jid: str
    password: str
    default_receiver: str
    base_url: str = ""
    allowed_jids: frozenset[str] | None = None
    connect_timeout: int = DEFAULT_CONNECT_TIMEOUT
    keepalive_interval: int = DEFAULT_KEEPALIVE_INTERVAL
    retry_delay: float = DEFAULT_RETRY_DELAY
    send_delay: float = DEFAULT_SEND_DELAY
    resource: str = DEFAULT_RESOURCE
    debug: bool = DEFAULT_DEBUG

    def __post_init__(self) -> None:
        """Validate settings after initialization."""
        if not self.jid:
            raise ValueError(ERR_JID_REQUIRED)
        if not self.password:
            raise ValueError(ERR_PASSWORD_REQUIRED)
        if not self.default_receiver:
            raise ValueError(ERR_DEFAULT_RECEIVER_REQUIRED)

        _validate_jid(self.jid, "JID")
        _validate_jid(self.default_receiver, "default receiver")

    @property
    def jid_user(self) -> str:
        """Extract the user part of the JID (before @)."""
        return self.jid.split("@")[0]

    @property
    def jid_domain(self) -> str:
        """Extract the domain part of the JID (after @, before /)."""
        domain_part = self.jid.split("@")[1]
        return domain_part.split("/")[0]

    @property
    def full_jid(self) -> str:
        """Get the full JID with resource."""
        if "/" in self.jid:
            return self.jid
        return f"{self.jid}/{self.resource}"

    def is_jid_allowed(self, jid: str) -> bool:
        """Check if a JID is allowed to interact with the bot."""
        if self.allowed_jids is None:
            return True
        # Extract bare JID (without resource) for comparison
        bare_jid = jid.split("/")[0]
        return bare_jid in self.allowed_jids

    @classmethod
    def from_env(cls, env_path: str | Path | None = None) -> Settings:
        """Create Settings from environment variables.

        Args:
            env_path: Optional path to .env file. If None, searches for .env
                     in current directory and parent directories.

        Returns:
            Settings instance with values from environment.

        Raises:
            ValueError: If required environment variables are missing or invalid.
        """
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()

        jid = os.getenv(ENV_JID, "")
        password = os.getenv(ENV_PASSWORD, "")
        default_receiver = os.getenv(ENV_DEFAULT_RECEIVER, "")
        base_url = os.getenv(ENV_BASE_URL, "")
        allowed_jids = _parse_allowed_jids(os.getenv(ENV_ALLOWED_JIDS))

        connect_timeout = int(os.getenv(ENV_CONNECT_TIMEOUT, str(DEFAULT_CONNECT_TIMEOUT)))
        keepalive_interval = int(os.getenv(ENV_KEEPALIVE_INTERVAL, str(DEFAULT_KEEPALIVE_INTERVAL)))
        retry_delay = float(os.getenv(ENV_RETRY_DELAY, str(DEFAULT_RETRY_DELAY)))
        send_delay = float(os.getenv(ENV_SEND_DELAY, str(DEFAULT_SEND_DELAY)))
        resource = os.getenv(ENV_RESOURCE, DEFAULT_RESOURCE)
        debug = _parse_bool(os.getenv(ENV_DEBUG), DEFAULT_DEBUG)

        return cls(
            jid=jid,
            password=password,
            default_receiver=default_receiver,
            base_url=base_url,
            allowed_jids=allowed_jids,
            connect_timeout=connect_timeout,
            keepalive_interval=keepalive_interval,
            retry_delay=retry_delay,
            send_delay=send_delay,
            resource=resource,
            debug=debug,
        )

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Settings:
        """Create Settings from a dictionary.

        Args:
            data: Dictionary with settings values.

        Returns:
            Settings instance.
        """
        allowed_jids = data.get("allowed_jids")
        if isinstance(allowed_jids, str):
            allowed_jids = _parse_allowed_jids(allowed_jids)
        elif isinstance(allowed_jids, (list, set, frozenset)):
            allowed_jids = frozenset(allowed_jids) if allowed_jids else None

        connect_timeout_raw = data.get("connect_timeout")
        keepalive_raw = data.get("keepalive_interval")
        retry_raw = data.get("retry_delay")
        send_raw = data.get("send_delay")

        connect_timeout_val = (
            int(str(connect_timeout_raw))
            if connect_timeout_raw is not None
            else DEFAULT_CONNECT_TIMEOUT
        )
        keepalive_val = (
            int(str(keepalive_raw)) if keepalive_raw is not None else DEFAULT_KEEPALIVE_INTERVAL
        )
        retry_val = float(str(retry_raw)) if retry_raw is not None else DEFAULT_RETRY_DELAY
        send_val = float(str(send_raw)) if send_raw is not None else DEFAULT_SEND_DELAY

        return cls(
            jid=str(data.get("jid", "")),
            password=str(data.get("password", "")),
            default_receiver=str(data.get("default_receiver", "")),
            base_url=str(data.get("base_url", "")),
            allowed_jids=allowed_jids,  # type: ignore[arg-type]
            connect_timeout=connect_timeout_val,
            keepalive_interval=keepalive_val,
            retry_delay=retry_val,
            send_delay=send_val,
            resource=str(data.get("resource", DEFAULT_RESOURCE)),
            debug=bool(data.get("debug", DEFAULT_DEBUG)),
        )
