"""Valkey async client (BSD-3 Redis fork — NEVER use redis package)."""

from valkey.asyncio import Valkey

from config import settings

valkey: Valkey = Valkey.from_url(
    settings.valkey_url,
    decode_responses=True,
    socket_keepalive=True,
)
