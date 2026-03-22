from __future__ import annotations

import re
import secrets

TOKEN_PATTERN = re.compile(r"^vf_[A-Za-z0-9]{24,128}$")


def create_paid_access_token() -> str:
    # 32 bytes URL-safe, stripped to alphanumeric payload for simpler handling.
    raw = secrets.token_urlsafe(32)
    compact = "".join(ch for ch in raw if ch.isalnum())
    compact = compact[:48] if len(compact) > 48 else compact
    if len(compact) < 24:
        compact += secrets.token_hex(12)
    return f"vf_{compact}"


def is_valid_paid_access_token(token: str) -> bool:
    return bool(TOKEN_PATTERN.fullmatch(token or ""))
