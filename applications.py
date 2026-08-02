import re
from typing import Any


def trim_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def build_answer_block(label: str, value: str) -> str:
    cleaned = trim_text((value or "—").strip(), limit=850)
    quoted = "\n".join(f"> {line}" for line in cleaned.splitlines() if line.strip()) or "> —"
    return f"**{label}**\n{quoted}"


def sanitize_channel_name_component(value: str, fallback: str = "user", limit: int = 24) -> str:
    cleaned = re.sub(r"[^a-z0-9а-яё_-]+", "-", (value or "").strip().lower(), flags=re.IGNORECASE)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned[:limit] or fallback


def extract_nickname_and_static(raw_value: str) -> tuple[str, str]:
    cleaned = " ".join((raw_value or "").strip().split())
    if not cleaned:
        return "Ник", "Статик"

    static_match = re.search(r"(\d{1,8})\s*$", cleaned)
    static_value = static_match.group(1) if static_match else "Статик"
    nickname_part = cleaned[: static_match.start()].strip(" |-") if static_match else cleaned
    nickname_tokens = nickname_part.split()
    nickname = nickname_tokens[0] if nickname_tokens else nickname_part or "Ник"
    return nickname[:24], static_value[:16]


def extract_legacy_irl_name(raw_value: str) -> str:
    cleaned = " ".join((raw_value or "").strip().split())
    if not cleaned:
        return ""
    cleaned = re.sub(r"\b\d{1,2}\b.*$", "", cleaned).strip(" ,|-/")
    return cleaned[:20]


def extract_static_id(raw_value: str) -> str:
    _nickname, static_value = extract_nickname_and_static(raw_value)
    return static_value


def build_asx_member_nickname(application: dict[str, Any]) -> str:
    irl_name = (application.get("irlName") or extract_legacy_irl_name(application.get("nameAge", "")) or "Имя").strip()
    static_value = extract_static_id(application.get("nameStatic", "")) or "Static-ID"
    suffix = f" | {static_value}"
    max_name_length = max(1, 32 - len("ASX | ") - len(suffix))
    return f"ASX | {irl_name[:max_name_length]}{suffix}"[:32]
