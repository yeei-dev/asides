import asyncio
import os
import random
import re
import sys
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands
from applications import (
    build_answer_block,
    build_asx_member_nickname,
    extract_legacy_irl_name,
    extract_nickname_and_static,
    extract_static_id,
    sanitize_channel_name_component,
)
from config import *
from logging_setup import setup_logging
from storage import BotStorage


logger = setup_logging(BASE_DIR)


def console_log(message: str) -> None:
    level = logger.error if any(word in message.lower() for word in ("failed", "error", "skipped")) else logger.info
    level(message)
    sys.stdout.write(f"{message}\n")



FAMQ_FLEET = [
    {
        "name": "Enus Callinon",
        "real_name": "Rolls-Royce Cullinan",
        "capacity": "180 кг",
        "speed": "320 км/ч",
        "fuel": "Premium",
        "rank": "3 Ранг",
        "image": "https://cdn.discordapp.com/attachments/1476538051416162415/1484133399177465977/image.png?ex=69ccf070&is=69cb9ef0&hm=e6cf5275ffd01f3b98a44565b97f0cc1ecac07e294e1b1f9494a5f6d99aecbf2&",
    },
    {
        "name": "Ubermacht X6 M F86",
        "real_name": "BMW X6 M F86",
        "capacity": "100 кг",
        "speed": "275 км/ч",
        "fuel": "Premium",
        "rank": "3 Ранг",
        "image": "https://cdn.discordapp.com/attachments/1476538051416162415/1484133964330565765/image.png?ex=69ccf0f6&is=69cb9f76&hm=68e52ac053de58ac41b294e3f62629293a032a51af6eba8cd898fae40e8d0458&",
    },
    {
        "name": "Pegassi Eventora",
        "real_name": "Lamborghini Reventon",
        "capacity": "35 кг",
        "speed": "315 км/ч",
        "fuel": "Premium",
        "rank": "3 Ранг",
        "image": "https://cdn.discordapp.com/attachments/1476538051416162415/1484134255788560426/image.png?ex=69ccf13c&is=69cb9fbc&hm=1ecd441518395f5e8ba4d211e9dd0083ca30daf975f8a318a280a7739598599c&",
    },
    {
        "name": "Ubermacht M8 Gran Coupe",
        "real_name": "BMW M8 Gran Coupe",
        "capacity": "100 кг",
        "speed": "315 км/ч",
        "fuel": "Premium",
        "rank": "3 Ранг",
        "image": "https://cdn.discordapp.com/attachments/1476538051416162415/1484134528522911774/image.png?ex=69ccf17d&is=69cb9ffd&hm=d690af9bc05ab9d1fb67b6c799740ca5aa1c5617faed73a93e333f45a2afea62&",
    },
    {
        "name": "Grotti Timucua SP3",
        "real_name": "Ferrari Daytona SP3",
        "capacity": "30 кг",
        "speed": "360 км/ч",
        "fuel": "Premium",
        "rank": "3 Ранг",
        "image": "https://cdn.discordapp.com/attachments/1476538051416162415/1484135036776218654/image.png?ex=69ccf1f6&is=69cba076&hm=427c772ca0d4eeb72a6a7b52c34e0fcc704ab39fc010f305dba629e7f0c08c16&",
    },
    {
        "name": "Buzzard S",
        "real_name": "Вертолёт",
        "capacity": "500 кг",
        "speed": "Max км/ч",
        "fuel": "Regular",
        "rank": "5 Ранг",
        "image": "https://cdn.discordapp.com/attachments/1476538051416162415/1487371753733754930/image.png?ex=69ccdae4&is=69cb8964&hm=8eb1aef5d4a09627cedd431b443779a36facd838037fa67f8b5a041c62df43f5&",
    },
    {
        "name": "Daimler ASG P-One",
        "real_name": "Mercedes-Benz Project One",
        "capacity": "5 кг",
        "speed": "370 км/ч",
        "fuel": "Premium",
        "rank": "3 Ранг",
        "image": "https://cdn.discordapp.com/attachments/1476538051416162415/1488563013547196556/image.png?ex=69cd3bd6&is=69cbea56&hm=d375f2ae917b166c1f59a0c991b07010db42049d2c36bbf2cc2e25f022733eef&",
    },
    {
        "name": "Daimler Runner",
        "real_name": "Mercedes-Benz Sprinter",
        "capacity": "180 кг",
        "speed": "230 км/ч",
        "fuel": "Premium",
        "rank": "3 Ранг",
        "image": "https://cdn.discordapp.com/attachments/1476538051416162415/1488564435839746138/image.png?ex=69cd3d29&is=69cbeba9&hm=2f53326ce184591e7c7c035e51170b542bb47e5edfed8f0a36f8cc14cc487519&",
    },
]



storage = BotStorage(
    applications_file=APPLICATIONS_FILE,
    panels_file=PANELS_FILE,
    giveaways_file=GIVEAWAYS_FILE,
    voice_rooms_file=VOICE_ROOMS_FILE,
    member_activity_file=MEMBER_ACTIVITY_FILE,
    legacy_applications_file=LEGACY_APPLICATIONS_FILE,
)
application_store = storage.applications
panel_store = storage.panels
giveaway_store = storage.giveaways
voice_room_store = storage.voice_rooms
member_activity_store = storage.member_activity


def save_applications() -> None:
    storage.schedule_save("applications")


def save_panels() -> None:
    storage.schedule_save("panels")


def save_giveaways() -> None:
    storage.schedule_save("giveaways")


def save_voice_rooms() -> None:
    storage.schedule_save("voice_rooms")


def save_member_activity() -> None:
    storage.schedule_save("member_activity")


def reload_applications() -> None:
    storage.reload("applications")


def reload_giveaways() -> None:
    storage.reload("giveaways")


def reload_voice_rooms() -> None:
    storage.reload("voice_rooms")


def reload_member_activity() -> None:
    storage.reload("member_activity")


def get_application_state(guild_id: int) -> dict[str, Any]:
    record = panel_store.setdefault(
        get_project_panel_key(APPLICATION_STATE_KEY, guild_id),
        {"closedServers": []},
    )
    closed_servers = record.get("closedServers", [])
    if not isinstance(closed_servers, list):
        closed_servers = []
    record["closedServers"] = [str(server) for server in closed_servers if str(server).strip()]
    return record


def get_default_closed_servers(guild_id: int | None) -> list[str]:
    project = get_project(guild_id)
    if project is None:
        return []
    return [
        str(option["key"])
        for option in project.get("application_options", [])
        if not option.get("default_open", True)
    ]


def apply_default_closed_application_servers() -> bool:
    changed = False
    for guild_id in PROJECT_GUILD_IDS:
        default_closed = set(get_default_closed_servers(guild_id))
        if not default_closed:
            continue
        state = get_application_state(guild_id)
        closed_servers = set(state.get("closedServers", []))
        updated = sorted(closed_servers | default_closed)
        if updated == sorted(closed_servers):
            continue
        state["closedServers"] = updated
        changed = True
    if changed:
        save_panels()
    return changed


def next_application_id() -> int:
    app_id = int(application_store.get("nextId", 1))
    application_store["nextId"] = app_id + 1
    return app_id


def next_giveaway_id() -> int:
    giveaway_id = int(giveaway_store.get("nextId", 1))
    giveaway_store["nextId"] = giveaway_id + 1
    return giveaway_id


def parse_iso(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.now(timezone.utc)


def member_has_any_role(member: discord.Member | None, role_ids: list[int]) -> bool:
    if member is None:
        return False
    member_role_ids = {role.id for role in member.roles}
    return any(role_id in member_role_ids for role_id in role_ids)


def get_guild_activity_store(guild_id: int) -> dict[str, Any]:
    guilds = member_activity_store.setdefault("guilds", {})
    guild_store = guilds.setdefault(str(guild_id), {"members": {}})
    guild_store.setdefault("members", {})
    return guild_store


def get_member_activity_record(guild_id: int, user_id: int) -> dict[str, Any]:
    guild_store = get_guild_activity_store(guild_id)
    members = guild_store.setdefault("members", {})
    record = members.setdefault(
        str(user_id),
        {
            "joinEvents": [],
            "leaveEvents": [],
            "knownRoleNames": [],
            "lastNickname": "",
            "lastUsername": "",
            "lastGlobalName": "",
            "boostEvents": [],
            "lastSeenAt": "",
            "lastAvatarUrl": "",
            "lastBannerUrl": "",
            "lastGuildAvatarUrl": "",
            "lastAvatarDecoration": "",
            "lastAccentColor": "",
        },
    )
    record.setdefault("joinEvents", [])
    record.setdefault("leaveEvents", [])
    record.setdefault("knownRoleNames", [])
    record.setdefault("boostEvents", [])
    record.setdefault("lastAvatarUrl", "")
    record.setdefault("lastBannerUrl", "")
    record.setdefault("lastGuildAvatarUrl", "")
    record.setdefault("lastAvatarDecoration", "")
    record.setdefault("lastAccentColor", "")
    return record


def merge_known_role_names(record: dict[str, Any], role_names: list[str]) -> None:
    existing = {str(name) for name in record.get("knownRoleNames", []) if str(name).strip()}
    for role_name in role_names:
        cleaned = str(role_name).strip()
        if cleaned:
            existing.add(cleaned)
    record["knownRoleNames"] = sorted(existing, key=str.casefold)


def get_member_role_names(member: discord.Member) -> list[str]:
    return [role.name for role in member.roles if role != member.guild.default_role]


def format_datetime_msk(value: datetime | None) -> str:
    if value is None:
        return "—"
    current = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    localized = current.astimezone(MSK_TZ)
    month_names = [
        "января",
        "февраля",
        "марта",
        "апреля",
        "мая",
        "июня",
        "июля",
        "августа",
        "сентября",
        "октября",
        "ноября",
        "декабря",
    ]
    month_name = month_names[localized.month - 1]
    return f"{localized.day} {month_name} {localized.year} г. • {localized.strftime('%H:%M')} MSK"


def format_relative_time(value: datetime | None) -> str:
    if value is None:
        return "—"
    current = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - current.astimezone(timezone.utc)
    seconds = max(int(delta.total_seconds()), 0)
    if seconds < 60:
        return "только что"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} мин. назад"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} ч. назад"
    days = hours // 24
    if days < 30:
        return f"{days} дн. назад"
    months = days // 30
    if months < 12:
        return f"{months} мес. назад"
    years = months // 12
    return f"{years} г. назад"


def format_member_event_line(event: dict[str, Any]) -> str:
    event_at = parse_iso(str(event.get("at", "")))
    reason = str(event.get("reason", "left"))
    reason_map = {
        "join": "вступил",
        "left": "вышел",
        "kick": "кикнут",
        "ban": "забанен",
    }
    actor_id = int(event.get("actorId", 0) or 0)
    audit_reason = str(event.get("auditReason", "")).strip()
    line = f"{format_datetime_msk(event_at)} — {reason_map.get(reason, reason)}"
    if actor_id:
        line += f" (<@{actor_id}>)"
    if audit_reason:
        line += f" — {audit_reason}"
    return line


def trim_embed_text(value: str, limit: int = 1024) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def update_member_activity_profile(member: discord.Member) -> None:
    record = get_member_activity_record(member.guild.id, member.id)
    record["lastNickname"] = member.display_name
    record["lastUsername"] = member.name
    record["lastGlobalName"] = member.global_name or ""
    record["lastSeenAt"] = datetime.now(timezone.utc).isoformat()
    record["lastAvatarUrl"] = str(member.display_avatar.url)
    guild_avatar = getattr(member, "guild_avatar", None)
    record["lastGuildAvatarUrl"] = str(guild_avatar.url) if guild_avatar is not None else ""
    banner = getattr(member, "banner", None)
    record["lastBannerUrl"] = str(banner.url) if banner is not None else ""
    avatar_decoration = getattr(member, "avatar_decoration", None)
    decoration_url = getattr(avatar_decoration, "url", None) if avatar_decoration is not None else None
    record["lastAvatarDecoration"] = str(decoration_url or getattr(member, "avatar_decoration_sku_id", "") or "")
    record["lastAccentColor"] = str(getattr(member, "accent_color", "") or "")
    merge_known_role_names(record, get_member_role_names(member))
    if member.premium_since is not None:
        premium_since_iso = member.premium_since.astimezone(timezone.utc).isoformat()
        boost_events = [str(item) for item in record.get("boostEvents", [])]
        if premium_since_iso not in boost_events:
            boost_events.append(premium_since_iso)
            record["boostEvents"] = boost_events


def record_member_join_activity(member: discord.Member) -> None:
    update_member_activity_profile(member)
    record = get_member_activity_record(member.guild.id, member.id)
    join_events = record.get("joinEvents", [])
    now_iso = datetime.now(timezone.utc).isoformat()
    if not join_events or abs((parse_iso(str(join_events[-1].get("at", ""))) - datetime.now(timezone.utc)).total_seconds()) > 5:
        join_events.append({"at": now_iso, "reason": "join"})
    record["joinEvents"] = join_events[-50:]
    save_member_activity()


def record_member_leave_activity(
    guild_id: int,
    user_id: int,
    *,
    reason: str,
    actor_id: int | None = None,
    audit_reason: str | None = None,
    role_names: list[str] | None = None,
    nickname: str = "",
    username: str = "",
    global_name: str = "",
) -> None:
    record = get_member_activity_record(guild_id, user_id)
    if role_names:
        merge_known_role_names(record, role_names)
    if nickname:
        record["lastNickname"] = nickname
    if username:
        record["lastUsername"] = username
    if global_name:
        record["lastGlobalName"] = global_name
    leave_events = record.get("leaveEvents", [])
    now = datetime.now(timezone.utc)
    payload = {
        "at": now.isoformat(),
        "reason": reason,
        "actorId": int(actor_id or 0),
        "auditReason": audit_reason or "",
    }
    if leave_events:
        last_event = leave_events[-1]
        last_at = parse_iso(str(last_event.get("at", "")))
        if (
            str(last_event.get("reason", "")) == reason
            and abs((now - last_at.astimezone(timezone.utc)).total_seconds()) <= 5
        ):
            leave_events[-1] = payload
            record["leaveEvents"] = leave_events[-50:]
            save_member_activity()
            return
    leave_events.append(payload)
    record["leaveEvents"] = leave_events[-50:]
    save_member_activity()


async def detect_leave_reason(guild: discord.Guild, user_id: int) -> tuple[str, int | None, str | None]:
    actor, entry = await fetch_audit_executor(guild, discord.AuditLogAction.ban, target_id=user_id)
    if entry is not None:
        return "ban", actor.id if actor is not None else None, entry.reason
    actor, entry = await fetch_audit_executor(guild, discord.AuditLogAction.kick, target_id=user_id)
    if entry is not None:
        return "kick", actor.id if actor is not None else None, entry.reason
    return "left", None, None


def get_voice_rooms() -> dict[str, dict[str, Any]]:
    rooms = voice_room_store.get("rooms", {})
    if not isinstance(rooms, dict):
        rooms = {}
        voice_room_store["rooms"] = rooms
    return rooms


def get_voice_room(channel_id: int) -> dict[str, Any] | None:
    return get_voice_rooms().get(str(channel_id))


def get_owned_voice_room(owner_id: int, guild_id: int | None = None) -> tuple[int, dict[str, Any]] | None:
    for channel_id, room in get_voice_rooms().items():
        try:
            if int(room.get("ownerId", 0)) != owner_id:
                continue
            if guild_id is not None and int(room.get("guildId", 0)) != guild_id:
                continue
            return int(channel_id), room
        except (TypeError, ValueError):
            continue
    return None


def set_voice_room(channel_id: int, payload: dict[str, Any]) -> None:
    get_voice_rooms()[str(channel_id)] = payload
    save_voice_rooms()


def remove_voice_room(channel_id: int) -> None:
    get_voice_rooms().pop(str(channel_id), None)
    save_voice_rooms()


def extract_user_id(raw_value: str) -> int | None:
    match = re.search(r"\d{15,22}", raw_value or "")
    if not match:
        return None
    try:
        return int(match.group(0))
    except ValueError:
        return None


def text_sendable(channel: Any) -> bool:
    return isinstance(channel, (discord.TextChannel, discord.Thread))


def prune_deque(values: deque[float], window: float, now: float | None = None) -> None:
    current = now if now is not None else time.time()
    while values and current - values[0] > window:
        values.popleft()


def prune_security_caches(now: float | None = None) -> None:
    current = now if now is not None else time.time()
    for guild_id in list(join_cache.keys()):
        prune_deque(join_cache[guild_id], 10, current)
        if not join_cache[guild_id]:
            join_cache.pop(guild_id, None)

    for cache_key in list(user_message_cache.keys()):
        prune_deque(user_message_cache[cache_key], 10, current)
        if not user_message_cache[cache_key]:
            user_message_cache.pop(cache_key, None)

    for cache_key in list(admin_action_cache.keys()):
        action_map = admin_action_cache[cache_key]
        for action_name in list(action_map.keys()):
            prune_deque(action_map[action_name], 10, current)
            if not action_map[action_name]:
                action_map.pop(action_name, None)
        if not action_map:
            admin_action_cache.pop(cache_key, None)

    for cache_key in list(spam_action_cache.keys()):
        if current - spam_action_cache[cache_key] > 10:
            spam_action_cache.pop(cache_key, None)


def is_protected_target(guild: discord.Guild, user_id: int) -> bool:
    if bot.user is not None and user_id == bot.user.id:
        return True
    return guild.owner_id == user_id


async def resolve_security_log_channel(guild: discord.Guild) -> discord.TextChannel | None:
    project = get_project(guild)
    if project is None:
        return None
    try:
        channel = guild.get_channel(int(project["security_log_channel_id"])) or await guild.fetch_channel(int(project["security_log_channel_id"]))
    except Exception:
        return None
    return channel if isinstance(channel, discord.TextChannel) else None


async def apply_timeout_to_member(member: discord.Member | None, duration_seconds: int, reason: str) -> bool:
    if member is None or member.guild is None or is_protected_target(member.guild, member.id):
        return False
    try:
        await member.timeout(timedelta(seconds=duration_seconds), reason=reason)
        return True
    except Exception:
        return False


async def fetch_audit_executor(
    guild: discord.Guild,
    action: discord.AuditLogAction,
    target_id: int | None = None,
) -> tuple[discord.Member | None, discord.AuditLogEntry | None]:
    try:
        async for entry in guild.audit_logs(limit=5, action=action):
            created_at = entry.created_at.replace(tzinfo=timezone.utc) if entry.created_at.tzinfo is None else entry.created_at
            if (datetime.now(timezone.utc) - created_at).total_seconds() > 15:
                continue
            if target_id is not None:
                entry_target_id = getattr(entry.target, "id", None)
                if entry_target_id != target_id:
                    continue
            user = entry.user
            if user is None:
                continue
            member = guild.get_member(user.id)
            if member is None:
                try:
                    member = await guild.fetch_member(user.id)
                except Exception:
                    member = None
            return member, entry
    except Exception:
        return None, None
    return None, None


def split_long_message(content: str, limit: int = 2000) -> list[str]:
    if len(content) <= limit:
        return [content]

    chunks: list[str] = []
    remaining = content
    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break

        split_at = remaining.rfind("\n", 0, limit)
        if split_at <= 0:
            split_at = limit
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip("\n")

    return [chunk for chunk in chunks if chunk]


async def cleanup_bot_messages(channel: discord.TextChannel, limit: int = 200) -> None:
    try:
        if bot.user is None:
            return
        await channel.purge(limit=limit, check=lambda message: message.author.id == bot.user.id)
    except Exception:
        pass


async def delete_message_safely(message: discord.Message) -> None:
    try:
        await message.delete()
        await asyncio.sleep(0.3)
    except Exception:
        pass


def parse_hours_input(raw_value: str) -> int | None:
    try:
        hours = int(raw_value.strip())
    except ValueError:
        return None
    if hours <= 0:
        return None
    return hours


def get_server_label(server: str) -> str:
    if server == FAMQ_SERVER_FRIEND_VERIFICATION:
        return f"{EMOJI_FRIEND_TEXT} Верификация для друзей"
    if server == FEDRU_APPLICATION_SERVER:
        return f"{EMOJI_ACCEPT_TEXT} ASIXEZ RU"
    if server == FAMQ_SERVER_DENVER:
        return "🏔️ Denver"
    if server == FAMQ_SERVER_ORLANDO:
        return f"{EMOJI_ORLANDO_TEXT} Orlando"
    if server == FAMQ_SERVER_SF:
        return f"{EMOJI_SF_TEXT} San Francisco"
    return f"{EMOJI_DETROIT_TEXT} Detroit"


def get_server_plain_label(server: str) -> str:
    if server == FAMQ_SERVER_FRIEND_VERIFICATION:
        return "Верификация для друзей"
    if server == FEDRU_APPLICATION_SERVER:
        return "ASIXEZ RU"
    if server == FAMQ_SERVER_DENVER:
        return "Denver"
    if server == FAMQ_SERVER_ORLANDO:
        return "Orlando"
    return "San Francisco" if server == FAMQ_SERVER_SF else "Detroit"


def get_server_tag(server: str) -> str:
    if server == FAMQ_SERVER_FRIEND_VERIFICATION:
        return "friend"
    if server == FEDRU_APPLICATION_SERVER:
        return "ru"
    if server == FAMQ_SERVER_DENVER:
        return "den"
    if server == FAMQ_SERVER_ORLANDO:
        return "orl"
    return "sf" if server == FAMQ_SERVER_SF else "det"


def is_friend_verification_application(server: str) -> bool:
    return server == FAMQ_SERVER_FRIEND_VERIFICATION


def get_project(guild_or_id: discord.Guild | int | None) -> dict[str, Any] | None:
    guild_id = guild_or_id.id if isinstance(guild_or_id, discord.Guild) else guild_or_id
    if guild_id is None:
        return None
    return PROJECT_CONFIGS.get(int(guild_id))


def get_project_name(guild_id: int | None) -> str:
    project = get_project(guild_id)
    return str(project.get("project_name")) if project else "ASIXEZ"


def is_allowed_guild_id(guild_id: int | None) -> bool:
    return guild_id is not None and int(guild_id) in PROJECT_CONFIGS


def get_project_panel_key(base_key: str, guild_id: int) -> str:
    return f"{base_key}:{guild_id}"


def normalize_theme_color(color: int | None = None) -> int:
    if color in {0x2ECC71, 0x1F8B4C, 0x0F7B53}:
        return COLOR_SOFT
    if color in {0xE74C3C, 0xF1C40F}:
        return COLOR_MUTED
    return COLOR


def make_embed(
    *,
    title: str | None = None,
    description: str | None = None,
    color: int | None = None,
    timestamp: datetime | None = None,
    banner: bool = False,
) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=normalize_theme_color(color),
        timestamp=timestamp,
    )
    if banner and FAMILY_BRAND_BANNER_URL:
        embed.set_image(url=FAMILY_BRAND_BANNER_URL)
    return embed


def get_project_application_option(server: str, guild_id: int | None = None) -> dict[str, Any] | None:
    if guild_id is not None:
        project = get_project(guild_id)
        if project is not None:
            for option in project.get("application_options", []):
                if option["key"] == server:
                    return option
    for project in PROJECT_CONFIGS.values():
        for option in project.get("application_options", []):
            if option["key"] == server:
                return option
    return None


def get_visible_application_options(guild_id: int | None) -> list[dict[str, Any]]:
    project = get_project(guild_id)
    if project is None:
        return []
    return [
        option
        for option in project.get("application_options", [])
        if option.get("visible_in_select", True) and is_application_open(option["key"], guild_id)
    ]


def get_manageable_application_options(guild_id: int | None) -> list[dict[str, Any]]:
    project = get_project(guild_id)
    if project is None:
        return []
    return [
        option
        for option in project.get("application_options", [])
        if option["key"] != FAMQ_SERVER_FRIEND_VERIFICATION
    ]


def get_server_recruiter_roles(server: str, guild_id: int | None = None) -> list[int]:
    option = get_project_application_option(server, guild_id)
    if option is None:
        return []
    return list(option.get("recruiter_roles", []))


def get_server_accept_role_id(server: str, guild_id: int | None = None) -> int | None:
    option = get_project_application_option(server, guild_id)
    if option is None:
        return None
    return option.get("accept_role_id")


def get_server_manager_roles(server: str, guild_id: int | None = None) -> list[int]:
    option = get_project_application_option(server, guild_id)
    if option is None:
        return [APPLICATION_CONTROL_ROLE_ID]
    manager_roles = option.get("manager_roles")
    if isinstance(manager_roles, list) and manager_roles:
        return [int(role_id) for role_id in manager_roles if int(role_id)]
    return [APPLICATION_CONTROL_ROLE_ID]


def get_application_control_roles(guild_id: int | None) -> list[int]:
    role_ids = {APPLICATION_CONTROL_ROLE_ID}
    for option in get_manageable_application_options(guild_id):
        role_ids.update(int(role_id) for role_id in option.get("manager_roles", []) if int(role_id))
    return sorted(role_ids)


def is_application_open(server: str, guild_id: int | None) -> bool:
    if guild_id is None:
        return True
    state = get_application_state(int(guild_id))
    return server not in set(state.get("closedServers", []))


def set_application_open(server: str, guild_id: int, is_open: bool) -> None:
    state = get_application_state(guild_id)
    closed_servers = set(state.get("closedServers", []))
    if is_open:
        closed_servers.discard(server)
    else:
        closed_servers.add(server)
    state["closedServers"] = sorted(closed_servers)
    save_panels()


def can_manage_application(member: discord.Member | None, server: str, guild_id: int | None = None) -> bool:
    if member is None:
        return False
    return member_has_any_role(member, get_server_recruiter_roles(server, guild_id or member.guild.id))


async def notify_unwhitelisted_guild(guild: discord.Guild) -> None:
    notice = (
        "Этот сервер отсутствует в whitelist бота.\n"
        f"Чтобы получить доступ, свяжитесь с: `{WHITELIST_CONTACT_ID}`"
    )
    candidate_channels: list[discord.abc.MessageableChannel] = []
    if isinstance(guild.system_channel, discord.TextChannel):
        candidate_channels.append(guild.system_channel)
    for channel in guild.text_channels:
        if channel not in candidate_channels:
            candidate_channels.append(channel)

    for channel in candidate_channels:
        try:
            await channel.send(notice)
            return
        except Exception:
            continue


intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True
intents.voice_states = True
if hasattr(intents, "moderation"):
    intents.moderation = True
if hasattr(intents, "bans"):
    intents.bans = True

bot = commands.Bot(command_prefix="!", intents=intents)
startup_done = False
views_restored = False
restart_task: asyncio.Task | None = None
command_sync_done = False
giveaway_tasks: dict[int, asyncio.Task] = {}
join_cache: dict[int, deque[float]] = {}
user_message_cache: dict[tuple[int, int], deque[float]] = {}
admin_action_cache: dict[tuple[int, int], dict[str, deque[float]]] = {}
spam_action_cache: dict[tuple[int, int], float] = {}
kick_restriction_cache: dict[tuple[int, int], dict[str, Any]] = {}
join_alert_state: dict[int, dict[str, float]] = {}
application_action_locks: dict[int, asyncio.Lock] = {}


def build_panel_embed(guild_id: int) -> discord.Embed:
    project = get_project(guild_id)
    visible_options = get_visible_application_options(guild_id)
    open_lines = [
        f"{option.get('emoji_text', '•')} **{option['label']}**"
        for option in visible_options
    ]
    open_block = "\n".join(open_lines) if open_lines else f"{EMOJI_REJECT_TEXT} `набор временно закрыт`"
    if project and project.get("panel_mode") == "single_server":
        description = "\n".join(
            [
                f"## {EMOJI_ACCEPT_TEXT} Заявки в ASIXEZ",
                "",
                f"{EMOJI_REVIEW_TEXT} **Доступно сейчас**",
                open_block,
                "",
                f"{EMOJI_CALL_TEXT} Ответ и приглашение на обзвон придут прямо в вашу ветку заявки.",
                "",
                f"{EMOJI_REJECT_TEXT} Если кнопка ниже недоступна, набор временно закрыт.",
            ]
        )
    else:
        description = "\n".join(
            [
                f"## {EMOJI_ACCEPT_TEXT} Заявки в ASIXEZ",
                "",
                f"{EMOJI_REVIEW_TEXT} **Открытые направления**",
                open_block,
                "",
                f"{EMOJI_CALL_TEXT} После подачи бот создаст отдельную ветку, где рекрутеры рассмотрят анкету и вызовут на обзвон.",
                f"{EMOJI_FRIEND_TEXT} Верификация для друзей находится в этом же меню.",
                f"{EMOJI_REJECT_TEXT} Если нужного сервера нет в списке, значит набор закрыт.",
            ]
        )
    embed = make_embed(description=description, color=COLOR_PANEL)
    embed.set_author(name=project.get("project_name", "ASIXEZ") if project else "ASIXEZ")
    embed.set_footer(text="ASIXEZ • Application Center • обычно 20-60 минут")
    return embed


def build_voice_panel_embed() -> discord.Embed:
    description = "\n".join(
        [
            "## Управление временной комнатой",
            "",
            f"{VOICE_EMOJI_ADD_SLOT_TEXT} Добавить 1 слот",
            f"{VOICE_EMOJI_REMOVE_SLOT_TEXT} Убрать 1 слот",
            f"{VOICE_EMOJI_LOCK_TEXT} Открыть или закрыть комнату",
            f"{VOICE_EMOJI_SPEAK_TEXT} Выдать или забрать право говорить",
            f"{VOICE_EMOJI_KICK_TEXT} Исключить пользователя",
            f"{VOICE_EMOJI_BITRATE_TEXT} Изменить битрейт",
            f"{VOICE_EMOJI_SET_SLOTS_TEXT} Выставить лимит слотов",
            f"{VOICE_EMOJI_TRANSFER_TEXT} Передать владение",
            f"{VOICE_EMOJI_RENAME_TEXT} Переименовать комнату",
            f"{VOICE_EMOJI_ACCESS_TEXT} Выдать или забрать доступ",
            "",
            "Создание временных комнат доступно для всех участников.",
        ]
    )
    embed = make_embed(description=description, color=COLOR_PANEL, banner=True)
    embed.set_thumbnail(url=VOICE_PANEL_THUMBNAIL_URL)
    embed.set_footer(text="ASIXEZ • Voice Control")
    return embed


def build_application_embed(application: dict[str, Any], applicant_tag: str) -> discord.Embed:
    if is_friend_verification_application(application["server"]):
        status_line = ""
        if application.get("claimedBy"):
            status_line = f"\n\n**Заявка закреплена за:** <@{application['claimedBy']}>"
        embed = make_embed(
            title=f"Верификация для друзей #{application['id']}",
            description="\n\n".join(
                [
                    f"{EMOJI_REVIEW_TEXT} **Заявитель:** {applicant_tag}",
                    f"{EMOJI_FRIEND_TEXT} **Тип:** {get_server_label(application['server'])}",
                    build_answer_block("01. Ваше имя, фамилия в игре", application.get("friendNameGame") or "—"),
                    build_answer_block("02. В какой семье вы состоите?", application.get("friendFamily") or "—"),
                ]
            )
            + status_line,
            color=COLOR_PANEL,
            timestamp=parse_iso(application.get("submittedAt")),
        )
        embed.set_footer(text=f"ID заявителя: {application['applicantId']}")
        return embed

    status_line = ""
    if application.get("claimedBy"):
        status_line = f"\n\n**Заявка закреплена за:** <@{application['claimedBy']}>"
    embed = make_embed(
        title=f"Заявка #{application['id']}",
        description="\n\n".join(
            [
                f"{EMOJI_REVIEW_TEXT} **Заявитель:** {applicant_tag}",
                f"{get_server_label(application['server'])} **Сервер:** {get_server_plain_label(application['server'])}",
                build_answer_block("01. Имя IRL", application.get("irlName") or extract_legacy_irl_name(application.get("nameAge", "")) or "—"),
                build_answer_block("02. Возраст IRL", application.get("ageIrl") or application.get("nameAge") or "—"),
                build_answer_block("03. Левел, онлайн и часовой пояс", application.get("levelOnline") or "—"),
                build_answer_block("04. Фракция", application.get("fraction") or "—"),
                build_answer_block("05. Ник и Static-ID", application.get("nameStatic") or "—"),
            ]
        )
        + status_line,
        color=COLOR_PANEL,
        timestamp=parse_iso(application.get("submittedAt")),
        )
    embed.set_footer(text=f"ID заявителя: {application['applicantId']}")
    return embed


def build_dm_embed(title: str, description: str) -> discord.Embed:
    return make_embed(
        title=title,
        description=description,
        color=COLOR_SOFT,
        timestamp=datetime.now(timezone.utc),
        banner=True,
    )


STAFF_ROLE_GROUPS: tuple[tuple[str, int, str], ...] = (
    ("Leaders", FAMQ_FRIEND_VERIFY_ROLE_1_ID, EMOJI_ACCEPT_TEXT),
    ("Dep Leaders", FAMQ_DEP_LEADER_ROLE_ID, EMOJI_REVIEW_TEXT),
    ("Curators", FAMQ_CURATOR_ROLE_ID, EMOJI_CALL_TEXT),
    ("Boss Famq", FAMQ_BOSS_ROLE_ID, EMOJI_DETROIT_TEXT),
    ("High Famq", FAMQ_HIGH_ROLE_ID, EMOJI_SF_TEXT),
    ("Recruits", FAMQ_RECRUITER_ROLE_ID, EMOJI_ORLANDO_TEXT),
)

NICKNAME_RULES: tuple[tuple[int, str], ...] = (
    (FAMQ_DEP_LEADER_ROLE_ID, "Dep"),
    (FAMQ_CURATOR_ROLE_ID, "Curator"),
    (FAMQ_BOSS_ROLE_ID, "Boss"),
    (FAMQ_HIGH_ROLE_ID, "High"),
    (FAMQ_RECRUITER_ROLE_ID, "Rec"),
    (APPLICATION_EXTRA_ACCEPT_ROLE_ID, "ASX"),
)


def format_member_mentions_for_role(guild: discord.Guild, role_id: int) -> str:
    role = guild.get_role(int(role_id))
    if role is None:
        return "`роль не найдена`"
    members = sorted([member for member in role.members if not member.bot], key=lambda member: member.display_name.lower())
    if not members:
        return "—"
    lines = [f"- {member.mention}" for member in members]
    return trim_embed_text("\n".join(lines), limit=1024)


def build_staff_panel_embed(guild: discord.Guild) -> discord.Embed:
    embed = make_embed(
        title=f"{EMOJI_ACCEPT_TEXT} Состав семьи ASIXEZ",
        description=(
            "Актуальный список старшего состава, кураторов и рекрутеров.\n"
            "Панель обновляется автоматически после каждого рестарта бота."
        ),
        color=COLOR_PANEL,
        timestamp=datetime.now(timezone.utc),
    )
    for title, role_id, emoji_text in STAFF_ROLE_GROUPS:
        embed.add_field(
            name=f"{emoji_text} {title}",
            value=format_member_mentions_for_role(guild, role_id),
            inline=False,
        )
    embed.set_footer(text=f"ASIXEZ • обновлено {format_log_time_msk()}")
    return embed


def get_required_nickname_prefix(member: discord.Member) -> str | None:
    role_ids = {role.id for role in member.roles}
    if FAMQ_FRIEND_VERIFY_ROLE_1_ID in role_ids:
        return None
    for role_id, prefix in NICKNAME_RULES:
        if int(role_id) in role_ids:
            return prefix
    return None


def nickname_matches_required_format(member: discord.Member, prefix: str) -> bool:
    pattern = rf"^{re.escape(prefix)}\s*\|\s*.+?\s*\|\s*\d{{1,12}}$"
    return re.match(pattern, member.display_name.strip(), flags=re.IGNORECASE) is not None


def build_formatted_nickname(prefix: str, irl_name: str, static_id: str) -> str:
    cleaned_name = " ".join((irl_name or "Имя").strip().split())[:20] or "Имя"
    cleaned_static = re.sub(r"\D+", "", static_id or "")[:12] or "Static-ID"
    suffix = f" | {cleaned_static}"
    max_name_length = max(1, 32 - len(f"{prefix} | ") - len(suffix))
    return f"{prefix} | {cleaned_name[:max_name_length]}{suffix}"[:32]


def get_members_with_bad_nicknames(guild: discord.Guild) -> list[tuple[discord.Member, str]]:
    bad_members: list[tuple[discord.Member, str]] = []
    for member in guild.members:
        if member.bot:
            continue
        prefix = get_required_nickname_prefix(member)
        if prefix is None:
            continue
        if not nickname_matches_required_format(member, prefix):
            bad_members.append((member, prefix))
    bad_members.sort(key=lambda item: (item[1], item[0].display_name.lower()))
    return bad_members


def build_nickname_report_embed(guild: discord.Guild, bad_members: list[tuple[discord.Member, str]]) -> discord.Embed:
    if not bad_members:
        embed = make_embed(
            title=f"{EMOJI_ACCEPT_TEXT} Проверка никнеймов",
            description="Все проверенные участники стоят по форме. Красота, порядок, дышим ровно.",
            color=COLOR_SOFT,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text=f"ASIXEZ • {format_log_time_msk()}")
        return embed

    lines = [
        f"- {member.mention} → `{prefix} | Имя РЛ | Static-ID`"
        for member, prefix in bad_members[:35]
    ]
    if len(bad_members) > 35:
        lines.append(f"...и ещё {len(bad_members) - 35} участник(ов).")
    embed = make_embed(
        title=f"{EMOJI_REVIEW_TEXT} Проверка никнеймов",
        description=(
            "Ниже участники, у которых ник не по форме.\n"
            "Пожалуйста, поставьте ник по указанному шаблону. Если не получается, нажмите кнопку ниже, бот поможет сам.\n\n"
            + "\n".join(lines)
        ),
        color=COLOR_MUTED,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text=f"ASIXEZ • найдено: {len(bad_members)} • {format_log_time_msk()}")
    return embed


def build_log_embed(description: str) -> discord.Embed:
    return make_embed(
        title="Лог заявок — ASIXEZ",
        description=description,
        color=COLOR,
        timestamp=datetime.now(timezone.utc),
    )
def build_log_embed_for_guild(guild_id: int, description: str) -> discord.Embed:
    project = get_project(guild_id)
    if project is None:
        return build_log_embed(description)
    return make_embed(
        title=f"Лог заявок — {project['project_name']}",
        description=description,
        color=COLOR,
        timestamp=datetime.now(timezone.utc),
    )


def has_usi_access(member: discord.Member | None) -> bool:
    return member_has_any_role(member, USI_ALLOWED_ROLE_IDS)


def format_roles_for_usi(guild: discord.Guild, member: discord.Member | None, record: dict[str, Any]) -> str:
    if member is not None:
        role_mentions = [role.mention for role in reversed(member.roles) if role != guild.default_role]
        if role_mentions:
            return ", ".join(role_mentions)
    known_role_names = [str(name) for name in record.get("knownRoleNames", []) if str(name).strip()]
    if known_role_names:
        return trim_embed_text(", ".join(f"`{name}`" for name in known_role_names))
    return "Роли ещё не зафиксированы."


def build_customization_lines(member: discord.Member | None, user: discord.abc.User) -> str:
    lines = [f"[Аватар]({user.display_avatar.url})"]
    guild_avatar = getattr(member, "guild_avatar", None) if member is not None else None
    if guild_avatar is not None:
        lines.append(f"[Серверный аватар]({guild_avatar.url})")
    banner = getattr(user, "banner", None)
    if banner is not None:
        lines.append(f"[Баннер]({banner.url})")
    avatar_decoration = getattr(user, "avatar_decoration", None)
    avatar_decoration_sku_id = getattr(user, "avatar_decoration_sku_id", None)
    if avatar_decoration is not None:
        decoration_url = getattr(avatar_decoration, "url", None)
        if decoration_url:
            lines.append(f"[Украшение]({decoration_url})")
    elif avatar_decoration_sku_id:
        lines.append(f"Украшение: `{avatar_decoration_sku_id}`")
    if getattr(user, "accent_color", None):
        lines.append(f"Акцент: `{str(user.accent_color)}`")
    if getattr(user, "global_name", None):
        lines.append(f"Неймплейс: `{user.global_name}`")
    return trim_embed_text(" • ".join(lines))


def build_join_history_text(record: dict[str, Any]) -> str:
    join_events = list(record.get("joinEvents", []))
    leave_events = list(record.get("leaveEvents", []))
    summary = [
        f"Вступлений: **{len(join_events)}**",
        f"Выходов: **{len(leave_events)}**",
    ]
    recent_events = leave_events[-3:]
    if recent_events:
        summary.append("")
        summary.append("Последние выходы:")
        summary.extend([f"• {format_member_event_line(event)}" for event in reversed(recent_events)])
    elif join_events:
        summary.append("")
        summary.append(f"Последний вход: {format_member_event_line(join_events[-1])}")
    else:
        summary.append("")
        summary.append("История входов пока не зафиксирована.")
    return trim_embed_text("\n".join(summary))


def build_usi_embed(guild: discord.Guild, member: discord.Member | None, user: discord.abc.User, record: dict[str, Any]) -> discord.Embed:
    created_at = getattr(user, "created_at", None)
    joined_at = member.joined_at if member is not None else (parse_iso(str(record.get("joinEvents", [])[-1].get("at"))) if record.get("joinEvents") else None)
    premium_since = member.premium_since if member is not None else None
    nickname = member.display_name if member is not None else (record.get("lastNickname") or record.get("lastUsername") or user.name)
    title = f"{EMOJI_REVIEW_TEXT} {nickname} ({user.name} • {user.id})"
    embed = make_embed(color=COLOR, timestamp=datetime.now(timezone.utc))
    embed.description = title
    embed.add_field(
        name="Создан",
        value=f"{format_datetime_msk(created_at)}\n{format_relative_time(created_at)}",
        inline=True,
    )
    embed.add_field(
        name="Заходы",
        value=build_join_history_text(record),
        inline=True,
    )
    embed.add_field(
        name="Буст",
        value=(
            f"{format_datetime_msk(premium_since)}\n{format_relative_time(premium_since)}"
            if premium_since is not None
            else "Не бустит сервер."
        ),
        inline=True,
    )
    embed.add_field(
        name=f"Роли ({len([name for name in record.get('knownRoleNames', []) if str(name).strip()])})",
        value=format_roles_for_usi(guild, member, record),
        inline=False,
    )
    embed.add_field(
        name="Кастомизация",
        value=build_customization_lines(member, user),
        inline=False,
    )
    last_join_text = format_datetime_msk(joined_at) if joined_at is not None else "—"
    embed.set_footer(text=f"{guild.name} • ID: {user.id} • Последний вход: {last_join_text}")
    embed.set_thumbnail(url=user.display_avatar.url)
    return embed


class CopyDiscordIdView(discord.ui.View):
    def __init__(self, target_user_id: int):
        super().__init__(timeout=None)
        self.target_user_id = target_user_id

    @discord.ui.button(label="Копировать Discord-ID", style=discord.ButtonStyle.secondary)
    async def copy_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_message(
            f"Discord ID пользователя:\n```text\n{self.target_user_id}\n```",
            ephemeral=True,
        )


class NicknameSelfFixModal(discord.ui.Modal):
    def __init__(self, prefix: str):
        super().__init__(title="Изменить себе никнейм", timeout=180)
        self.prefix = prefix
        self.irl_name = discord.ui.TextInput(
            label="Ваше имя в РЛ",
            max_length=40,
            required=True,
        )
        self.static_id = discord.ui.TextInput(
            label="Ваш Static-ID",
            max_length=20,
            required=True,
        )
        self.add_item(self.irl_name)
        self.add_item(self.static_id)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Не удалось найти вас на сервере.", ephemeral=True)
            return

        prefix = get_required_nickname_prefix(interaction.user)
        if prefix is None:
            await interaction.response.send_message("Для ваших ролей форма ника не требуется.", ephemeral=True)
            return

        static_id = re.sub(r"\D+", "", str(self.static_id))
        if not static_id:
            await interaction.response.send_message("Static-ID должен содержать цифры.", ephemeral=True)
            return

        new_nick = build_formatted_nickname(prefix, str(self.irl_name), static_id)
        try:
            await interaction.user.edit(nick=new_nick, reason="Nickname self-fix form")
        except Exception:
            await interaction.response.send_message(
                "Не удалось изменить ник. Проверьте, что роль бота выше вашей роли, или обратитесь к старшему.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(f"Готово, поставил ник: **{new_nick}**", ephemeral=True)


class NicknameSelfFixView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Изменить себе никнейм",
        style=discord.ButtonStyle.secondary,
        custom_id="famq_self_fix_nickname",
    )
    async def fix_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Не удалось найти вас на сервере.", ephemeral=True)
            return
        prefix = get_required_nickname_prefix(interaction.user)
        if prefix is None:
            await interaction.response.send_message("Для ваших ролей форма ника не требуется.", ephemeral=True)
            return
        await interaction.response.send_modal(NicknameSelfFixModal(prefix))


class ApplicationHistoryView(discord.ui.View):
    def __init__(self, guild_id: int, target_user_id: int, requester_id: int):
        super().__init__(timeout=900)
        self.guild_id = guild_id
        self.target_user_id = target_user_id
        self.requester_id = requester_id

    @discord.ui.button(label="История по заявкам", style=discord.ButtonStyle.secondary)
    async def history_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        member = interaction.user if isinstance(interaction.user, discord.Member) else None
        if interaction.user.id != self.requester_id and not has_usi_access(member):
            await interaction.response.send_message("Недостаточно прав для просмотра истории заявок.", ephemeral=True)
            return

        reload_applications()
        items = [
            app
            for app in application_store.get("items", {}).values()
            if int(app.get("guildId", 0)) == self.guild_id and int(app.get("applicantId", 0)) == self.target_user_id
        ]
        if not items:
            await interaction.response.send_message("Пользователь не подал ещё ни одной заявки.", ephemeral=True)
            return

        items.sort(key=lambda app: parse_iso(str(app.get("submittedAt", ""))), reverse=True)
        lines: list[str] = []
        for app in items[:15]:
            submitted = format_datetime_msk(parse_iso(str(app.get("submittedAt", ""))))
            decided_at = parse_iso(str(app.get("decidedAt", ""))) if app.get("decidedAt") else None
            decided_text = format_datetime_msk(decided_at) if decided_at is not None else "ещё не обработана"
            lines.append(
                "\n".join(
                    [
                        f"**#{app['id']}** — {get_server_plain_label(str(app.get('server', '')))}",
                        f"Статус: `{app.get('status', 'unknown')}`",
                        f"Подана: {submitted}",
                        f"Решение: {decided_text}",
                    ]
                )
            )

        embed = make_embed(
            title=f"{EMOJI_REVIEW_TEXT} История заявок пользователя",
            description="\n\n".join(lines),
            color=COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class SecurityActionView(discord.ui.View):
    def __init__(self, target_user_id: int):
        super().__init__(timeout=None)
        self.target_user_id = target_user_id

    async def _guard(self, interaction: discord.Interaction) -> discord.Member | None:
        if interaction.guild is None:
            await interaction.response.send_message("Сервер не найден.", ephemeral=True)
            return None
        member = interaction.user if isinstance(interaction.user, discord.Member) else None
        if member is None or not member.guild_permissions.manage_guild:
            await interaction.response.send_message("Недостаточно прав для использования этих кнопок.", ephemeral=True)
            return None
        target = interaction.guild.get_member(self.target_user_id)
        if target is None:
            try:
                target = await interaction.guild.fetch_member(self.target_user_id)
            except Exception:
                target = None
        if target is None:
            await interaction.response.send_message("Пользователь не найден на сервере.", ephemeral=True)
            return None
        if is_protected_target(interaction.guild, target.id):
            await interaction.response.send_message("К этому пользователю нельзя применять действия.", ephemeral=True)
            return None
        return target

    @discord.ui.button(label="Mute", emoji="🔇", style=discord.ButtonStyle.secondary)
    async def mute_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        target = await self._guard(interaction)
        if target is None:
            return
        applied = await apply_timeout_to_member(target, 10 * 60, f"Security log mute by {interaction.user}")
        await interaction.response.send_message(
            "Пользователь отправлен в timeout на 10 минут." if applied else "Не удалось выдать timeout.",
            ephemeral=True,
        )

    @discord.ui.button(label="Kick", emoji="🔨", style=discord.ButtonStyle.secondary)
    async def kick_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        target = await self._guard(interaction)
        if target is None:
            return
        try:
            await target.kick(reason=f"Security log kick by {interaction.user}")
            await interaction.response.send_message("Пользователь кикнут.", ephemeral=True)
        except Exception:
            await interaction.response.send_message("Не удалось кикнуть пользователя.", ephemeral=True)

    @discord.ui.button(label="Ban", emoji="🚫", style=discord.ButtonStyle.secondary)
    async def ban_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        target = await self._guard(interaction)
        if target is None:
            return
        try:
            await interaction.guild.ban(target, reason=f"Security log ban by {interaction.user}", delete_message_days=0)
            await interaction.response.send_message("Пользователь забанен.", ephemeral=True)
        except Exception:
            await interaction.response.send_message("Не удалось забанить пользователя.", ephemeral=True)


class KickRestrictionReviewView(discord.ui.View):
    def __init__(self, actor_id: int):
        super().__init__(timeout=None)
        self.actor_id = actor_id

    async def _guard(self, interaction: discord.Interaction) -> bool:
        member = interaction.user if isinstance(interaction.user, discord.Member) else None
        if interaction.guild is None or member is None or not member.guild_permissions.manage_guild:
            await interaction.response.send_message("Недостаточно прав для проверки.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Да, вернуть", style=discord.ButtonStyle.secondary, custom_id="kick_restriction_restore")
    async def restore_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await self._guard(interaction):
            return
        restored = await restore_kick_restriction(interaction.guild, self.actor_id, f"Approved by {interaction.user}")
        await interaction.response.edit_message(
            content=None,
            view=None,
            embed=build_security_embed(
                title="✅ Kick restriction approved",
                color=0x2ECC71,
                user_id=self.actor_id,
                action_label="Mass Kick Review",
                count_label="Manual check completed",
                result_label="Moderation roles restored" if restored else "Nothing to restore or restore failed",
                extra_lines=[f"Checked by: <@{interaction.user.id}>"],
            ),
        )

    @discord.ui.button(label="Нет, не возвращать", style=discord.ButtonStyle.secondary, custom_id="kick_restriction_keep")
    async def keep_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await self._guard(interaction):
            return
        kick_restriction_cache.pop(self.actor_id, None)
        await interaction.response.edit_message(
            content=None,
            view=None,
            embed=build_security_embed(
                title="🚫 Kick restriction rejected",
                color=0xE74C3C,
                user_id=self.actor_id,
                action_label="Mass Kick Review",
                count_label="Manual check completed",
                result_label="Moderation roles were not restored",
                extra_lines=[f"Checked by: <@{interaction.user.id}>"],
            ),
        )


def build_security_embed(
    *,
    title: str,
    color: int,
    user_id: int | None,
    action_label: str,
    count_label: str,
    result_label: str,
    extra_lines: list[str] | None = None,
    source_message_id: int | None = None,
) -> discord.Embed:
    embed = make_embed(title=title, color=color, timestamp=datetime.now(timezone.utc))
    embed.add_field(
        name="👤 User",
        value=(f"<@{user_id}> (`{user_id}`)" if user_id else "Не определён"),
        inline=False,
    )
    embed.add_field(name="📌 Action", value=action_label, inline=True)
    embed.add_field(name="📊 Count", value=count_label, inline=True)
    embed.add_field(name="⚡ Result", value=result_label, inline=False)
    if extra_lines:
        embed.add_field(name="🧾 Details", value="\n".join(extra_lines)[:1024], inline=False)
    if source_message_id:
        embed.add_field(name="🆔 Message ID", value=str(source_message_id), inline=False)
    return embed


def build_result_embed(app: dict[str, Any], recruiter_user_id: int, verdict: str, reject_reason: str | None = None) -> discord.Embed:
    is_accepted = verdict == "accepted"
    is_friend_verification = is_friend_verification_application(app["server"])
    embed = make_embed(
        color=COLOR_SOFT if is_accepted else COLOR_MUTED,
        timestamp=datetime.now(timezone.utc),
    )
    if FAMQ_RESULT_GIF:
        embed.set_thumbnail(url=FAMQ_RESULT_GIF)
    embed.set_footer(text=f"{get_project_name(int(app.get('guildId', 0)))} • {get_server_plain_label(app['server'])}")

    if is_accepted:
        embed.title = f"{EMOJI_ACCEPT_TEXT} {'Верификация одобрена' if is_friend_verification else 'Заявка принята'}"
        embed.description = "\n".join(
            [
                f"Заявка от пользователя <@{app['applicantId']}>",
                "",
                (
                    f"Верификация друга семьи была **одобрена**. {EMOJI_REVIEW_TEXT}"
                    if is_friend_verification
                    else f"На вступление в семью была **принята**. {EMOJI_REVIEW_TEXT}"
                ),
                "",
                f"**Рассматривал заявку:** <@{recruiter_user_id}>",
                "",
                (
                    "> После выдачи роли поставьте ник по форме, указанной в личных сообщениях."
                    if is_friend_verification
                    else "> Никнейм на сервере: ASIXEZ | Ник | Статик."
                ),
            ]
        )
    else:
        embed.title = f"{EMOJI_REJECT_TEXT} {'Верификация отклонена' if is_friend_verification else 'Заявка отклонена'}"
        embed.description = "\n".join(
            [
                f"Заявка от пользователя <@{app['applicantId']}>",
                "",
                (
                    "Верификация друга семьи была **отклонена**. ❌"
                    if is_friend_verification
                    else "На вступление в семью была **отклонена**. ❌"
                ),
                "",
                f"**Причина:** {reject_reason or 'не указана'}",
                f"**Рассматривал заявку:** <@{recruiter_user_id}>",
            ]
        )

    return embed


def build_info_embed() -> discord.Embed:
    description = "\n".join(
        [
            f"# {EMOJI_ACCEPT_TEXT} Добро пожаловать в семью **ASIXEZ**",
            "*Ты попал не просто в Discord — ты у ворот одной из самых закрытых и сильных Crime-семей на **Majestic RP**. Здесь нет случайных людей. Уважай место, куда вошёл.*",
            "",
            f"> **{EMOJI_DETROIT_TEXT} Основные правила:**",
            "> - Уважение — прежде всего.",
            "> - Оскорбления, токсичность и провокации наказуемо; **BAN / PERMBAN**",
            "",
            f"> {EMOJI_REVIEW_TEXT} **Конфиденциальность.**",
            "> - Всё, что происходит в семье — остаётся в семье. Разглашение информации любого вида (Слив чатов, личных переписок, любых чатов и т.п.) наказуемо; **BAN / PERMBAN**",
            "",
            f"> **{EMOJI_REJECT_TEXT} РП поведение — всегда.**",
            "> - Даже вне игры, ты остаёшься адекватным. Никакого флуда без причины, наказуемо; **WARN / MUTE / BAN**",
            "",
            f"> **{EMOJI_CALL_TEXT} Активность и лояльность.**",
            "> - За неактив без предупреждения — вылет. За предательство — забудем, что ты был, наказуемо; **BAN**",
            "",
            f"> **{EMOJI_DETROIT_TEXT} Приказы старших — не обсуждаются.**",
            "> - Иерархия соблюдается. Вопросы — через личку или офицеров, наказуемо; **WARN / BAN / PERMBAN**",
            "",
            f"> {EMOJI_ACCEPT_TEXT} **Заявки / Вступление:**",
            "> - Чтобы вступить в семью на сервере **DETROIT** нужно подать заявку тут — <#1466147735873786200>",
            "> **Старшие рассмотрят вашу заявку так скоро как получится. После принятия заявки поставьте ник по форме —**",
            "> - Имя Фамилия (В игре)",
            "",
            "**Добро пожаловать домой.**",
            "**Семья — навсегда.**",
            "***ASIXEZ.***",
        ]
    )
    return discord.Embed(description=description, color=COLOR)


def build_promo_embed() -> discord.Embed:
    description = "\n".join(
        [
            f"{EMOJI_REVIEW_TEXT} **Хочешь играть на Majestic RP?**",
            "",
            f"{EMOJI_ACCEPT_TEXT} Введите в чат промокод: **`/promo FED`**",
            f"{EMOJI_REVIEW_TEXT} Или зарегистрируйтесь по ссылке:",
            "https://majestic-rp.ru/register?utm_campaign=FED",
            "",
            "*Поддержи семью — используй промокод при регистрации!*",
        ]
    )
    embed = discord.Embed(description=description, color=COLOR)
    if FAMQ_PROMO_IMAGE_URL:
        embed.set_image(url=FAMQ_PROMO_IMAGE_URL)
    return embed


def build_contract_embeds() -> list[discord.Embed]:
    intro = discord.Embed(
        description="\n".join(
            [
                f"# {EMOJI_REVIEW_TEXT} Семейные Контракты и получение денег.",
                "- **Семейные контракты это** — Возможность прокачки уровня семьи, и заработка для себя.",
                "",
                "- За контракты, за которые функционально дают деньги на баланс семьи, а не игроку — мы выдаём деньги. Для их получения достаточно написать в ветку ниже с запросом и скрином выполнения контракта.",
            ]
        ),
        color=COLOR,
    )

    listing = discord.Embed(
        description="\n".join(
            [
                f"# {EMOJI_CALL_TEXT} Список семейных контрактов. {EMOJI_CALL_TEXT}",
                "- Гровер II",
                "- Курьер Green I",
                "- Подставная стройка",
                "- Нелегальный поставщик II",
                "- Ценная партия I",
                "- Ценный урок",
                "- Наводка I",
            ]
        ),
        color=COLOR,
    )

    details1 = discord.Embed(
        description="\n".join(
            [
                f"# {EMOJI_ACCEPT_TEXT} Информация о семейных контрактах. {EMOJI_ACCEPT_TEXT}",
                "",
                f"## {EMOJI_REVIEW_TEXT} **Гровер II:**",
                "*Данный контракт представляет собой задание на выращивание и последующую поставку продукции заказчику. Контракт активируется за фиксированную сумму и требует выполнения конкретного объёма поставки.*",
                "",
                "- **Активация:**",
                "• Контракт становится доступным при достижении 6 уровня персонажа.",
                "• Активация контракта осуществляется за 10 000$.",
                "",
                "- **Суть задания. Необходимо:**",
                "• Вырастить продукцию типа Green.",
                "• Обеспечить поставку 110 кустов Green.",
                "• Доставить указанное количество заказчику (Джамалу).",
                "",
                "- **Вознаграждение за выполнение:**",
                "• Оплата: 158.500$ (в фонд семьи)",
                "• Оплата игроку (вам): 50.000$",
                "• Репутация: 200",
                "• Семейный опыт: 150",
                "",
                f"## {EMOJI_REVIEW_TEXT} **Подставная стройка:**",
                "*Данный контракт представляет собой задание на разгрузку и поставку поддержанных кабелей на строительный объект в районе военной базы Форт-Занкудо. Контракт активируется за фиксированную сумму и требует выполнения установленного объёма поставки.*",
                "",
                "- **Активация:**",
                "• Контракт становится доступным при достижении 7 уровня персонажа.",
                "• Активация контракта осуществляется за 10 000$.",
                "",
                "- **Суть задания. Необходимо:**",
                "• Разгрузить поддержанные кабели.",
                "• Доставить 130 ящиков на стройку около военной базы Форт-Занкудо.",
                "• Выполнить поставку в полном объёме (130/130).",
                "",
                "- **Вознаграждение за выполнение:**",
                "• Оплата: 141.500$ (в фонд семьи)",
                "• Оплата игроку (каждому): 50.000$",
                "• Репутация: 210",
                "• Семейный опыт: 160",
                "",
                f"## {EMOJI_REVIEW_TEXT} **Нелегальный поставщик II:**",
                "*Данный контракт представляет собой задание на угон и доставку транспортного средства по заказу Рагнара. Контракт активируется за фиксированную сумму и требует выполнения конкретной цели.*",
                "",
                "- **Активация:**",
                "• Контракт становится доступным при достижении 8 уровня персонажа.",
                "• Требуется 2 ранг любой работы на 7 уровне персонажа.",
                "• Активация контракта осуществляется за 200$.",
                "",
                "- **Суть задания. Необходимо:**",
                "• Угнать транспорт по заказу Рагнара.",
                "• Доставить транспорт в указанную точку.",
                "• Выполнить заказ в полном объёме (1/1).",
                "",
                "- **Вознаграждение за выполнение:**",
                "• Оплата игроку (Вам): Зависит от уровня.",
                "• Репутация: 210",
                "• Семейный опыт: 160",
            ]
        ),
        color=COLOR,
    )

    details2 = discord.Embed(
        description="\n".join(
            [
                f"## {EMOJI_REVIEW_TEXT} **Ценная партия I:**",
                "*Данный контракт представляет собой задание на кражу и доставку наличных средств для подельника Оскара. Контракт активируется за фиксированную сумму и требует выполнения установленного объёма.*",
                "",
                "- **Активация:**",
                "• Контракт становится доступным при достижении 6 уровня персонажа.",
                "• Активация контракта осуществляется за 3 000$.",
                "",
                "- **Суть задания. Необходимо:**",
                "• Украсть малую партию пачек наличных.",
                "• Доставить 19 500$ для подельника Оскара.",
                "• Выполнить задание в полном объёме (19 500 / 19 500).",
                "",
                "- **Вознаграждение за выполнение:**",
                "• Оплата: 119 000$ (в фонд семьи)",
                "• Оплата игроку (Вам): 15.000$",
                "• Репутация: 210",
                "• Семейный опыт: 180",
                "",
                f"## {EMOJI_REVIEW_TEXT} **Ценный урок:**",
                "*Данный контракт представляет собой задание на изготовление и обналичивание поддельной подарочной карты по схеме Волкера. Контракт активируется за фиксированную сумму и требует выполнения установленной цели.*",
                "",
                "- **Активация:**",
                "• Контракт становится доступным при достижении 7 уровня персонажа.",
                "• Активация контракта осуществляется за 5 000$.",
                "",
                "- **Суть задания. Необходимо:**",
                "• Создать в помещении «Поддельная печать» поддельную подарочную карту.",
                "• Обналичить её в магазине одежды по схеме Волкера.",
                "• Выполнить задание в полном объёме (0/1 → 1/1).",
                "",
                "- **Вознаграждение за выполнение:**",
                "• Оплата: 80 000$ – 100 000$ (в фонд семьи)",
                "• Оплата игроку (Вам): 15.000$",
                "• Репутация: 80",
                "• Семейный опыт: 50",
            ]
        ),
        color=COLOR,
    )

    return [intro, listing, details1, details2]


def build_fleet_embeds() -> list[discord.Embed]:
    embeds: list[discord.Embed] = []
    for car in FAMQ_FLEET:
        embed = discord.Embed(
            title=f"{EMOJI_CALL_TEXT} {car['name']} — {car['real_name']} {EMOJI_CALL_TEXT}",
            color=COLOR,
        )
        embed.add_field(name="🏋️ Вместимость", value=f"**{car['capacity']}**", inline=True)
        embed.add_field(name="⚡ Скорость", value=f"**{car['speed']}**", inline=True)
        embed.add_field(name="⛽ Топливо", value=f"**{car['fuel']}**", inline=True)
        embed.add_field(name="🔑 Доступ", value=f"**{car['rank']}**", inline=True)
        embed.set_image(url=car["image"])
        embeds.append(embed)
    return embeds


def build_info_embed_for_guild(guild_id: int) -> discord.Embed:
    project = get_project(guild_id)
    if project and project.get("panel_mode") == "single_server":
        description = "\n".join(
            [
                f"# {EMOJI_ACCEPT_TEXT} Добро пожаловать в семью **ASIXEZ**",
                "*Ты попал не просто в Discord — ты у ворот одной из самых сильных Crime-семей на Russia Online. Здесь нет случайных людей. Уважай место, куда вошёл.*",
                "",
                f"> **{EMOJI_DETROIT_TEXT} Основные правила:**",
                "> - Уважение — прежде всего.",
                "> - Оскорбления, токсичность и провокации наказуемо; **BAN / PERMBAN**",
                "",
                f"> {EMOJI_REVIEW_TEXT} **Конфиденциальность.**",
                "> - Всё, что происходит в семье — остаётся в семье. Разглашение информации любого вида наказуемо; **BAN / PERMBAN**",
                "",
                f"> **{EMOJI_REJECT_TEXT} РП поведение — всегда.**",
                "> - Даже вне игры, ты остаёшься адекватным. Никакого флуда без причины, наказуемо; **WARN / MUTE / BAN**",
                "",
                f"> **{EMOJI_CALL_TEXT} Активность и лояльность.**",
                "> - За неактив без предупреждения — вылет. За предательство — BAN",
                "",
                f"> **{EMOJI_DETROIT_TEXT} Приказы старших — не обсуждаются.**",
                "> - Иерархия соблюдается. Вопросы — через личку или офицеров.",
                "",
                f"> {EMOJI_ACCEPT_TEXT} **Заявки / Вступление:**",
                f"> - Чтобы вступить в семью на Russia Online нужно подать заявку тут — <#{project['panel_channel_id']}>",
                "> **Старшие рассмотрят вашу заявку так скоро как получится. После принятия заявки поставьте ник по форме —**",
                "> - ASIXEZ | Имя (IRL) | Имя Фамилия (В игре)",
                "",
                "**Добро пожаловать домой.**",
                "**Семья — навсегда.**",
                "***ASIXEZ.***",
            ]
        )
        return discord.Embed(description=description, color=COLOR)
    return build_info_embed()


def build_promo_embed_for_guild(guild_id: int) -> discord.Embed:
    project = get_project(guild_id)
    if project and project.get("panel_mode") == "single_server":
        description_lines = [
            f"{EMOJI_REVIEW_TEXT} **Хочешь играть на Russia Online?**",
            "",
            f"{EMOJI_ACCEPT_TEXT} Введите в чат промокод: **`/promo {project.get('promo_code', 'FED')}`**",
            f"{EMOJI_REVIEW_TEXT} Или зарегистрируйтесь по ссылке:",
            project.get("promo_register_url") or "Пока не указано",
            "",
            "*Поддержи семью — используй промокод при регистрации!*",
        ]
        embed = discord.Embed(description="\n".join(description_lines), color=COLOR)
        if FAMQ_PROMO_IMAGE_URL:
            embed.set_image(url=FAMQ_PROMO_IMAGE_URL)
        return embed
    return build_promo_embed()


def build_contract_embeds_for_guild(guild_id: int) -> list[discord.Embed]:
    project = get_project(guild_id)
    if project and project.get("contracts_mode") == "empty":
        return [discord.Embed(description="Контракты скоро будут добавлены.", color=COLOR)]
    return build_contract_embeds()


def build_fleet_embeds_for_guild(guild_id: int) -> list[discord.Embed]:
    project = get_project(guild_id)
    if project and project.get("fleet_mode") == "empty":
        return [discord.Embed(description="Автопарк скоро будет добавлен.", color=COLOR)]
    return build_fleet_embeds()


def build_giveaway_embed(giveaway: dict[str, Any], creator_mention: str) -> discord.Embed:
    participants = len(giveaway.get("participants", []))
    ends_at = parse_iso(giveaway.get("endsAt"))
    embed = make_embed(
        title=f"{EMOJI_ACCEPT_TEXT} Розыгрыш {giveaway.get('prize', 'Приз')}",
        description="\n".join(
            [
                f"**Организатор:** {creator_mention}",
                f"**Приз:** {giveaway.get('prize', 'Не указан')}",
                "",
                f"{EMOJI_REVIEW_TEXT} **Условия участия:**",
                giveaway.get("conditions", "Не указаны"),
                "",
                f"{EMOJI_CALL_TEXT} **Участников:** {participants}",
                f"{EMOJI_DETROIT_TEXT} **Завершение:** <t:{int(ends_at.timestamp())}:R>",
            ]
        ),
        color=COLOR_SOFT,
        timestamp=ends_at,
    )
    embed.set_footer(text=f"Giveaway #{giveaway['id']}")
    if GIVEAWAY_IMAGE_URL:
        embed.set_image(url=GIVEAWAY_IMAGE_URL)
    return embed


def build_giveaway_closed_embed(giveaway: dict[str, Any], creator_mention: str, winner_mention: str | None) -> discord.Embed:
    embed = build_giveaway_embed(giveaway, creator_mention)
    embed.color = COLOR_SOFT if winner_mention else COLOR_MUTED
    if winner_mention:
        embed.description += f"\n\n{EMOJI_ACCEPT_TEXT} **Победитель:** {winner_mention}"
    else:
        embed.description += f"\n\n{EMOJI_REJECT_TEXT} Розыгрыш завершён без участников."
    return embed


async def send_dm_or_fallback(guild: discord.Guild, user_id: int, embed: discord.Embed) -> None:
    member = guild.get_member(user_id)
    user: discord.abc.User = member if member is not None else await bot.fetch_user(user_id)

    try:
        await user.send(embed=embed)
        return
    except Exception:
        pass

    project = get_project(guild)
    fallback_channel_id = project.get("dm_fallback_channel_id") if project else None
    if not fallback_channel_id:
        return
    try:
        fallback = guild.get_channel(int(fallback_channel_id)) or await guild.fetch_channel(int(fallback_channel_id))
    except Exception:
        return

    if text_sendable(fallback):
        await fallback.send(
            content=f"<@{user_id}>",
            embed=embed,
            allowed_mentions=discord.AllowedMentions(users=True),
        )


async def log_action(guild: discord.Guild, description: str) -> None:
    project = get_project(guild)
    if project is None:
        return
    try:
        log_channel = guild.get_channel(int(project["application_log_channel_id"])) or await guild.fetch_channel(int(project["application_log_channel_id"]))
    except Exception:
        return

    if text_sendable(log_channel):
        await log_channel.send(embed=build_log_embed_for_guild(guild.id, description))


async def send_security_log(
    guild: discord.Guild,
    *,
    title: str,
    color: int,
    user_id: int | None,
    action_label: str,
    count_label: str,
    result_label: str,
    extra_lines: list[str] | None = None,
    source_message_id: int | None = None,
    ping_alert_role: bool = False,
    view: discord.ui.View | None = None,
) -> None:
    channel = await resolve_security_log_channel(guild)
    if channel is None:
        return

    project = get_project(guild)
    alert_role_id = int(project["alert_role_id"]) if project and project.get("alert_role_id") else ALERT_ROLE_ID
    content = f"<@&{alert_role_id}>" if ping_alert_role else None
    log_view = view if view is not None else (SecurityActionView(user_id) if user_id and not is_protected_target(guild, user_id) else None)
    try:
        await channel.send(
            content=content,
            embed=build_security_embed(
                title=title,
                color=color,
                user_id=user_id,
                action_label=action_label,
                count_label=count_label,
                result_label=result_label,
                extra_lines=extra_lines,
                source_message_id=source_message_id,
            ),
            view=log_view,
            allowed_mentions=discord.AllowedMentions(roles=True),
        )
    except Exception:
        pass


def is_famq_activity_guild(guild_id: int) -> bool:
    return guild_id == FAMQ_GUILD_ID


def format_log_time_msk(value: datetime | None = None) -> str:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    localized = current.astimezone(MSK_TZ)
    today = datetime.now(MSK_TZ).date()
    target_date = localized.date()
    if target_date == today:
        prefix = "Сегодня"
    elif target_date == today - timedelta(days=1):
        prefix = "Вчера"
    else:
        prefix = localized.strftime("%d.%m.%Y")
    return f"{prefix}, в {localized.strftime('%H:%M')} MSK"


def safe_asset_url(asset: Any) -> str:
    if asset is None:
        return ""
    return str(getattr(asset, "url", "") or "")


def get_member_timeout_until(member: discord.Member) -> datetime | None:
    return (
        getattr(member, "communication_disabled_until", None)
        or getattr(member, "timed_out_until", None)
        or getattr(member, "timeout_until", None)
    )


def format_member_label(member: discord.abc.User | discord.Member | None) -> str:
    if member is None:
        return "неизвестно"
    if isinstance(member, discord.Member):
        return member.mention
    return f"<@{member.id}>"


def format_role_label(role: discord.Role | None) -> str:
    if role is None:
        return "неизвестно"
    return role.mention


def format_roles_label(roles: list[discord.Role]) -> str:
    if not roles:
        return "—"
    return trim_embed_text(" ".join(role.mention for role in roles))


def format_channel_label(channel: Any) -> str:
    if channel is None:
        return "# неизвестно"
    mention = getattr(channel, "mention", None)
    if mention:
        return mention
    name = getattr(channel, "name", "неизвестно")
    return f"# {name}"


def format_thread_parent_label(thread: discord.Thread | None) -> str:
    parent = thread.parent if thread is not None else None
    if parent is None:
        return "неизвестно"
    return format_channel_label(parent)


def format_channel_type_label(channel: Any) -> str:
    if channel is None:
        return "unknown"
    if isinstance(channel, discord.Thread):
        return "thread"
    channel_type = getattr(channel, "type", None)
    if channel_type is None:
        return "unknown"
    return str(channel_type).replace("_", " ")


def format_text_block(value: str, *, fallback: str = "Нет", limit: int = 1000) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        return fallback
    return trim_embed_text(cleaned, limit=limit)


def build_before_after_value(before_value: str, after_value: str) -> str:
    before_clean = format_text_block(before_value)
    after_clean = format_text_block(after_value)
    return f"**До:** {before_clean}\n**После:** {after_clean}"


def decorate_field_name(name: str) -> str:
    return name


async def resolve_activity_log_channel(guild: discord.Guild) -> discord.TextChannel | None:
    if not is_famq_activity_guild(guild.id):
        return None
    project = get_project(guild)
    if project is None or not project.get("activity_log_channel_id"):
        return None
    try:
        channel = guild.get_channel(int(project["activity_log_channel_id"])) or await guild.fetch_channel(int(project["activity_log_channel_id"]))
    except Exception:
        return None
    return channel if isinstance(channel, discord.TextChannel) else None


async def fetch_optional_audit_executor(
    guild: discord.Guild,
    action_name: str,
    target_id: int | None = None,
) -> tuple[discord.Member | None, discord.AuditLogEntry | None]:
    action = getattr(discord.AuditLogAction, action_name, None)
    if action is None:
        return None, None
    return await fetch_audit_executor(guild, action, target_id=target_id)


def build_activity_embed(
    *,
    title: str,
    description: str,
    fields: list[tuple[str, str, bool]],
    color: int = COLOR,
    author_name: str | None = None,
    author_icon_url: str | None = None,
    footer_parts: list[str] | None = None,
    thumbnail_url: str | None = None,
    image_url: str | None = None,
) -> discord.Embed:
    embed = make_embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    if author_name:
        if author_icon_url:
            embed.set_author(name=author_name, icon_url=author_icon_url)
        else:
            embed.set_author(name=author_name)
    else:
        embed.title = title
    for name, value, inline in fields:
        if not value:
            continue
        embed.add_field(name=decorate_field_name(name), value=trim_embed_text(value), inline=inline)
    if footer_parts:
        embed.set_footer(text=" • ".join(part for part in footer_parts if part))
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    if image_url:
        embed.set_image(url=image_url)
    return embed


async def send_activity_log(
    guild: discord.Guild,
    *,
    title: str,
    description: str,
    fields: list[tuple[str, str, bool]],
    color: int = COLOR,
    author_name: str | None = None,
    author_icon_url: str | None = None,
    footer_parts: list[str] | None = None,
    thumbnail_url: str | None = None,
    image_url: str | None = None,
) -> None:
    channel = await resolve_activity_log_channel(guild)
    if channel is None:
        return
    try:
        await channel.send(
            embed=build_activity_embed(
                title=title,
                description=description,
                fields=fields,
                color=color,
                author_name=author_name,
                author_icon_url=author_icon_url,
                footer_parts=footer_parts,
                thumbnail_url=thumbnail_url,
                image_url=image_url,
            )
        )
    except Exception:
        pass


def get_channel_update_changes(before: discord.abc.GuildChannel, after: discord.abc.GuildChannel) -> list[str]:
    changes: list[str] = []
    if before.name != after.name:
        changes.append(f"Имя: `{before.name}` → `{after.name}`")
    if getattr(before, "category_id", None) != getattr(after, "category_id", None):
        changes.append(
            f"Категория: `{getattr(before.category, 'name', 'нет')}` → `{getattr(after.category, 'name', 'нет')}`"
        )
    for attr_name, label in (
        ("topic", "Тема"),
        ("slowmode_delay", "Слоумод"),
        ("nsfw", "NSFW"),
        ("bitrate", "Битрейт"),
        ("user_limit", "Лимит пользователей"),
        ("position", "Позиция"),
    ):
        if getattr(before, attr_name, None) != getattr(after, attr_name, None):
            changes.append(f"{label}: `{getattr(before, attr_name, None)}` → `{getattr(after, attr_name, None)}`")
    return changes


def get_role_update_changes(before: discord.Role, after: discord.Role) -> list[str]:
    changes: list[str] = []
    if before.name != after.name:
        changes.append(f"Имя: `{before.name}` → `{after.name}`")
    if before.colour != after.colour:
        changes.append(f"Цвет: `{before.colour}` → `{after.colour}`")
    if before.hoist != after.hoist:
        changes.append(f"Отдельно: `{before.hoist}` → `{after.hoist}`")
    if before.mentionable != after.mentionable:
        changes.append(f"Упоминание: `{before.mentionable}` → `{after.mentionable}`")
    if before.permissions.value != after.permissions.value:
        changes.append("Права роли были изменены.")
    return changes


def get_guild_update_changes(before: discord.Guild, after: discord.Guild) -> list[str]:
    changes: list[str] = []
    for attr_name, label in (
        ("name", "Название"),
        ("description", "Описание"),
        ("vanity_url_code", "Vanity"),
        ("preferred_locale", "Язык"),
        ("verification_level", "Верификация"),
        ("explicit_content_filter", "Фильтр контента"),
        ("default_notifications", "Уведомления"),
    ):
        if getattr(before, attr_name, None) != getattr(after, attr_name, None):
            changes.append(f"{label}: `{getattr(before, attr_name, None) or '—'}` → `{getattr(after, attr_name, None) or '—'}`")
    if safe_asset_url(before.icon) != safe_asset_url(after.icon):
        changes.append("Иконка сервера была изменена.")
    if safe_asset_url(before.banner) != safe_asset_url(after.banner):
        changes.append("Баннер сервера был изменён.")
    if safe_asset_url(before.splash) != safe_asset_url(after.splash):
        changes.append("Splash-изображение было изменено.")
    if safe_asset_url(before.discovery_splash) != safe_asset_url(after.discovery_splash):
        changes.append("Discovery splash был изменён.")
    return changes


def register_admin_action(guild_id: int, user_id: int, action_name: str, now: float | None = None) -> int:
    current = now if now is not None else time.time()
    prune_security_caches(current)
    action_map = admin_action_cache.setdefault((guild_id, user_id), {})
    action_queue = action_map.setdefault(action_name, deque())
    action_queue.append(current)
    prune_deque(action_queue, 10, current)
    return len(action_queue)


def register_user_message(guild_id: int, user_id: int, now: float | None = None) -> int:
    current = now if now is not None else time.time()
    prune_security_caches(current)
    message_queue = user_message_cache.setdefault((guild_id, user_id), deque())
    message_queue.append(current)
    prune_deque(message_queue, 10, current)
    return sum(1 for timestamp in message_queue if current - timestamp <= 5)


def role_has_moderation_power(role: discord.Role) -> bool:
    permissions = role.permissions
    return any(
        [
            permissions.administrator,
            permissions.kick_members,
            permissions.ban_members,
            permissions.manage_roles,
            getattr(permissions, "moderate_members", False),
            getattr(permissions, "mute_members", False),
        ]
    )


def get_removable_moderation_roles(member: discord.Member) -> list[discord.Role]:
    guild_me = member.guild.me
    if guild_me is None:
        return []

    removable_roles: list[discord.Role] = []
    for role in member.roles:
        if role == member.guild.default_role or role.managed:
            continue
        if not role_has_moderation_power(role):
            continue
        if role >= guild_me.top_role:
            continue
        removable_roles.append(role)
    return removable_roles


async def restrict_kick_actor(member: discord.Member) -> list[int]:
    if is_protected_target(member.guild, member.id):
        return []
    cache_key = (member.guild.id, member.id)
    if cache_key in kick_restriction_cache:
        return list(kick_restriction_cache[cache_key].get("roleIds", []))

    roles_to_remove = get_removable_moderation_roles(member)
    if not roles_to_remove:
        return []

    try:
        await member.remove_roles(*roles_to_remove, reason="Anti-nuke mass kick restriction")
    except Exception:
        return []

    role_ids = [role.id for role in roles_to_remove]
    kick_restriction_cache[cache_key] = {
        "roleIds": role_ids,
        "createdAt": time.time(),
    }
    return role_ids


async def restore_kick_restriction(guild: discord.Guild, user_id: int, reason: str) -> bool:
    record = kick_restriction_cache.pop((guild.id, user_id), None)
    if not record:
        return False

    member = guild.get_member(user_id)
    if member is None:
        try:
            member = await guild.fetch_member(user_id)
        except Exception:
            member = None
    if member is None or is_protected_target(guild, user_id):
        return False

    roles = [role for role_id in record.get("roleIds", []) if (role := guild.get_role(int(role_id))) is not None]
    if not roles:
        return False

    try:
        await member.add_roles(*roles, reason=reason)
        return True
    except Exception:
        return False


async def maybe_restrict_kick_actor(guild: discord.Guild, kicked_user_id: int) -> None:
    actor, _entry = await fetch_audit_executor(guild, discord.AuditLogAction.kick, target_id=kicked_user_id)
    if actor is None or is_protected_target(guild, actor.id):
        return

    count = register_admin_action(guild.id, actor.id, "kick")
    limit = ANTI_NUKE_LIMITS["kick"]
    if count < limit or (guild.id, actor.id) in kick_restriction_cache:
        return

    removed_role_ids = await restrict_kick_actor(actor)
    removed_roles_text = ", ".join(f"<@&{role_id}>" for role_id in removed_role_ids) if removed_role_ids else "Роли не удалось снять"
    await send_security_log(
        guild,
        title="🛡️ Mass Kick Review Required",
        color=0xE74C3C,
        user_id=actor.id,
        action_label="Mass Kick",
        count_label=f"{count} / 10 sec (limit: {limit})",
        result_label="Kick/Ban/Mute roles temporarily removed until review" if removed_role_ids else "Limit reached, but roles could not be removed",
        extra_lines=[
            "Была ли это запланированная акция?",
            "Нажмите **Да**, чтобы вернуть функционал.",
            "Нажмите **Нет**, чтобы не возвращать функционал.",
            f"Removed roles: {removed_roles_text}",
            f"Last kicked user ID: `{kicked_user_id}`",
        ],
        ping_alert_role=True,
        view=KickRestrictionReviewView(actor.id),
    )


async def maybe_timeout_admin_actor(
    guild: discord.Guild,
    action_name: str,
    action_label: str,
    target_id: int | None = None,
) -> None:
    action_map = {
        "channel_delete": discord.AuditLogAction.channel_delete,
        "role_delete": discord.AuditLogAction.role_delete,
        "ban": discord.AuditLogAction.ban,
    }
    audit_action = action_map.get(action_name)
    if audit_action is None:
        return

    actor, _entry = await fetch_audit_executor(guild, audit_action, target_id=target_id)
    if actor is None or is_protected_target(guild, actor.id):
        return

    count = register_admin_action(guild.id, actor.id, action_name)
    limit = ANTI_NUKE_LIMITS[action_name]
    if count < limit:
        return

    applied = await apply_timeout_to_member(actor, 10 * 60, f"Anti-nuke trigger: {action_name}")
    removed_role_ids: list[int] = []
    if not applied:
        removed_role_ids = await restrict_kick_actor(actor)
    removed_roles_text = ", ".join(f"<@&{role_id}>" for role_id in removed_role_ids) if removed_role_ids else ""
    await send_security_log(
        guild,
        title="🧨 Anti-Nuke Triggered",
        color=0xE74C3C,
        user_id=actor.id,
        action_label=action_label,
        count_label=f"{count} / 10 sec (limit: {limit})",
        result_label=(
            "Timeout applied for 10 minutes"
            if applied
            else (
                "Timeout failed, moderation roles removed"
                if removed_role_ids
                else "Limit reached, but timeout/role removal could not be applied"
            )
        ),
        extra_lines=[
            line
            for line in (
                f"Target ID: `{target_id}`" if target_id else "",
                f"Removed roles: {removed_roles_text}" if removed_roles_text else "",
            )
            if line
        ],
        ping_alert_role=True,
    )


async def post_result(
    guild: discord.Guild,
    app: dict[str, Any],
    recruiter_user_id: int,
    verdict: str,
    reject_reason: str | None = None,
) -> None:
    project = get_project(guild)
    if project is None:
        return
    try:
        channel = guild.get_channel(int(project["results_channel_id"])) or await guild.fetch_channel(int(project["results_channel_id"]))
    except Exception:
        return

    if not text_sendable(channel):
        return

    await channel.send(
        content=f"<@{app['applicantId']}>",
        embed=build_result_embed(app, recruiter_user_id, verdict, reject_reason),
        allowed_mentions=discord.AllowedMentions(users=True),
    )


async def delete_channel_now(channel_id: int, reason: str) -> bool:
    channel = bot.get_channel(channel_id)
    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except Exception:
            channel = None

    if channel is None:
        return True

    if isinstance(channel, discord.Thread) and channel.archived:
        try:
            await channel.edit(archived=False, reason=reason)
        except Exception:
            pass

    delete_method = getattr(channel, "delete", None)
    if not callable(delete_method):
        return True

    try:
        await delete_method(reason=reason)
        return True
    except Exception as error:
        console_log(f"Failed to delete channel {channel_id}: {error}")
        return False


async def delete_channel_later(channel_id: int, reason: str) -> None:
    await asyncio.sleep(4)
    for _attempt in range(8):
        if await delete_channel_now(channel_id, reason):
            return
        await asyncio.sleep(3)


async def cleanup_resolved_application_channels(guild: discord.Guild) -> int:
    reload_applications()
    deleted = 0
    for app in application_store.get("items", {}).values():
        if int(app.get("guildId", 0)) != guild.id:
            continue
        if app.get("status") not in {"accepted", "rejected"}:
            continue
        channel_id = int(app.get("channelId") or 0)
        if channel_id <= 0:
            continue
        if await delete_channel_now(channel_id, f"Cleanup resolved application #{app.get('id')}"):
            deleted += 1
    return deleted


async def collect_restart_issues(guild: discord.Guild, setup_issues: list[str] | None = None) -> list[str]:
    project = get_project(guild)
    issues = list(setup_issues or [])
    if project is None:
        return issues

    me = guild.me or guild.get_member(bot.user.id) if bot.user else None
    permissions = me.guild_permissions if me is not None else None
    required_permissions = {
        "view_audit_log": "нет доступа к журналу аудита, анти-рейд не сможет видеть нарушителя",
        "manage_roles": "нет права управлять ролями, анти-рейд не сможет снять опасные роли",
        "moderate_members": "нет права выдавать timeout, анти-спам/анти-рейд не сможет мутить",
        "manage_channels": "нет права управлять каналами, заявки и голосовые комнаты могут тормозить или падать",
    }
    if permissions is None:
        issues.append("не удалось получить права бота на сервере")
    else:
        for permission_name, message in required_permissions.items():
            if not getattr(permissions, permission_name, False):
                issues.append(message)

    channel_checks = [
        ("канал отчётности перезапуска", project.get("restart_status_channel_id")),
        ("канал логов безопасности", project.get("security_log_channel_id")),
        ("канал логов заявок", project.get("application_log_channel_id")),
        ("канал панели заявок", project.get("panel_channel_id")),
    ]
    for label, channel_id in channel_checks:
        if not channel_id:
            issues.append(f"{label}: ID не настроен")
            continue
        try:
            channel = guild.get_channel(int(channel_id)) or await guild.fetch_channel(int(channel_id))
        except Exception:
            issues.append(f"{label}: не найден или нет доступа")
            continue
        if not text_sendable(channel):
            issues.append(f"{label}: канал не текстовый")

    category_id = project.get("application_category_id")
    if category_id:
        category = guild.get_channel(int(category_id))
        if category is None:
            issues.append("категория заявок не найдена в кеше сервера")

    return issues


async def send_restart_status(guild: discord.Guild, setup_issues: list[str] | None = None) -> None:
    project = get_project(guild)
    if project is None:
        return
    try:
        channel = guild.get_channel(int(project["restart_status_channel_id"])) or await guild.fetch_channel(int(project["restart_status_channel_id"]))
    except Exception:
        return

    if not text_sendable(channel):
        return

    issues = await collect_restart_issues(guild, setup_issues)
    embed = make_embed(
        title=f"{EMOJI_ACCEPT_TEXT} {project['project_name']} Bot Restart",
        description=(
            "✅ Бот перезапущен и работает стабильно."
            if not issues
            else f"⚠️ Бот перезапущен, но найдено проблем: **{len(issues)}**. Отчёт ниже в ветке."
        ),
        color=COLOR_SOFT if not issues else COLOR_MUTED,
        timestamp=datetime.now(timezone.utc),
    )
    message = await channel.send(embed=embed)
    if not issues or not isinstance(channel, discord.TextChannel):
        return

    report_embed = make_embed(
        title="🧾 Отчёт после перезапуска",
        description="\n".join(f"• {issue}" for issue in issues[:20]),
        color=COLOR_MUTED,
        timestamp=datetime.now(timezone.utc),
    )
    report_embed.set_footer(text="Проверьте эти пункты, чтобы анти-рейд и заявки работали без задержек.")
    try:
        thread = await channel.create_thread(
            name=f"restart-report-{datetime.now(MSK_TZ).strftime('%d-%m-%H-%M')}",
            message=message,
            auto_archive_duration=1440,
        )
        await thread.send(embed=report_embed)
    except Exception:
        try:
            await channel.send(embed=report_embed)
        except Exception:
            pass


async def send_famq_welcome_message(member: discord.Member) -> None:
    if member.guild.id != FAMQ_GUILD_ID:
        return
    try:
        channel = member.guild.get_channel(FAMQ_WELCOME_CHANNEL_ID) or await member.guild.fetch_channel(FAMQ_WELCOME_CHANNEL_ID)
    except Exception:
        return

    if not text_sendable(channel):
        return

    member_count = member.guild.member_count or len(member.guild.members)
    embed = make_embed(
        title=f"{EMOJI_ACCEPT_TEXT} Добро пожаловать в ASIXEZ",
        description=(
            f"👋 {member.mention} зашёл на сервер.\n\n"
            f"👥 Теперь нас: **{member_count}**\n"
            "📋 Заявки и верификация: <#1466147735873786200>\n"
            "🎁 Промокод: **`/promo FED`**"
        ),
        color=COLOR,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    await channel.send(
        embed=embed,
        view=CopyDiscordIdView(member.id),
        allowed_mentions=discord.AllowedMentions(users=True),
    )


async def send_famq_leave_message(member: discord.Member) -> None:
    if member.guild.id != FAMQ_GUILD_ID:
        return
    try:
        channel = member.guild.get_channel(FAMQ_WELCOME_CHANNEL_ID) or await member.guild.fetch_channel(FAMQ_WELCOME_CHANNEL_ID)
    except Exception:
        return

    if not text_sendable(channel):
        return

    member_count = member.guild.member_count or len(member.guild.members)
    embed = make_embed(
        title="🚪 Участник покинул сервер",
        description=(
            f"👤 {member.mention} вышел с сервера.\n\n"
            f"👥 Теперь нас: **{member_count}**\n"
            "🕯️ Канал держит историю движения состава."
        ),
        color=COLOR_MUTED,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    await channel.send(
        embed=embed,
        allowed_mentions=discord.AllowedMentions(users=True),
    )


def get_next_restart_datetime(now: datetime | None = None) -> datetime:
    current = now if now is not None else datetime.now(MSK_TZ)
    if current.tzinfo is None:
        current = current.replace(tzinfo=MSK_TZ)
    else:
        current = current.astimezone(MSK_TZ)

    for hour in RESTART_HOURS_MSK:
        candidate = current.replace(hour=hour, minute=0, second=0, microsecond=0)
        if candidate > current:
            return candidate

    next_day = current + timedelta(days=1)
    return next_day.replace(hour=RESTART_HOURS_MSK[0], minute=0, second=0, microsecond=0)


async def restart_process_later() -> None:
    while True:
        try:
            now = datetime.now(MSK_TZ)
            next_restart = get_next_restart_datetime(now)
            delay_seconds = max((next_restart - now).total_seconds(), 1)
            console_log(f"Next bot restart scheduled at {next_restart.isoformat()}")
            await asyncio.sleep(delay_seconds)
            storage.flush()
            sys.stdout.flush()
            sys.stderr.flush()
            os.execv(sys.executable, [sys.executable, *sys.argv])
        except asyncio.CancelledError:
            raise
        except Exception as error:
            console_log(f"Restart task failed: {error}")
            await asyncio.sleep(60)


def ensure_restart_task() -> None:
    global restart_task
    if restart_task is not None and not restart_task.done():
        return
    if restart_task is not None:
        try:
            exception = restart_task.exception()
        except Exception:
            exception = None
        if exception is not None:
            console_log(f"Restart task stopped with error: {exception}")
    restart_task = asyncio.create_task(restart_process_later())


def build_voice_owner_overwrite() -> discord.PermissionOverwrite:
    return discord.PermissionOverwrite(
        view_channel=True,
        connect=True,
        speak=True,
        stream=True,
        use_voice_activation=True,
        priority_speaker=True,
        move_members=True,
        mute_members=True,
        deafen_members=True,
        manage_channels=True,
    )


async def resolve_owned_voice_channel(
    interaction: discord.Interaction,
) -> tuple[discord.VoiceChannel, dict[str, Any]] | tuple[None, None]:
    if interaction.guild is None:
        return None, None

    reload_voice_rooms()
    owned_room = get_owned_voice_room(interaction.user.id, interaction.guild.id)
    if owned_room is None:
        await interaction.response.send_message(
            "У вас нет активной голосовой комнаты. Зайдите в канал создания комнаты и попробуйте снова.",
            ephemeral=True,
        )
        return None, None

    channel_id, room = owned_room
    channel = interaction.guild.get_channel(channel_id)
    if channel is None:
        try:
            channel = await interaction.guild.fetch_channel(channel_id)
        except Exception:
            channel = None

    if not isinstance(channel, discord.VoiceChannel):
        remove_voice_room(channel_id)
        await interaction.response.send_message(
            "Ваша голосовая комната не найдена. Зайдите в канал создания комнаты ещё раз.",
            ephemeral=True,
        )
        return None, None

    return channel, room


async def fetch_target_member(guild: discord.Guild, raw_value: str) -> discord.Member | None:
    user_id = extract_user_id(raw_value)
    if user_id is None:
        return None

    member = guild.get_member(user_id)
    if member is not None:
        return member

    try:
        return await guild.fetch_member(user_id)
    except Exception:
        return None


async def create_temporary_voice_room(member: discord.Member) -> discord.VoiceChannel | None:
    guild = member.guild
    project = get_project(guild)
    if project is None:
        return None
    existing_room = get_owned_voice_room(member.id, guild.id)
    if existing_room is not None:
        existing_channel = guild.get_channel(existing_room[0])
        if existing_channel is None:
            try:
                existing_channel = await guild.fetch_channel(existing_room[0])
            except Exception:
                existing_channel = None
        if isinstance(existing_channel, discord.VoiceChannel):
            return existing_channel
        remove_voice_room(existing_room[0])

    trigger_channel_id = int(project["voice_trigger_channel_id"])
    trigger_channel = guild.get_channel(trigger_channel_id)
    if trigger_channel is None:
        try:
            trigger_channel = await guild.fetch_channel(trigger_channel_id)
        except Exception:
            return None

    if not isinstance(trigger_channel, discord.VoiceChannel):
        return None

    room_name = f"Комната {member.display_name}"
    overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
        guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=True, speak=True),
        member: build_voice_owner_overwrite(),
    }

    try:
        channel = await guild.create_voice_channel(
            name=room_name,
            category=trigger_channel.category,
            overwrites=overwrites,
            user_limit=2,
            bitrate=min(trigger_channel.bitrate, guild.bitrate_limit),
            reason=f"Временная голосовая комната для {member}",
        )
    except Exception:
        return None

    set_voice_room(
        channel.id,
        {
            "channelId": channel.id,
            "guildId": guild.id,
            "ownerId": member.id,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "name": channel.name,
        },
    )
    return channel


async def cleanup_voice_room_if_empty(channel: discord.abc.GuildChannel | None) -> None:
    if not isinstance(channel, discord.VoiceChannel):
        return
    if not get_voice_room(channel.id):
        return
    if channel.members:
        return

    remove_voice_room(channel.id)
    try:
        await channel.delete(reason="Пустая временная голосовая комната")
    except Exception:
        pass


async def cleanup_stale_voice_rooms(guild: discord.Guild) -> None:
    reload_voice_rooms()
    stale_ids: list[int] = []

    for channel_id in list(get_voice_rooms().keys()):
        try:
            voice_channel = guild.get_channel(int(channel_id)) or await guild.fetch_channel(int(channel_id))
        except Exception:
            voice_channel = None

        if not isinstance(voice_channel, discord.VoiceChannel):
            stale_ids.append(int(channel_id))
            continue

        if not voice_channel.members:
            try:
                await voice_channel.delete(reason="Очистка пустой временной комнаты после рестарта")
            except Exception:
                pass
            stale_ids.append(int(channel_id))

    for channel_id in stale_ids:
        remove_voice_room(channel_id)

async def finish_giveaway(giveaway_id: int) -> None:
    try:
        reload_giveaways()
        giveaway = giveaway_store["items"].get(str(giveaway_id))
        if not giveaway or giveaway.get("status") != "active":
            return

        delay = (parse_iso(giveaway.get("endsAt")) - datetime.now(timezone.utc)).total_seconds()
        if delay > 0:
            await asyncio.sleep(delay)

        reload_giveaways()
        giveaway = giveaway_store["items"].get(str(giveaway_id))
        if not giveaway or giveaway.get("status") != "active":
            return

        try:
            guild = bot.get_guild(FAMQ_GUILD_ID) or await bot.fetch_guild(FAMQ_GUILD_ID)
            channel = guild.get_channel(int(giveaway["channelId"])) or await guild.fetch_channel(int(giveaway["channelId"]))
        except Exception:
            return

        if not isinstance(channel, discord.TextChannel):
            return

        participants = list(dict.fromkeys(int(user_id) for user_id in giveaway.get("participants", [])))
        creator_id = int(giveaway["creatorId"])
        winner_id = random.choice(participants) if participants else None

        giveaway["status"] = "finished"
        giveaway["finishedAt"] = datetime.now(timezone.utc).isoformat()
        giveaway["winnerId"] = winner_id or 0
        giveaway_store["items"][str(giveaway_id)] = giveaway
        save_giveaways()

        message = None
        try:
            message = await channel.fetch_message(int(giveaway["messageId"]))
        except Exception:
            message = None

        creator_mention = f"<@{creator_id}>"
        winner_mention = f"<@{winner_id}>" if winner_id else None
        closed_view = GiveawayJoinView(giveaway_id)
        for child in closed_view.children:
            child.disabled = True

        if message is not None:
            await message.edit(
                content="@everyone",
                embed=build_giveaway_closed_embed(giveaway, creator_mention, winner_mention),
                view=closed_view,
                allowed_mentions=discord.AllowedMentions(everyone=True),
            )

        if winner_id:
            await channel.send(
                content=f"{winner_mention} победил в розыгрыше от {creator_mention}.",
                allowed_mentions=discord.AllowedMentions(users=True),
            )
            try:
                winner_user = guild.get_member(winner_id) or await bot.fetch_user(winner_id)
                creator_user = guild.get_member(creator_id) or await bot.fetch_user(creator_id)
                await winner_user.send(
                    embed=make_embed(
                        title=f"{EMOJI_ACCEPT_TEXT} Вы победили в розыгрыше!",
                        description="\n".join(
                            [
                                f"Вы выиграли: **{giveaway.get('prize', 'Приз')}**",
                                f"Организатор: {creator_user.mention if hasattr(creator_user, 'mention') else creator_mention}",
                                "Отправьте организатору в личные сообщения доказательства выполнения условий.",
                                f"Discord организатора: `{getattr(creator_user, 'name', str(creator_id))}`",
                            ]
                        ),
                        color=COLOR_SOFT,
                        timestamp=datetime.now(timezone.utc),
                    )
                )
            except Exception:
                pass
        else:
            await channel.send("Розыгрыш завершён без участников.")
    finally:
        giveaway_tasks.pop(giveaway_id, None)


def ensure_giveaway_task(giveaway_id: int) -> None:
    existing = giveaway_tasks.get(giveaway_id)
    if existing and not existing.done():
        return
    giveaway_tasks[giveaway_id] = asyncio.create_task(finish_giveaway(giveaway_id))


class GiveawayConfirmView(discord.ui.View):
    def __init__(self, giveaway_id: int):
        super().__init__(timeout=180)
        self.giveaway_id = giveaway_id

    @discord.ui.button(label="Да", style=discord.ButtonStyle.secondary)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        reload_giveaways()
        giveaway = giveaway_store["items"].get(str(self.giveaway_id))
        if not giveaway or giveaway.get("status") != "active":
            await interaction.response.edit_message(content="Этот розыгрыш уже завершён.", view=None)
            return

        user_id = interaction.user.id
        participants = list(dict.fromkeys(int(user) for user in giveaway.get("participants", [])))
        if user_id not in participants:
            participants.append(user_id)
            giveaway["participants"] = participants
            giveaway_store["items"][str(self.giveaway_id)] = giveaway
            save_giveaways()

            try:
                guild = interaction.guild or bot.get_guild(FAMQ_GUILD_ID)
                if guild is not None:
                    channel = guild.get_channel(int(giveaway["channelId"])) or await guild.fetch_channel(int(giveaway["channelId"]))
                    if isinstance(channel, discord.TextChannel):
                        message = await channel.fetch_message(int(giveaway["messageId"]))
                        await message.edit(
                            content="@everyone",
                            embed=build_giveaway_embed(giveaway, f"<@{giveaway['creatorId']}>"),
                            view=GiveawayJoinView(self.giveaway_id),
                            allowed_mentions=discord.AllowedMentions(everyone=True),
                        )
                reload_giveaways()
            except Exception:
                pass

        await interaction.response.edit_message(content="Вы успешно приняли участие в розыгрыше.", view=None)

    @discord.ui.button(label="Нет", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.edit_message(content="Участие отменено.", view=None)


class GiveawayJoinView(discord.ui.View):
    def __init__(self, giveaway_id: int):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id
        reload_giveaways()
        giveaway = giveaway_store["items"].get(str(giveaway_id), {})
        participant_count = len(giveaway.get("participants", []))
        is_active = giveaway.get("status") == "active"

        join_button = discord.ui.Button(
            custom_id=f"giveaway_join_{giveaway_id}",
            label=f"Принять участие ({participant_count})",
            emoji=EMOJI_ACCEPT,
            style=discord.ButtonStyle.secondary,
            disabled=not is_active,
        )
        join_button.callback = self.join_callback
        self.add_item(join_button)

    async def join_callback(self, interaction: discord.Interaction) -> None:
        reload_giveaways()
        giveaway = giveaway_store["items"].get(str(self.giveaway_id))
        if not giveaway or giveaway.get("status") != "active":
            await interaction.response.send_message("Этот розыгрыш уже завершён.", ephemeral=True)
            return

        await interaction.response.send_message(
            "Нажимая кнопку вы подтверждаете выполнение условий, в случае если условия не выполнены при победе вы ничего не получите.",
            view=GiveawayConfirmView(self.giveaway_id),
            ephemeral=True,
        )


class GiveawayModal(discord.ui.Modal, title="Создание розыгрыша"):
    conditions = discord.ui.TextInput(
        label="Введите условия розыгрыша",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True,
        placeholder="Опишите подробно, что нужно сделать для участия.",
    )
    prize = discord.ui.TextInput(
        label="Введите сумму розыгрыша (с валютой)",
        max_length=120,
        required=True,
        placeholder="Например: 5.000.000$",
    )
    duration_hours = discord.ui.TextInput(
        label="Введите время розыгрыша в часах",
        max_length=6,
        required=True,
        placeholder="Например: 24",
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        hours = parse_hours_input(str(self.duration_hours))
        if hours is None:
            await interaction.response.send_message("Укажите время розыгрыша целым числом часов.", ephemeral=True)
            return

        if interaction.guild is None or interaction.guild.id != FAMQ_GUILD_ID:
            await interaction.response.send_message("Команда доступна только на сервере ASIXEZ.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        reload_giveaways()
        giveaway_id = next_giveaway_id()
        save_giveaways()

        try:
            channel = interaction.guild.get_channel(GIVEAWAY_CHANNEL_ID) or await interaction.guild.fetch_channel(GIVEAWAY_CHANNEL_ID)
        except Exception:
            await interaction.followup.send("Канал розыгрышей не найден.", ephemeral=True)
            return

        if not isinstance(channel, discord.TextChannel):
            await interaction.followup.send("Канал розыгрышей недоступен.", ephemeral=True)
            return

        ends_at = datetime.now(timezone.utc) + timedelta(hours=hours)
        giveaway = {
            "id": giveaway_id,
            "creatorId": interaction.user.id,
            "channelId": channel.id,
            "messageId": 0,
            "conditions": str(self.conditions).strip(),
            "prize": str(self.prize).strip(),
            "durationHours": hours,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "endsAt": ends_at.isoformat(),
            "status": "active",
            "participants": [],
            "winnerId": 0,
        }
        giveaway_store["items"][str(giveaway_id)] = giveaway
        save_giveaways()

        message = await channel.send(
            content="@everyone",
            embed=build_giveaway_embed(giveaway, interaction.user.mention),
            view=GiveawayJoinView(giveaway_id),
            allowed_mentions=discord.AllowedMentions(everyone=True),
        )
        giveaway["messageId"] = message.id
        giveaway_store["items"][str(giveaway_id)] = giveaway
        save_giveaways()
        bot.add_view(GiveawayJoinView(giveaway_id), message_id=message.id)
        ensure_giveaway_task(giveaway_id)

        await interaction.followup.send(f"Розыгрыш #{giveaway_id} опубликован в <#{channel.id}>.", ephemeral=True)


class ApplicationModal(discord.ui.Modal):
    def __init__(self, server: str):
        title = f"Заявка — {get_server_plain_label(server)}"
        super().__init__(title=title, timeout=None)
        self.server = server

        self.irl_name = discord.ui.TextInput(
            label="Ваше имя IRL",
            max_length=40,
            required=True,
        )
        self.age_irl = discord.ui.TextInput(
            label="Ваш возраст IRL",
            max_length=20,
            required=True,
        )
        self.level_online = discord.ui.TextInput(
            label="Левел в игре & Онлайн и часовой пояс",
            max_length=150,
            required=True,
        )
        self.fraction = discord.ui.TextInput(
            label="Состоите во фракции? Если да — в какой?",
            max_length=150,
            required=True,
        )
        self.name_static = discord.ui.TextInput(
            label="Ник в игре & Static-ID",
            max_length=150,
            required=True,
        )

        self.add_item(self.irl_name)
        self.add_item(self.age_irl)
        self.add_item(self.level_online)
        self.add_item(self.fraction)
        self.add_item(self.name_static)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        project = get_project(interaction.guild if interaction.guild is not None else None)
        if interaction.guild is None or project is None:
            await interaction.response.send_message(
                "Это действие доступно только на разрешённых серверах проекта.",
                ephemeral=True,
            )
            return
        if not is_application_open(self.server, interaction.guild.id):
            await interaction.response.send_message(
                "Подача заявок на этот сервер сейчас закрыта.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        reload_applications()
        app_id = next_application_id()

        server_tag = get_server_tag(self.server)
        safe_username = "".join(ch if ch.isalnum() else "-" for ch in interaction.user.name.lower())[:16].strip("-") or "user"
        channel_name = f"famq-{server_tag}-{safe_username}-{app_id}"

        recruiter_roles = get_server_recruiter_roles(self.server, interaction.guild.id)
        application_channel = await create_application_thread(
            interaction.guild,
            project,
            name=channel_name,
            applicant=interaction.user,
            recruiter_role_ids=recruiter_roles,
            reason=f"{project['project_name']} application #{app_id}",
        )
        if application_channel is None:
            overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, read_message_history=True),
            }
            for role_id in recruiter_roles:
                role = interaction.guild.get_role(role_id)
                if role is not None:
                    overwrites[role] = discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True,
                    )
            add_global_application_observer_overwrites(interaction.guild, overwrites)
            try:
                category = interaction.guild.get_channel(int(project["application_category_id"]))
                application_channel = await interaction.guild.create_text_channel(
                    name=channel_name,
                    category=category if isinstance(category, discord.CategoryChannel) else None,
                    overwrites=overwrites,
                    reason=f"{project['project_name']} application #{app_id}",
                )
            except Exception:
                application_channel = None
        if application_channel is None:
            await interaction.followup.send(
                "Не удалось создать ветку для заявки. Проверьте права бота.",
                ephemeral=True,
            )
            return

        application = {
            "id": app_id,
            "server": self.server,
            "applicantId": interaction.user.id,
            "guildId": interaction.guild.id,
            "channelId": application_channel.id,
            "irlName": str(self.irl_name).strip(),
            "ageIrl": str(self.age_irl).strip(),
            "nameAge": f"{str(self.irl_name).strip()} | {str(self.age_irl).strip()}",
            "levelOnline": str(self.level_online).strip(),
            "fraction": str(self.fraction).strip(),
            "nameStatic": str(self.name_static).strip(),
            "status": "pending",
            "claimedBy": 0,
            "claimedAt": "",
            "submittedAt": datetime.now(timezone.utc).isoformat(),
            "decidedAt": "",
            "decidedBy": "",
            "applicationMessageId": "",
        }

        ping_content = build_application_ping_content(interaction.user.id)
        app_message = await application_channel.send(
            content=ping_content,
            embed=build_application_embed(application, interaction.user.name),
            view=RecruiterActionView(app_id),
            allowed_mentions=discord.AllowedMentions(roles=True, users=True),
        )

        application["applicationMessageId"] = app_message.id
        application_store["items"][str(app_id)] = application
        save_applications()
        bot.add_view(RecruiterActionView(app_id), message_id=app_message.id)

        server_label = get_server_plain_label(self.server)
        await interaction.followup.send(
            embed=build_dm_embed(
                "✅ Заявка принята",
                f"Ваша заявка **#{app_id}** ({server_label}) успешно подана!\nВаша ветка: <#{application_channel.id}>\n\nОжидайте ответа от рекрутера.",
            ),
            ephemeral=True,
        )
        asyncio.create_task(
            log_action(
                interaction.guild,
                f"<@{interaction.user.id}> подал заявку #{app_id} ({server_label}). Ветка: <#{application_channel.id}>",
            )
        )


class FriendVerificationModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Верификация для друзей", timeout=None)
        self.friend_name_game = discord.ui.TextInput(
            label="Ваше имя, фамилия в игре",
            max_length=120,
            required=True,
        )
        self.friend_family = discord.ui.TextInput(
            label="В какой семье вы состоите?",
            max_length=150,
            required=True,
        )
        self.add_item(self.friend_name_game)
        self.add_item(self.friend_family)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        project = get_project(interaction.guild if interaction.guild is not None else None)
        if interaction.guild is None or project is None or interaction.guild.id != FAMQ_GUILD_ID:
            await interaction.response.send_message(
                "Эта форма доступна только на сервере ASIXEZ.",
                ephemeral=True,
            )
            return
        if not is_application_open(FAMQ_SERVER_FRIEND_VERIFICATION, interaction.guild.id):
            await interaction.response.send_message(
                "Подача верификации для друзей сейчас закрыта.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        reload_applications()
        app_id = next_application_id()

        safe_username = "".join(ch if ch.isalnum() else "-" for ch in interaction.user.name.lower())[:16].strip("-") or "user"
        channel_name = f"friend-verify-{safe_username}-{app_id}"

        recruiter_roles = get_server_recruiter_roles(FAMQ_SERVER_FRIEND_VERIFICATION, interaction.guild.id)
        application_channel = await create_application_thread(
            interaction.guild,
            project,
            name=channel_name,
            applicant=interaction.user,
            recruiter_role_ids=recruiter_roles,
            reason=f"{project['project_name']} friend verification #{app_id}",
            include_global_observers=False,
        )
        if application_channel is None:
            overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, read_message_history=True),
            }
            for role_id in recruiter_roles:
                role = interaction.guild.get_role(role_id)
                if role is not None:
                    overwrites[role] = discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True,
                    )
            try:
                category = interaction.guild.get_channel(int(project["application_category_id"]))
                application_channel = await interaction.guild.create_text_channel(
                    name=channel_name,
                    category=category if isinstance(category, discord.CategoryChannel) else None,
                    overwrites=overwrites,
                    reason=f"{project['project_name']} friend verification #{app_id}",
                )
            except Exception:
                application_channel = None
        if application_channel is None:
            await interaction.followup.send(
                "Не удалось создать ветку для верификации. Проверьте права бота.",
                ephemeral=True,
            )
            return

        application = {
            "id": app_id,
            "server": FAMQ_SERVER_FRIEND_VERIFICATION,
            "kind": "friend_verification",
            "applicantId": interaction.user.id,
            "guildId": interaction.guild.id,
            "channelId": application_channel.id,
            "friendNameGame": str(self.friend_name_game).strip(),
            "friendFamily": str(self.friend_family).strip(),
            "status": "pending",
            "claimedBy": 0,
            "claimedAt": "",
            "submittedAt": datetime.now(timezone.utc).isoformat(),
            "decidedAt": "",
            "decidedBy": "",
            "applicationMessageId": "",
        }

        ping_content = build_application_ping_content(interaction.user.id, recruiter_roles)
        app_message = await application_channel.send(
            content=f"{ping_content}\nЗаявка на верификацию для друзей.",
            embed=build_application_embed(application, interaction.user.name),
            view=RecruiterActionView(app_id),
            allowed_mentions=discord.AllowedMentions(roles=True, users=True),
        )

        application["applicationMessageId"] = app_message.id
        application_store["items"][str(app_id)] = application
        save_applications()
        bot.add_view(RecruiterActionView(app_id), message_id=app_message.id)

        await interaction.followup.send(
            embed=build_dm_embed(
                "🤝 Верификация отправлена",
                f"Ваша заявка на верификацию для друзей **#{app_id}** успешно подана.\nВаша ветка: <#{application_channel.id}>\n\nОжидайте решения старшего состава.",
            ),
            ephemeral=True,
        )
        asyncio.create_task(
            log_action(
                interaction.guild,
                f"<@{interaction.user.id}> подал заявку на верификацию для друзей #{app_id}. Ветка: <#{application_channel.id}>",
            )
        )


class RejectModal(discord.ui.Modal):
    def __init__(self, app_id: int):
        super().__init__(title="Отклонить заявку", timeout=None)
        self.app_id = app_id
        self.reason = discord.ui.TextInput(
            label="Укажите причину отклонения",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=True,
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        member = interaction.user if isinstance(interaction.user, discord.Member) else None
        reload_applications()
        app = application_store["items"].get(str(self.app_id))
        if not app:
            await interaction.response.send_message("Заявка не найдена.", ephemeral=True)
            return
        if interaction.guild is None or not can_manage_application(member, app.get("server", FAMQ_SERVER_DETROIT), int(app.get("guildId", interaction.guild.id))):
            await interaction.response.send_message("Недостаточно прав.", ephemeral=True)
            return

        reject_reason = str(self.reason).strip()
        async with get_application_lock(self.app_id):
            reload_applications()
            app = application_store["items"].get(str(self.app_id))
            if not app:
                await interaction.response.send_message("Заявка не найдена.", ephemeral=True)
                return
            if app.get("status") in {"accepted", "rejected"}:
                await interaction.response.send_message("Заявка уже обработана.", ephemeral=True)
                return
            claimed_by = int(app.get("claimedBy") or 0)
            if claimed_by not in {0, interaction.user.id}:
                await interaction.response.send_message(
                    f"Эта заявка уже закреплена за рекрутером <@{claimed_by}>.",
                    ephemeral=True,
                )
                return

            app["claimedBy"] = interaction.user.id
            app["claimedAt"] = datetime.now(timezone.utc).isoformat()
            app["status"] = "rejected"
            app["decidedBy"] = interaction.user.id
            app["decidedAt"] = datetime.now(timezone.utc).isoformat()
            app["rejectReason"] = reject_reason
            application_store["items"][str(self.app_id)] = app
            save_applications()

        await lock_application_channel_to_recruiter(interaction.guild, app)
        await disable_buttons(interaction.guild, app)
        is_friend_verification = is_friend_verification_application(app.get("server", ""))
        await send_dm_or_fallback(
            interaction.guild,
            int(app["applicantId"]),
            build_dm_embed(
                "Верификация отклонена" if is_friend_verification else "Заявка отклонена",
                (
                    "\n".join(
                        [
                            "Ваше заявление на верификацию для друзей было отклонено.",
                            f"Проект: **{get_project_name(int(app.get('guildId', interaction.guild.id)))}**",
                            f"Рассматривал: <@{interaction.user.id}>",
                            f"**Причина:** {reject_reason}",
                        ]
                    )
                    if is_friend_verification
                    else "\n".join(
                        [
                            f"Ваша заявка в ASIXEZ была отклонена рекрутером: <@{interaction.user.id}>.",
                            f"Проект: **{get_project_name(int(app.get('guildId', interaction.guild.id)))}**",
                            f"**Причина:** {reject_reason}",
                            "Вы можете подать заявку повторно исправив свою ошибку.",
                        ]
                    )
                ),
            ),
        )
        await post_result(interaction.guild, app, interaction.user.id, "rejected", reject_reason)
        await log_action(
            interaction.guild,
            f"<@{interaction.user.id}> **отклонил** заявку #{self.app_id} от <@{app['applicantId']}>. Причина: {reject_reason}",
        )
        await interaction.response.send_message(
            f"Заявка #{self.app_id} отклонена. Ветка будет удалена.",
            ephemeral=True,
        )
        application_action_locks.pop(self.app_id, None)
        asyncio.create_task(delete_channel_later(int(app["channelId"]), "Заявка FAMQ отклонена"))


class VoiceRoomUserModal(discord.ui.Modal):
    def __init__(self, action: str):
        titles = {
            "speak": "Управление голосом",
            "kick": "Исключить пользователя",
            "transfer": "Передать владение",
            "access": "Управление доступом",
        }
        super().__init__(title=titles.get(action, "Управление комнатой"), timeout=None)
        self.action = action
        self.user_value = discord.ui.TextInput(
            label="Укажите @пользователя или ID",
            placeholder="@user или 123456789012345678",
            max_length=64,
            required=True,
        )
        self.add_item(self.user_value)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Сервер не найден.", ephemeral=True)
            return

        channel, room = await resolve_owned_voice_channel(interaction)
        if channel is None or room is None:
            return

        target = await fetch_target_member(interaction.guild, str(self.user_value).strip())
        if target is None:
            await interaction.response.send_message("Пользователь не найден.", ephemeral=True)
            return

        if self.action == "speak":
            overwrite = channel.overwrites_for(target)
            is_blocked = overwrite.speak is False
            overwrite.speak = None if is_blocked else False
            overwrite.view_channel = True if overwrite.view_channel is None else overwrite.view_channel
            overwrite.connect = True if overwrite.connect is None else overwrite.connect
            await channel.set_permissions(target, overwrite=overwrite, reason=f"Voice speak toggle by {interaction.user}")
            await interaction.response.send_message(
                f"{'Разрешил' if is_blocked else 'Запретил'} говорить пользователю {target.mention}.",
                ephemeral=True,
            )
            return

        if self.action == "kick":
            if target not in channel.members:
                await interaction.response.send_message("Этот пользователь сейчас не находится в вашей комнате.", ephemeral=True)
                return
            await target.move_to(None, reason=f"Voice room kick by {interaction.user}")
            await interaction.response.send_message(f"Пользователь {target.mention} исключён из комнаты.", ephemeral=True)
            return

        if self.action == "transfer":
            if target.id == interaction.user.id:
                await interaction.response.send_message("Вы уже являетесь владельцем этой комнаты.", ephemeral=True)
                return
            if target not in channel.members:
                await interaction.response.send_message(
                    "Передать владение можно только пользователю, который находится в вашей комнате.",
                    ephemeral=True,
                )
                return

            old_owner = interaction.guild.get_member(int(room.get("ownerId", interaction.user.id)))
            if old_owner is not None:
                await channel.set_permissions(
                    old_owner,
                    overwrite=discord.PermissionOverwrite(view_channel=True, connect=True, speak=True),
                    reason="Смена владельца временной комнаты",
                )
            await channel.set_permissions(
                target,
                overwrite=build_voice_owner_overwrite(),
                reason="Новый владелец временной комнаты",
            )
            room["ownerId"] = target.id
            room["name"] = channel.name
            set_voice_room(channel.id, room)
            await interaction.response.send_message(f"Права владельца переданы пользователю {target.mention}.", ephemeral=True)
            return

        if self.action == "access":
            if target.id == int(room.get("ownerId", 0)):
                await interaction.response.send_message("У владельца комнаты доступ нельзя забрать.", ephemeral=True)
                return
            overwrite = channel.overwrites_for(target)
            has_explicit_access = overwrite.connect is True
            overwrite.view_channel = True
            overwrite.connect = False if has_explicit_access else True
            await channel.set_permissions(target, overwrite=overwrite, reason=f"Voice access toggle by {interaction.user}")
            await interaction.response.send_message(
                f"{'Забрал' if has_explicit_access else 'Выдал'} доступ пользователю {target.mention}.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message("Неизвестное действие.", ephemeral=True)


class VoiceRoomRenameModal(discord.ui.Modal, title="Сменить название комнаты"):
    def __init__(self):
        super().__init__(timeout=None)
        self.room_name = discord.ui.TextInput(
            label="Новое название комнаты",
            placeholder="Введите новое название",
            max_length=80,
            required=True,
        )
        self.add_item(self.room_name)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        channel, room = await resolve_owned_voice_channel(interaction)
        if channel is None or room is None:
            return

        new_name = str(self.room_name).strip()
        if not new_name:
            await interaction.response.send_message("Название не может быть пустым.", ephemeral=True)
            return

        await channel.edit(name=new_name, reason=f"Voice room rename by {interaction.user}")
        room["name"] = new_name
        set_voice_room(channel.id, room)
        await interaction.response.send_message(f"Название комнаты изменено на **{discord.utils.escape_markdown(new_name)}**.", ephemeral=True)


class VoiceRoomBitrateModal(discord.ui.Modal, title="Изменить битрейт комнаты"):
    def __init__(self):
        super().__init__(timeout=None)
        self.bitrate = discord.ui.TextInput(
            label="Введите битрейт (например 96)",
            placeholder="Значение в kbps",
            max_length=8,
            required=True,
        )
        self.add_item(self.bitrate)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Сервер не найден.", ephemeral=True)
            return

        channel, _room = await resolve_owned_voice_channel(interaction)
        if channel is None:
            return

        raw_value = re.sub(r"[^\d]", "", str(self.bitrate))
        if not raw_value:
            await interaction.response.send_message("Укажите числовое значение битрейта.", ephemeral=True)
            return

        bitrate_value = int(raw_value)
        if bitrate_value <= 384:
            bitrate_value *= 1000
        bitrate_value = max(8000, min(bitrate_value, interaction.guild.bitrate_limit))

        await channel.edit(bitrate=bitrate_value, reason=f"Voice bitrate updated by {interaction.user}")
        await interaction.response.send_message(f"Битрейт комнаты изменён на **{bitrate_value // 1000} kbps**.", ephemeral=True)


class VoiceRoomSlotsModal(discord.ui.Modal, title="Установить количество слотов"):
    def __init__(self):
        super().__init__(timeout=None)
        self.slots = discord.ui.TextInput(
            label="Введите количество слотов",
            placeholder="От 0 до 99 (0 = без лимита)",
            max_length=3,
            required=True,
        )
        self.add_item(self.slots)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        channel, _room = await resolve_owned_voice_channel(interaction)
        if channel is None:
            return

        raw_value = re.sub(r"[^\d]", "", str(self.slots))
        if not raw_value:
            await interaction.response.send_message("Укажите число от 0 до 99.", ephemeral=True)
            return

        slots = int(raw_value)
        if slots < 0 or slots > 99:
            await interaction.response.send_message("Количество слотов должно быть от 0 до 99.", ephemeral=True)
            return
        if slots != 0 and slots < len(channel.members):
            await interaction.response.send_message(
                f"Сейчас в комнате {len(channel.members)} участников. Установите лимит не меньше этого числа.",
                ephemeral=True,
            )
            return

        await channel.edit(user_limit=slots, reason=f"Voice slots updated by {interaction.user}")
        label = "без лимита" if slots == 0 else str(slots)
        await interaction.response.send_message(f"Количество слотов обновлено: **{label}**.", ephemeral=True)


class VoiceRoomControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _owned_room(self, interaction: discord.Interaction) -> tuple[discord.VoiceChannel, dict[str, Any]] | tuple[None, None]:
        return await resolve_owned_voice_channel(interaction)

    @discord.ui.button(emoji=VOICE_EMOJI_ADD_SLOT, style=discord.ButtonStyle.secondary, custom_id="voice_room_add_slot", row=0)
    async def add_slot(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        channel, _room = await self._owned_room(interaction)
        if channel is None:
            return
        if channel.user_limit == 0:
            await interaction.response.send_message("В комнате уже установлен безлимит. Сначала задайте конкретное количество слотов.", ephemeral=True)
            return

        new_limit = min(channel.user_limit + 1, 99)
        if new_limit == channel.user_limit:
            await interaction.response.send_message("Достигнут максимальный лимит слотов.", ephemeral=True)
            return

        await channel.edit(user_limit=new_limit, reason=f"Voice slot add by {interaction.user}")
        await interaction.response.send_message(f"Добавил 1 слот. Теперь лимит комнаты: **{new_limit}**.", ephemeral=True)

    @discord.ui.button(emoji=VOICE_EMOJI_REMOVE_SLOT, style=discord.ButtonStyle.secondary, custom_id="voice_room_remove_slot", row=0)
    async def remove_slot(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        channel, _room = await self._owned_room(interaction)
        if channel is None:
            return
        if channel.user_limit == 0:
            await interaction.response.send_message("Сейчас у комнаты нет лимита. Установите количество слотов вручную.", ephemeral=True)
            return

        min_limit = max(1, len(channel.members))
        new_limit = max(min_limit, channel.user_limit - 1)
        if new_limit == channel.user_limit:
            await interaction.response.send_message("Сейчас нельзя уменьшить лимит ниже текущего числа участников.", ephemeral=True)
            return

        await channel.edit(user_limit=new_limit, reason=f"Voice slot remove by {interaction.user}")
        await interaction.response.send_message(f"Убрал 1 слот. Теперь лимит комнаты: **{new_limit}**.", ephemeral=True)

    @discord.ui.button(emoji=VOICE_EMOJI_LOCK, style=discord.ButtonStyle.secondary, custom_id="voice_room_lock", row=0)
    async def toggle_lock(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        channel, _room = await self._owned_room(interaction)
        if channel is None or interaction.guild is None:
            return

        overwrite = channel.overwrites_for(interaction.guild.default_role)
        is_locked = overwrite.connect is False
        overwrite.view_channel = True
        overwrite.connect = None if is_locked else False
        await channel.set_permissions(
            interaction.guild.default_role,
            overwrite=overwrite,
            reason=f"Voice lock toggle by {interaction.user}",
        )
        await interaction.response.send_message(
            "Вход в комнату разрешён для всех." if is_locked else "Вход в комнату запрещён для всех, кроме тех, у кого есть доступ.",
            ephemeral=True,
        )

    @discord.ui.button(emoji=VOICE_EMOJI_SPEAK, style=discord.ButtonStyle.secondary, custom_id="voice_room_speak", row=0)
    async def toggle_speak(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        channel, _room = await self._owned_room(interaction)
        if channel is None:
            return
        await interaction.response.send_modal(VoiceRoomUserModal("speak"))

    @discord.ui.button(emoji=VOICE_EMOJI_KICK, style=discord.ButtonStyle.secondary, custom_id="voice_room_kick", row=0)
    async def kick_user(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        channel, _room = await self._owned_room(interaction)
        if channel is None:
            return
        await interaction.response.send_modal(VoiceRoomUserModal("kick"))

    @discord.ui.button(emoji=VOICE_EMOJI_BITRATE, style=discord.ButtonStyle.secondary, custom_id="voice_room_bitrate", row=1)
    async def change_bitrate(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        channel, _room = await self._owned_room(interaction)
        if channel is None:
            return
        await interaction.response.send_modal(VoiceRoomBitrateModal())

    @discord.ui.button(emoji=VOICE_EMOJI_SET_SLOTS, style=discord.ButtonStyle.secondary, custom_id="voice_room_set_slots", row=1)
    async def set_slots(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        channel, _room = await self._owned_room(interaction)
        if channel is None:
            return
        await interaction.response.send_modal(VoiceRoomSlotsModal())

    @discord.ui.button(emoji=VOICE_EMOJI_TRANSFER, style=discord.ButtonStyle.secondary, custom_id="voice_room_transfer", row=1)
    async def transfer_owner(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        channel, _room = await self._owned_room(interaction)
        if channel is None:
            return
        await interaction.response.send_modal(VoiceRoomUserModal("transfer"))

    @discord.ui.button(emoji=VOICE_EMOJI_RENAME, style=discord.ButtonStyle.secondary, custom_id="voice_room_rename", row=1)
    async def rename_room(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        channel, _room = await self._owned_room(interaction)
        if channel is None:
            return
        await interaction.response.send_modal(VoiceRoomRenameModal())

    @discord.ui.button(emoji=VOICE_EMOJI_ACCESS, style=discord.ButtonStyle.secondary, custom_id="voice_room_access", row=1)
    async def toggle_access(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        channel, _room = await self._owned_room(interaction)
        if channel is None:
            return
        await interaction.response.send_modal(VoiceRoomUserModal("access"))

def get_application_lock(app_id: int) -> asyncio.Lock:
    lock = application_action_locks.get(app_id)
    if lock is None:
        lock = asyncio.Lock()
        application_action_locks[app_id] = lock
    return lock


def build_application_ping_content(applicant_id: int, role_ids: list[int] | None = None) -> str:
    mentions = [f"<@{applicant_id}>"]
    target_role_ids = GLOBAL_APPLICATION_PING_ROLE_IDS if role_ids is None else role_ids
    mentions.extend(f"<@&{role_id}>" for role_id in target_role_ids if role_id)
    unique_mentions = list(dict.fromkeys(mentions))
    return " ".join(unique_mentions)


def add_global_application_observer_overwrites(
    guild: discord.Guild,
    overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite],
) -> None:
    read_only_overwrite = discord.PermissionOverwrite(
        view_channel=True,
        read_message_history=True,
    )
    for role_id in GLOBAL_APPLICATION_PING_ROLE_IDS:
        role = guild.get_role(int(role_id)) if role_id else None
        if role is None or role in overwrites:
            continue
        overwrites[role] = read_only_overwrite


async def add_members_to_application_thread(
    thread: discord.Thread,
    applicant: discord.abc.User,
    recruiter_role_ids: list[int],
    include_global_observers: bool = True,
) -> None:
    try:
        await thread.add_user(applicant)
    except Exception:
        pass

    observer_role_ids = GLOBAL_APPLICATION_PING_ROLE_IDS if include_global_observers else []
    invited_ids = {applicant.id}
    for role_id in dict.fromkeys([*recruiter_role_ids, *observer_role_ids]):
        role = thread.guild.get_role(int(role_id)) if role_id else None
        if role is None:
            continue
        for member in role.members[:40]:
            if member.bot or member.id in invited_ids:
                continue
            invited_ids.add(member.id)
            try:
                await thread.add_user(member)
            except Exception:
                continue


async def create_application_thread(
    guild: discord.Guild,
    project: dict[str, Any],
    *,
    name: str,
    applicant: discord.abc.User,
    recruiter_role_ids: list[int],
    reason: str,
    include_global_observers: bool = True,
) -> discord.Thread | None:
    parent_channel_id = int(project.get("panel_channel_id") or 0)
    if parent_channel_id <= 0:
        return None
    try:
        parent = guild.get_channel(parent_channel_id) or await guild.fetch_channel(parent_channel_id)
    except Exception:
        return None
    if not isinstance(parent, discord.TextChannel):
        return None

    try:
        thread = await parent.create_thread(
            name=name[:90],
            type=discord.ChannelType.private_thread,
            invitable=False,
            auto_archive_duration=1440,
            reason=reason,
        )
    except Exception:
        try:
            thread = await parent.create_thread(
                name=name[:90],
                type=discord.ChannelType.public_thread,
                auto_archive_duration=1440,
                reason=reason,
            )
        except Exception:
            return None

    await add_members_to_application_thread(thread, applicant, recruiter_role_ids, include_global_observers)
    return thread


async def ensure_application_channel_observers(
    guild: discord.Guild,
    channel: discord.TextChannel,
) -> None:
    read_only_overwrite = discord.PermissionOverwrite(
        view_channel=True,
        read_message_history=True,
    )
    current_overwrites = channel.overwrites
    for role_id in GLOBAL_APPLICATION_PING_ROLE_IDS:
        role = guild.get_role(int(role_id)) if role_id else None
        if role is None or role in current_overwrites:
            continue
        try:
            await channel.set_permissions(
                role,
                overwrite=read_only_overwrite,
                reason="Global application observer access",
            )
        except Exception:
            continue


async def lock_application_channel_to_recruiter(
    guild: discord.Guild,
    application: dict[str, Any],
) -> None:
    channel_id = application.get("channelId")
    claimed_by = int(application.get("claimedBy") or 0)
    if not channel_id or claimed_by <= 0:
        return

    try:
        channel = guild.get_channel(int(channel_id)) or await guild.fetch_channel(int(channel_id))
    except Exception:
        return

    if isinstance(channel, discord.Thread):
        claimant = guild.get_member(claimed_by)
        if claimant is None:
            try:
                claimant = await guild.fetch_member(claimed_by)
            except Exception:
                claimant = None
        if claimant is not None:
            try:
                await channel.add_user(claimant)
            except Exception:
                pass
        return

    if not text_sendable(channel):
        return

    recruiter_role_ids = set(
        get_server_recruiter_roles(
            application.get("server", FAMQ_SERVER_DETROIT),
            int(application.get("guildId", guild.id)),
        )
    )
    recruiter_role_ids.update(int(role_id) for role_id in GLOBAL_APPLICATION_PING_ROLE_IDS if int(role_id))
    if not recruiter_role_ids:
        return

    applicant_id = int(application.get("applicantId") or 0)
    denied_overwrite = discord.PermissionOverwrite(
        view_channel=False,
        send_messages=False,
        read_message_history=False,
    )
    allow_overwrite = discord.PermissionOverwrite(
        view_channel=True,
        send_messages=True,
        read_message_history=True,
    )

    claimant = guild.get_member(claimed_by)
    if claimant is None:
        try:
            claimant = await guild.fetch_member(claimed_by)
        except Exception:
            claimant = None
    if claimant is not None:
        try:
            await channel.set_permissions(
                claimant,
                overwrite=allow_overwrite,
                reason=f"Application #{application.get('id')} claimed by recruiter",
            )
        except Exception:
            pass

    for member in channel.members:
        if member.bot or member.id in {applicant_id, claimed_by}:
            continue
        member_role_ids = {role.id for role in member.roles}
        if recruiter_role_ids.isdisjoint(member_role_ids):
            continue
        try:
            await channel.set_permissions(
                member,
                overwrite=denied_overwrite,
                reason=f"Application #{application.get('id')} locked to recruiter {claimed_by}",
            )
        except Exception:
            continue


async def show_application_modal(
    interaction: discord.Interaction,
    server: str,
    guild_id: int,
) -> None:
    if not is_application_open(server, guild_id):
        await interaction.response.send_message("Подача заявок на этот сервер сейчас закрыта.", ephemeral=True)
        return
    if server == FAMQ_SERVER_FRIEND_VERIFICATION:
        await interaction.response.send_modal(FriendVerificationModal())
        return
    await interaction.response.send_modal(ApplicationModal(server))


class FamqPanelView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        project = get_project(guild_id)
        visible_options = get_visible_application_options(guild_id)

        if not visible_options:
            self.add_item(
                discord.ui.Button(
                    custom_id=f"famq_apply_closed_{guild_id}",
                    label="Набор временно закрыт",
                    style=discord.ButtonStyle.secondary,
                    disabled=True,
                )
            )
        elif len(visible_options) <= 1:
            apply_button = discord.ui.Button(
                custom_id=f"famq_apply_{guild_id}",
                label="Подать заявку",
                style=discord.ButtonStyle.secondary,
            )
            apply_button.callback = self.apply_callback
            self.add_item(apply_button)
        else:
            select = discord.ui.Select(
                custom_id=f"{PANEL_SELECT_ID}_{guild_id}",
                placeholder="Выберите сервер или верификацию",
                min_values=1,
                max_values=1,
                options=[
                    discord.SelectOption(
                        label=option["label"],
                        value=option["key"],
                        description="Открытая подача анкеты",
                    )
                    for option in visible_options
                ],
            )
            select.callback = self.select_callback
            self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction) -> None:
        selected = self.children[0]
        if not isinstance(selected, discord.ui.Select) or not selected.values:
            await interaction.response.send_message("Не удалось определить сервер.", ephemeral=True)
            return
        await show_application_modal(interaction, selected.values[0], self.guild_id)

    async def apply_callback(self, interaction: discord.Interaction) -> None:
        options = get_visible_application_options(self.guild_id)
        if not options:
            await interaction.response.send_message("Подача заявок сейчас недоступна.", ephemeral=True)
            return
        await show_application_modal(interaction, options[0]["key"], self.guild_id)


class RecruiterActionView(discord.ui.View):
    def __init__(self, app_id: int, disabled: bool = False):
        super().__init__(timeout=None)
        self.app_id = app_id

        review_button = discord.ui.Button(
            custom_id=f"{BTN_REVIEW_PREFIX}{app_id}",
            label="Взять на рассмотрение",
            style=discord.ButtonStyle.secondary,
            disabled=disabled,
        )
        review_button.callback = self.review_callback
        self.add_item(review_button)

        call_button = discord.ui.Button(
            custom_id=f"{BTN_CALL_PREFIX}{app_id}",
            label="Вызвать на обзвон",
            style=discord.ButtonStyle.secondary,
            disabled=disabled,
        )
        call_button.callback = self.call_callback
        self.add_item(call_button)

        accept_button = discord.ui.Button(
            custom_id=f"{BTN_ACCEPT_PREFIX}{app_id}",
            label="Принять заявку",
            style=discord.ButtonStyle.secondary,
            disabled=disabled,
        )
        accept_button.callback = self.accept_callback
        self.add_item(accept_button)

        reject_button = discord.ui.Button(
            custom_id=f"{BTN_REJECT_PREFIX}{app_id}",
            label="Отклонить заявку",
            style=discord.ButtonStyle.secondary,
            disabled=disabled,
        )
        reject_button.callback = self.reject_callback
        self.add_item(reject_button)

    async def _guard(self, interaction: discord.Interaction) -> dict[str, Any] | None:
        member = interaction.user if isinstance(interaction.user, discord.Member) else None
        reload_applications()
        app = application_store["items"].get(str(self.app_id))
        if not app:
            await interaction.response.send_message("Заявка не найдена.", ephemeral=True)
            return None
        if interaction.guild is None or not can_manage_application(member, app.get("server", FAMQ_SERVER_DETROIT), int(app.get("guildId", interaction.guild.id))):
            await interaction.response.send_message("Эта кнопка доступна только назначенным ролям этого сервера.", ephemeral=True)
            return None
        return app

    def _claimed_by_other(self, app: dict[str, Any], user_id: int) -> bool:
        claimed_by = int(app.get("claimedBy") or 0)
        return claimed_by not in {0, user_id}

    async def review_callback(self, interaction: discord.Interaction) -> None:
        app = await self._guard(interaction)
        if app is None:
            return
        async with get_application_lock(self.app_id):
            reload_applications()
            app = application_store["items"].get(str(self.app_id))
            if not app:
                await interaction.response.send_message("Заявка не найдена.", ephemeral=True)
                return
            if app.get("status") in {"accepted", "rejected"}:
                await interaction.response.send_message("Заявка уже обработана.", ephemeral=True)
                return
            if self._claimed_by_other(app, interaction.user.id):
                await interaction.response.send_message(
                    f"Эта заявка уже закреплена за рекрутером <@{app['claimedBy']}>.",
                    ephemeral=True,
                )
                return

            app["claimedBy"] = interaction.user.id
            app["claimedAt"] = datetime.now(timezone.utc).isoformat()
            application_store["items"][str(self.app_id)] = app
            save_applications()

        await lock_application_channel_to_recruiter(interaction.guild, app)
        await refresh_application_message(interaction.guild, app)
        if text_sendable(interaction.channel):
            await interaction.channel.send(
                content=f"<@{app['applicantId']}> Ваша заявка взята на рассмотрение рекрутером <@{interaction.user.id}>.",
                allowed_mentions=discord.AllowedMentions(users=True),
            )
        await log_action(
            interaction.guild,
            f"<@{interaction.user.id}> взял на рассмотрение заявку #{self.app_id} от <@{app['applicantId']}>",
        )
        await interaction.response.send_message(
            f"Заявка #{self.app_id} закреплена за вами.",
            ephemeral=True,
        )

    async def call_callback(self, interaction: discord.Interaction) -> None:
        app = await self._guard(interaction)
        if app is None:
            return
        if self._claimed_by_other(app, interaction.user.id):
            await interaction.response.send_message(
                f"Заявка закреплена за рекрутером <@{app['claimedBy']}>.",
                ephemeral=True,
            )
            return
        if not int(app.get("claimedBy") or 0):
            app["claimedBy"] = interaction.user.id
            app["claimedAt"] = datetime.now(timezone.utc).isoformat()
            application_store["items"][str(self.app_id)] = app
            save_applications()
            await lock_application_channel_to_recruiter(interaction.guild, app)
            await refresh_application_message(interaction.guild, app)
        project = get_project(int(app.get("guildId", interaction.guild.id if interaction.guild else 0)))
        interview_channel_ids = list(project.get("interview_channel_ids", [])) if project else []
        if not interview_channel_ids:
            await interaction.response.send_message("Для этого проекта каналы обзвона пока не настроены.", ephemeral=True)
            return
        await interaction.response.send_message(
            "Выберите канал для обзвона:",
            view=CallSelectView(self.app_id, interview_channel_ids),
            ephemeral=True,
        )

    async def accept_callback(self, interaction: discord.Interaction) -> None:
        app = await self._guard(interaction)
        if app is None:
            return
        async with get_application_lock(self.app_id):
            reload_applications()
            app = application_store["items"].get(str(self.app_id))
            if not app:
                await interaction.response.send_message("Заявка не найдена.", ephemeral=True)
                return
            if app.get("status") in {"accepted", "rejected"}:
                await interaction.response.send_message("Заявка уже обработана.", ephemeral=True)
                return
            if self._claimed_by_other(app, interaction.user.id):
                await interaction.response.send_message(
                    f"Эта заявка уже закреплена за рекрутером <@{app['claimedBy']}>.",
                    ephemeral=True,
                )
                return

            app["claimedBy"] = interaction.user.id
            app["claimedAt"] = datetime.now(timezone.utc).isoformat()
            app["status"] = "accepted"
            app["decidedBy"] = interaction.user.id
            app["decidedAt"] = datetime.now(timezone.utc).isoformat()
            application_store["items"][str(self.app_id)] = app
            save_applications()

        await interaction.response.defer(ephemeral=True)
        await lock_application_channel_to_recruiter(interaction.guild, app)
        accept_role_id = get_server_accept_role_id(app.get("server", FAMQ_SERVER_DETROIT), int(app.get("guildId", interaction.guild.id)))
        member = interaction.guild.get_member(int(app["applicantId"]))
        if member is None:
            try:
                member = await interaction.guild.fetch_member(int(app["applicantId"]))
            except Exception:
                member = None

        is_friend_verification = is_friend_verification_application(app.get("server", ""))
        if member is not None:
            roles_to_add: list[discord.Role] = []
            if is_friend_verification:
                role = interaction.guild.get_role(int(accept_role_id)) if accept_role_id else None
                if role is not None:
                    roles_to_add.append(role)
            else:
                for role_id in (APPLICATION_ACADEMY_ROLE_ID, FAMQ_ACCEPT_ROLE_ID):
                    role = interaction.guild.get_role(int(role_id))
                    if role is not None:
                        roles_to_add.append(role)
            if roles_to_add:
                try:
                    await member.add_roles(*list(dict.fromkeys(roles_to_add)), reason="FAMQ application accepted")
                except Exception:
                    pass

            if not is_friend_verification:
                try:
                    await member.edit(
                        nick=build_asx_member_nickname(app),
                        reason="Accepted FAMQ application nickname format",
                    )
                except Exception:
                    pass

        await disable_buttons(interaction.guild, app)
        await send_dm_or_fallback(
            interaction.guild,
            int(app["applicantId"]),
            build_dm_embed(
                "Верификация одобрена" if is_friend_verification else "Заявка принята",
                (
                    "Вы успешно прошли верификацию на друга, в семье ASIXEZ. "
                    "Просьба поставить ник по форме на нашем сервере: Имя (IRL) | Имя/Ник(В игре)"
                    if is_friend_verification
                    else "\n".join(
                        [
                            f"Ваша заявка была успешно принята рекрутером: **<@{interaction.user.id}>**.",
                            "- Для получения инвайта обратитесь к любому старшему в игре.",
                            "- На данный момент Вы в академии семьи, чтобы получить ранг смените фамилию в игре на ASIXEZ, и обратитесь к любому старшему для повышения.",
                            "- Если Вы не вводили промокод, то введите в чат `/promo FED`, и получите 50.000$ при достижении 3 уровня, и дополнительные 50.000 от нашей семьи за ввод промокода.",
                        ]
                    )
                ),
            ),
        )
        await post_result(interaction.guild, app, interaction.user.id, "accepted")
        await log_action(
            interaction.guild,
            f"<@{interaction.user.id}> **принял** заявку #{self.app_id} от <@{app['applicantId']}>",
        )
        await interaction.followup.send(
            f"Заявка #{self.app_id} принята. Ветка будет удалена.",
            ephemeral=True,
        )
        application_action_locks.pop(self.app_id, None)
        asyncio.create_task(delete_channel_later(int(app["channelId"]), "Заявка FAMQ принята"))

    async def reject_callback(self, interaction: discord.Interaction) -> None:
        app = await self._guard(interaction)
        if app is None:
            return
        if app.get("status") in {"accepted", "rejected"}:
            await interaction.response.send_message("Заявка уже обработана.", ephemeral=True)
            return
        if self._claimed_by_other(app, interaction.user.id):
            await interaction.response.send_message(
                f"Эта заявка уже закреплена за рекрутером <@{app['claimedBy']}>.",
                ephemeral=True,
            )
            return
        await interaction.response.send_modal(RejectModal(self.app_id))


class CallSelectView(discord.ui.View):
    def __init__(self, app_id: int, interview_channel_ids: list[int]):
        super().__init__(timeout=180)
        self.app_id = app_id
        options = [
            discord.SelectOption(
                label=f"Канал для обзвона #{index + 1}",
                value=str(channel_id),
                description=f"ID: {channel_id}",
            )
            for index, channel_id in enumerate(interview_channel_ids)
        ]
        select = discord.ui.Select(
            custom_id=f"{SELECT_CALL_PREFIX}{app_id}",
            placeholder="Выберите канал для обзвона",
            min_values=1,
            max_values=1,
            options=options,
        )
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction) -> None:
        member = interaction.user if isinstance(interaction.user, discord.Member) else None
        selected = self.children[0]
        if not isinstance(selected, discord.ui.Select) or not selected.values:
            await interaction.response.send_message("Канал не выбран.", ephemeral=True)
            return

        reload_applications()
        app = application_store["items"].get(str(self.app_id))
        if not app:
            await interaction.response.send_message("Заявка не найдена.", ephemeral=True)
            return
        if interaction.guild is None or not can_manage_application(member, app.get("server", FAMQ_SERVER_DETROIT), int(app.get("guildId", interaction.guild.id))):
            await interaction.response.send_message("Недостаточно прав.", ephemeral=True)
            return
        claimed_by = int(app.get("claimedBy") or 0)
        if claimed_by not in {0, interaction.user.id}:
            await interaction.response.send_message(
                f"Эта заявка закреплена за рекрутером <@{claimed_by}>.",
                ephemeral=True,
            )
            return

        selected_channel_id = int(selected.values[0])
        project = get_project(int(app.get("guildId", interaction.guild.id)))
        waiting_channel_id = int(project["waiting_channel_id"]) if project and project.get("waiting_channel_id") else None
        if text_sendable(interaction.channel):
            await interaction.channel.send(
                content=(
                    f"<@{app['applicantId']}> Вы были вызваны на обзвон рекрутером <@{interaction.user.id}> "
                    + (
                        f"в канал <#{selected_channel_id}>."
                        if waiting_channel_id is None
                        else f"в канал <#{selected_channel_id}>. Для прохождения зайдите в канал ожидания: <#{waiting_channel_id}>."
                    )
                ),
                allowed_mentions=discord.AllowedMentions(users=True),
            )
        await log_action(
            interaction.guild,
            f"<@{interaction.user.id}> **вызвал на обзвон** заявителя <@{app['applicantId']}> (заявка #{self.app_id}) в канал <#{selected_channel_id}>",
        )
        await interaction.response.edit_message(
            content=f"Заявитель <@{app['applicantId']}> вызван на обзвон в <#{selected_channel_id}>.",
            view=None,
        )


async def disable_buttons(guild: discord.Guild, application: dict[str, Any]) -> None:
    channel_id = application.get("channelId")
    message_id = application.get("applicationMessageId")
    if not channel_id or not message_id:
        return

    try:
        channel = guild.get_channel(int(channel_id)) or await guild.fetch_channel(int(channel_id))
    except Exception:
        return

    if not isinstance(channel, discord.TextChannel):
        return

    try:
        message = await channel.fetch_message(int(message_id))
    except Exception:
        return

    await message.edit(view=RecruiterActionView(int(application["id"]), disabled=True))


async def refresh_application_message(guild: discord.Guild, application: dict[str, Any]) -> None:
    channel_id = application.get("channelId")
    message_id = application.get("applicationMessageId")
    if not channel_id or not message_id:
        return

    try:
        channel = guild.get_channel(int(channel_id)) or await guild.fetch_channel(int(channel_id))
    except Exception:
        return

    if not text_sendable(channel):
        return

    try:
        message = await channel.fetch_message(int(message_id))
    except Exception:
        return

    applicant_tag = f"user-{application['applicantId']}"
    try:
        user = guild.get_member(int(application["applicantId"])) or await bot.fetch_user(int(application["applicantId"]))
        applicant_tag = getattr(user, "display_name", None) or getattr(user, "name", applicant_tag)
    except Exception:
        pass

    await message.edit(
        embed=build_application_embed(application, applicant_tag),
        view=RecruiterActionView(int(application["id"]), disabled=application.get("status") != "pending"),
    )


async def refresh_pending_application_messages(guild: discord.Guild) -> int:
    reload_applications()
    refreshed = 0

    for app in application_store.get("items", {}).values():
        if int(app.get("guildId", 0)) != guild.id:
            continue
        if app.get("status") != "pending":
            continue

        try:
            channel = guild.get_channel(int(app["channelId"])) or await guild.fetch_channel(int(app["channelId"]))
        except Exception:
            continue

        if not text_sendable(channel):
            continue

        if isinstance(channel, discord.TextChannel):
            await ensure_application_channel_observers(guild, channel)

        ping_role_ids = (
            get_server_recruiter_roles(FAMQ_SERVER_FRIEND_VERIFICATION, guild.id)
            if is_friend_verification_application(str(app.get("server", "")))
            else None
        )
        ping_content = build_application_ping_content(int(app["applicantId"]), ping_role_ids)
        applicant_tag = f"user-{app['applicantId']}"
        try:
            user = guild.get_member(int(app["applicantId"])) or await bot.fetch_user(int(app["applicantId"]))
            applicant_tag = getattr(user, "display_name", None) or getattr(user, "name", applicant_tag)
        except Exception:
            pass

        message = None
        old_message_id = app.get("applicationMessageId")
        if old_message_id:
            try:
                message = await channel.fetch_message(int(old_message_id))
                await message.edit(
                    embed=build_application_embed(app, applicant_tag),
                    view=RecruiterActionView(int(app["id"])),
                )
            except Exception:
                message = None
        if message is None:
            message = await channel.send(
                content=ping_content,
                embed=build_application_embed(app, applicant_tag),
                view=RecruiterActionView(int(app["id"])),
                allowed_mentions=discord.AllowedMentions(roles=True, users=True),
            )
            app["applicationMessageId"] = message.id
            application_store["items"][str(app["id"])] = app
        bot.add_view(RecruiterActionView(int(app["id"])), message_id=message.id)
        if int(app.get("claimedBy") or 0):
            await lock_application_channel_to_recruiter(guild, app)
        refreshed += 1

    if refreshed:
        save_applications()

    return refreshed


async def ensure_panel_message(guild: discord.Guild, channel_id: int, panel_key: str, embeds: list[discord.Embed], force_recreate: bool = False) -> bool:
    try:
        channel = guild.get_channel(channel_id) or await guild.fetch_channel(channel_id)
    except Exception:
        return False

    if not isinstance(channel, discord.TextChannel):
        return False

    if force_recreate:
        await cleanup_bot_messages(channel)

    stored = panel_store.get(panel_key, {})
    existing_ids = stored.get("messageIds", [])
    if not force_recreate and isinstance(existing_ids, list) and len(existing_ids) == len(embeds):
        messages: list[discord.Message] = []
        for message_id in existing_ids:
            try:
                messages.append(await channel.fetch_message(int(message_id)))
            except Exception:
                messages = []
                break
        if messages:
            for index, message in enumerate(messages):
                await message.edit(embed=embeds[index])
            return False

    for message_id in existing_ids if isinstance(existing_ids, list) else []:
        try:
            message = await channel.fetch_message(int(message_id))
            await delete_message_safely(message)
        except Exception:
            pass

    created_ids: list[int] = []
    for embed in embeds:
        message = await channel.send(embed=embed)
        created_ids.append(message.id)

    panel_store[panel_key] = {"messageIds": created_ids, "channelId": channel.id}
    save_panels()
    return True


async def disable_panel_publication(guild: discord.Guild, channel_id: int, panel_key: str) -> bool:
    try:
        channel = guild.get_channel(channel_id) or await guild.fetch_channel(channel_id)
    except Exception:
        channel = None

    if isinstance(channel, discord.TextChannel):
        await cleanup_bot_messages(channel)

    panel_store.pop(panel_key, None)
    save_panels()
    return False


async def ensure_guild_members_loaded(guild: discord.Guild) -> None:
    try:
        await asyncio.wait_for(guild.chunk(cache=True), timeout=15)
    except Exception as error:
        console_log(f"Member chunk skipped for guild {guild.id}: {error}")


async def publish_staff_panel(guild: discord.Guild) -> bool:
    if guild.id != FAMQ_GUILD_ID:
        return False
    try:
        channel = guild.get_channel(FAMQ_STAFF_PANEL_CHANNEL_ID) or await guild.fetch_channel(FAMQ_STAFF_PANEL_CHANNEL_ID)
    except Exception as error:
        console_log(f"Staff panel channel fetch failed: {error}")
        return False
    if not isinstance(channel, discord.TextChannel):
        console_log(f"Staff panel channel is not text channel: {type(channel)!r}")
        return False

    try:
        await cleanup_bot_messages(channel)
        await channel.send(embed=build_staff_panel_embed(guild))
        console_log(f"Staff panel published to {channel.id}")
        return True
    except Exception as error:
        console_log(f"Staff panel publish failed: {error}")
        return False


async def publish_nickname_report(guild: discord.Guild) -> bool:
    if guild.id != FAMQ_GUILD_ID:
        return False
    try:
        channel = guild.get_channel(FAMQ_NICKNAME_REPORT_CHANNEL_ID) or await guild.fetch_channel(FAMQ_NICKNAME_REPORT_CHANNEL_ID)
    except Exception as error:
        console_log(f"Nickname report channel fetch failed: {error}")
        return False
    if not isinstance(channel, discord.TextChannel):
        console_log(f"Nickname report channel is not text channel: {type(channel)!r}")
        return False

    try:
        bad_members = get_members_with_bad_nicknames(guild)
        await cleanup_bot_messages(channel)
        content = " ".join(member.mention for member, _prefix in bad_members[:35]) if bad_members else None
        await channel.send(
            content=content,
            embed=build_nickname_report_embed(guild, bad_members),
            view=NicknameSelfFixView() if bad_members else None,
            allowed_mentions=discord.AllowedMentions(users=True),
        )
        console_log(f"Nickname report published to {channel.id}: {len(bad_members)} bad nicknames")
        return True
    except Exception as error:
        console_log(f"Nickname report publish failed: {error}")
        return False


async def publish_staff_and_nickname_panels(guild: discord.Guild) -> list[str]:
    issues: list[str] = []
    if guild.id != FAMQ_GUILD_ID:
        return issues
    await ensure_guild_members_loaded(guild)
    if not await publish_staff_panel(guild):
        issues.append("панель состава не была опубликована: проверьте канал 1533085586880200744 и права бота")
    if not await publish_nickname_report(guild):
        issues.append("отчёт по никнеймам не был опубликован: проверьте канал 1533219952591376384 и права бота")
    return issues


async def publish_staff_and_nickname_panels_later(guild: discord.Guild, delay_seconds: float = 3.0) -> None:
    await asyncio.sleep(delay_seconds)
    try:
        issues = await publish_staff_and_nickname_panels(guild)
        if issues:
            console_log("Staff/nickname publication issues: " + " | ".join(issues))
    except Exception as error:
        console_log(f"Staff/nickname background publication failed: {error}")


async def create_or_update_main_panel(guild: discord.Guild, force_recreate: bool = False) -> bool:
    project = get_project(guild)
    if project is None:
        return False
    try:
        channel = guild.get_channel(int(project["panel_channel_id"])) or await guild.fetch_channel(int(project["panel_channel_id"]))
    except Exception:
        return False
    if not isinstance(channel, discord.TextChannel):
        return False

    if force_recreate:
        await cleanup_bot_messages(channel)

    stored = panel_store.get(get_project_panel_key(PANEL_KEY, guild.id), {})
    if not force_recreate and stored.get("messageId"):
        try:
            if FAMILY_BRAND_BANNER_URL and stored.get("imageMessageId"):
                banner_message = await channel.fetch_message(int(stored["imageMessageId"]))
                banner_embed = make_embed(color=COLOR_PANEL)
                banner_embed.set_image(url=FAMILY_BRAND_BANNER_URL)
                await banner_message.edit(embed=banner_embed)
            panel_message = await channel.fetch_message(int(stored["messageId"]))
            await panel_message.edit(embed=build_panel_embed(guild.id), view=FamqPanelView(guild.id))
            return False
        except Exception:
            pass

    for key in ("imageMessageId", "messageId"):
        message_id = stored.get(key)
        if not message_id:
            continue
        try:
            message = await channel.fetch_message(int(message_id))
            await delete_message_safely(message)
        except Exception:
            pass

    image_message = None
    if FAMILY_BRAND_BANNER_URL:
        banner_embed = make_embed(color=COLOR_PANEL)
        banner_embed.set_image(url=FAMILY_BRAND_BANNER_URL)
        image_message = await channel.send(embed=banner_embed)
    panel_message = await channel.send(embed=build_panel_embed(guild.id), view=FamqPanelView(guild.id))
    panel_store[get_project_panel_key(PANEL_KEY, guild.id)] = {
        "imageMessageId": image_message.id if image_message is not None else 0,
        "messageId": panel_message.id,
        "channelId": channel.id,
    }
    save_panels()
    return True


async def create_or_update_info_panel(guild: discord.Guild, force_recreate: bool = False) -> bool:
    project = get_project(guild)
    if project is None:
        return False
    return await disable_panel_publication(
        guild,
        int(project["info_channel_id"]),
        get_project_panel_key(INFO_PANEL_KEY, guild.id),
    )


async def create_or_update_contracts_panel(guild: discord.Guild, force_recreate: bool = False) -> bool:
    project = get_project(guild)
    if project is None:
        return False
    return await disable_panel_publication(
        guild,
        int(project["contracts_channel_id"]),
        get_project_panel_key(CONTRACTS_PANEL_KEY, guild.id),
    )


async def create_or_update_fleet_panel(guild: discord.Guild, force_recreate: bool = False) -> bool:
    project = get_project(guild)
    if project is None:
        return False
    return await disable_panel_publication(
        guild,
        int(project["fleet_channel_id"]),
        get_project_panel_key(FLEET_PANEL_KEY, guild.id),
    )


async def create_or_update_voice_panel(guild: discord.Guild, force_recreate: bool = False) -> bool:
    project = get_project(guild)
    if project is None:
        return False
    try:
        channel = guild.get_channel(int(project["voice_panel_channel_id"])) or await guild.fetch_channel(int(project["voice_panel_channel_id"]))
    except Exception:
        return False

    if not isinstance(channel, discord.TextChannel):
        return False

    if force_recreate:
        await cleanup_bot_messages(channel)

    stored = panel_store.get(get_project_panel_key(VOICE_PANEL_KEY, guild.id), {})
    message_id = stored.get("messageId")

    if not force_recreate and message_id:
        try:
            message = await channel.fetch_message(int(message_id))
            await message.edit(embed=build_voice_panel_embed(), view=VoiceRoomControlView())
            return False
        except Exception:
            pass

    if message_id:
        try:
            old_message = await channel.fetch_message(int(message_id))
            await delete_message_safely(old_message)
        except Exception:
            pass

    message = await channel.send(embed=build_voice_panel_embed(), view=VoiceRoomControlView())
    panel_store[get_project_panel_key(VOICE_PANEL_KEY, guild.id)] = {
        "messageId": message.id,
        "channelId": channel.id,
    }
    save_panels()
    return True


def has_application_control_access(
    member: discord.Member | None,
    server: str | None = None,
    guild_id: int | None = None,
) -> bool:
    if member is None:
        return False
    role_ids = (
        get_server_manager_roles(server, guild_id or member.guild.id)
        if server is not None
        else get_application_control_roles(guild_id or member.guild.id)
    )
    return member_has_any_role(member, role_ids)


async def announce_application_state_change(guild: discord.Guild, server: str, is_open: bool) -> None:
    try:
        channel = guild.get_channel(APPLICATION_ANNOUNCE_CHANNEL_ID) or await guild.fetch_channel(APPLICATION_ANNOUNCE_CHANNEL_ID)
    except Exception:
        return

    if not text_sendable(channel):
        return

    server_name = get_server_plain_label(server)
    project = get_project(guild)
    application_link = (
        f"https://discord.com/channels/{guild.id}/{int(project['panel_channel_id'])}"
        if project and project.get("panel_channel_id")
        else "https://discord.com/channels/1466147160763666472/1466147735873786200"
    )
    if is_open:
        content = (
            "Приветствую, @everyone \n\n"
            f'Заявки на сервер "{server_name}" вновь открыты! Подать заявку можно тут: {application_link}.'
        )
    else:
        content = (
            "Приветствую, @everyone \n\n"
            f'Заявки на сервер "{server_name}" временно закрыты. '
            "О открытии команда семьи сообщит вам позже.\n\n"
            "Хорошего дня."
        )

    await channel.send(content, allowed_mentions=discord.AllowedMentions(everyone=True))


class ApplicationToggleView(discord.ui.View):
    def __init__(self, guild_id: int, action: str, author_id: int):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self.action = action
        self.author_id = author_id
        options = get_manageable_application_options(guild_id)
        select = discord.ui.Select(
            placeholder="Выберите сервер",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(
                    label=option["label"],
                    value=option["key"],
                    description="Открыть набор" if action == "open" else "Закрыть набор",
                )
                for option in options
            ],
        )
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Сервер не найден.", ephemeral=True)
            return
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Этим меню может пользоваться только автор команды.", ephemeral=True)
            return
        select = self.children[0]
        if not isinstance(select, discord.ui.Select) or not select.values:
            await interaction.response.send_message("Сервер не выбран.", ephemeral=True)
            return

        server = select.values[0]
        member = interaction.user if isinstance(interaction.user, discord.Member) else None
        if not has_application_control_access(member, server, interaction.guild.id):
            await interaction.response.send_message("Недостаточно прав.", ephemeral=True)
            return

        is_open = self.action == "open"
        set_application_open(server, interaction.guild.id, is_open)
        await create_or_update_main_panel(interaction.guild, force_recreate=False)
        await announce_application_state_change(interaction.guild, server, is_open)

        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content=(
                f'Подача заявок на сервер "{get_server_plain_label(server)}" '
                + ("открыта." if is_open else "закрыта.")
            ),
            view=self,
        )


async def clone_role_with_overwrites(
    guild: discord.Guild,
    source_role: discord.Role,
    new_name: str,
    reason: str,
) -> tuple[discord.Role, int]:
    created_role = await guild.create_role(
        name=new_name,
        permissions=source_role.permissions,
        colour=source_role.colour,
        hoist=source_role.hoist,
        mentionable=source_role.mentionable,
        reason=reason,
    )

    try:
        bot_member = guild.me or await guild.fetch_member(bot.user.id if bot.user else 0)
    except Exception:
        bot_member = guild.me

    if bot_member is not None:
        try:
            target_position = min(source_role.position, max(bot_member.top_role.position - 1, 1))
            if target_position > 0:
                await created_role.edit(position=target_position, reason=reason)
        except Exception:
            pass

    copied_overwrites = 0
    for channel in guild.channels:
        overwrite = channel.overwrites_for(source_role)
        if overwrite.is_empty():
            continue
        try:
            await channel.set_permissions(created_role, overwrite=overwrite, reason=reason)
            copied_overwrites += 1
        except Exception:
            continue

    return created_role, copied_overwrites


@bot.command(name="say")
@commands.has_permissions(manage_messages=True)
async def say_command(ctx: commands.Context, *, content: str) -> None:
    if not content.strip():
        await ctx.reply("Укажите сообщение для отправки.", mention_author=False, delete_after=5)
        return

    try:
        await delete_message_safely(ctx.message)
    except Exception:
        pass

    for chunk in split_long_message(content):
        await ctx.send(chunk)


@bot.command(name="clsapp")
async def close_application_command(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.reply("Команда доступна только на сервере.", mention_author=False, delete_after=5)
        return
    member = ctx.author if isinstance(ctx.author, discord.Member) else None
    if not has_application_control_access(member, guild_id=ctx.guild.id):
        await ctx.reply("Недостаточно прав для управления заявками.", mention_author=False, delete_after=5)
        return

    options = get_manageable_application_options(ctx.guild.id)
    if not options:
        await ctx.reply("Для этого сервера нет доступных направлений заявок.", mention_author=False, delete_after=5)
        return

    await ctx.send("Выберите сервер, для которого нужно закрыть подачу заявок.", view=ApplicationToggleView(ctx.guild.id, "close", ctx.author.id))


@bot.command(name="opnapp")
async def open_application_command(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.reply("Команда доступна только на сервере.", mention_author=False, delete_after=5)
        return
    member = ctx.author if isinstance(ctx.author, discord.Member) else None
    if not has_application_control_access(member, guild_id=ctx.guild.id):
        await ctx.reply("Недостаточно прав для управления заявками.", mention_author=False, delete_after=5)
        return

    options = get_manageable_application_options(ctx.guild.id)
    if not options:
        await ctx.reply("Для этого сервера нет доступных направлений заявок.", mention_author=False, delete_after=5)
        return

    await ctx.send("Выберите сервер, для которого нужно открыть подачу заявок.", view=ApplicationToggleView(ctx.guild.id, "open", ctx.author.id))


@bot.command(name="staffpanels")
async def staff_panels_command(ctx: commands.Context) -> None:
    if ctx.guild is None or ctx.guild.id != FAMQ_GUILD_ID:
        await ctx.reply("Команда доступна только на основном сервере ASIXEZ.", mention_author=False, delete_after=5)
        return
    member = ctx.author if isinstance(ctx.author, discord.Member) else None
    if not has_application_control_access(member, guild_id=ctx.guild.id) and not ctx.author.guild_permissions.manage_guild:
        await ctx.reply("Недостаточно прав для обновления панелей состава.", mention_author=False, delete_after=5)
        return

    notice = await ctx.reply("Обновляю панель состава и отчёт по никам...", mention_author=False)
    issues = await publish_staff_and_nickname_panels(ctx.guild)
    if issues:
        await notice.edit(content="Не всё получилось:\n" + "\n".join(f"• {issue}" for issue in issues))
        return
    await notice.edit(content="Готово: панель состава и отчёт по никам обновлены.")


@bot.command(name="roleclone")
@commands.has_permissions(manage_roles=True, manage_channels=True)
async def roleclone_command(ctx: commands.Context, source_role: discord.Role, *, new_name: str) -> None:
    if ctx.guild is None:
        await ctx.reply("Команда доступна только на сервере.", mention_author=False, delete_after=5)
        return

    bot_member = ctx.guild.me
    if bot_member is None:
        try:
            bot_member = await ctx.guild.fetch_member(bot.user.id if bot.user else 0)
        except Exception:
            bot_member = None

    if bot_member is None:
        await ctx.reply("Не удалось определить бота на сервере.", mention_author=False, delete_after=5)
        return

    if source_role >= bot_member.top_role:
        await ctx.reply("Я не могу клонировать роль, которая выше или равна моей верхней роли.", mention_author=False, delete_after=5)
        return

    try:
        await delete_message_safely(ctx.message)
    except Exception:
        pass

    status_message = await ctx.send(f"Клонирую роль **{discord.utils.escape_markdown(source_role.name)}**...")
    try:
        created_role, copied_overwrites = await clone_role_with_overwrites(
            ctx.guild,
            source_role,
            new_name.strip(),
            reason=f"Role cloned by {ctx.author}",
        )
    except Exception:
        await status_message.edit(content="Не удалось клонировать роль. Проверь мои права `Manage Roles` и `Manage Channels`.")
        return

    await status_message.edit(
        content=(
            f"Роль успешно клонирована: {created_role.mention}\n"
            f"Источник: **{discord.utils.escape_markdown(source_role.name)}**\n"
            f"Перенесено channel overwrites: **{copied_overwrites}**"
        )
    )


@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear_command(ctx: commands.Context, amount: int) -> None:
    if amount <= 0:
        await ctx.reply("Укажите число больше 0.", mention_author=False, delete_after=5)
        return

    amount = min(amount, 100)
    if not isinstance(ctx.channel, discord.TextChannel):
        await ctx.reply("Команда доступна только в текстовом канале.", mention_author=False, delete_after=5)
        return

    try:
        deleted = await ctx.channel.purge(limit=amount + 1)
        confirmation = await ctx.send(f"Удалено сообщений: {max(len(deleted) - 1, 0)}")
        await confirmation.delete(delay=5)
    except Exception:
        await ctx.reply("Не удалось удалить сообщения. Проверь права бота.", mention_author=False, delete_after=5)


@bot.command(name="usi")
async def usi_command(ctx: commands.Context, user_id: str) -> None:
    if ctx.guild is None:
        await ctx.reply("Команда доступна только на сервере.", mention_author=False, delete_after=5)
        return

    member = ctx.author if isinstance(ctx.author, discord.Member) else None
    if not has_usi_access(member):
        await ctx.reply("Недостаточно прав для выполнения команды.", mention_author=False, delete_after=5)
        return

    cleaned_user_id = re.sub(r"[^\d]", "", user_id)
    if not cleaned_user_id:
        await ctx.reply("Укажите корректный Discord ID пользователя.", mention_author=False, delete_after=5)
        return

    target_user_id = int(cleaned_user_id)
    target_member = ctx.guild.get_member(target_user_id)
    if target_member is None:
        try:
            target_member = await ctx.guild.fetch_member(target_user_id)
        except Exception:
            target_member = None

    try:
        target_user = await bot.fetch_user(target_user_id)
    except Exception:
        if target_member is None:
            await ctx.reply("Не удалось найти пользователя по этому Discord ID.", mention_author=False, delete_after=5)
            return
        target_user = target_member

    reload_member_activity()
    if target_member is not None:
        update_member_activity_profile(target_member)
        save_member_activity()
    record = get_member_activity_record(ctx.guild.id, target_user_id)
    embed = build_usi_embed(ctx.guild, target_member, target_user, record)
    await ctx.send(
        embed=embed,
        view=ApplicationHistoryView(ctx.guild.id, target_user_id, ctx.author.id),
    )


@say_command.error
@clear_command.error
@roleclone_command.error
@usi_command.error
async def moderation_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
    if isinstance(error, commands.MissingPermissions):
        await ctx.reply("Недостаточно прав для выполнения команды.", mention_author=False, delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        if ctx.command and ctx.command.name == "usi":
            await ctx.reply("Использование: `!usi <discord_id>`", mention_author=False, delete_after=5)
        else:
            await ctx.reply("Использование: `!roleclone <роль> <новое имя>`", mention_author=False, delete_after=5)
    elif isinstance(error, commands.BadArgument):
        await ctx.reply("Неверный формат команды.", mention_author=False, delete_after=5)


@bot.tree.command(
    name="giveaway",
    description="Создать розыгрыш. Время указывается в часах, через столько часов бот завершит розыгрыш.",
)
@app_commands.guilds(*GUILD_SCOPES)
@app_commands.default_permissions(manage_messages=True)
async def giveaway_command(interaction: discord.Interaction) -> None:
    if interaction.guild is None or interaction.guild.id != FAMQ_GUILD_ID:
        await interaction.response.send_message("На этом сервере розыгрыши пока не настроены.", ephemeral=True)
        return
    member = interaction.user if isinstance(interaction.user, discord.Member) else None
    if member is None or not member.guild_permissions.manage_messages:
        await interaction.response.send_message("Недостаточно прав для создания розыгрыша.", ephemeral=True)
        return
    await interaction.response.send_modal(GiveawayModal())


async def restore_persistent_views() -> None:
    global views_restored
    if views_restored:
        return

    for guild_id in PROJECT_GUILD_IDS:
        stored = panel_store.get(get_project_panel_key(PANEL_KEY, guild_id), {})
        message_id = stored.get("messageId")
        if message_id:
            bot.add_view(FamqPanelView(guild_id), message_id=int(message_id))
    bot.add_view(VoiceRoomControlView())
    bot.add_view(NicknameSelfFixView())
    reload_applications()
    reload_giveaways()
    reload_voice_rooms()
    reload_member_activity()
    for app in application_store.get("items", {}).values():
        if app.get("status") != "pending":
            continue
        message_id = app.get("applicationMessageId")
        if not message_id:
            continue
        bot.add_view(RecruiterActionView(int(app["id"])), message_id=int(message_id))

    for giveaway in giveaway_store.get("items", {}).values():
        if giveaway.get("status") != "active":
            continue
        message_id = giveaway.get("messageId")
        if message_id:
            bot.add_view(GiveawayJoinView(int(giveaway["id"])), message_id=int(message_id))
        ensure_giveaway_task(int(giveaway["id"]))

    views_restored = True


@bot.event
async def on_voice_state_update(
    member: discord.Member,
    before: discord.VoiceState,
    after: discord.VoiceState,
) -> None:
    project = get_project(member.guild)
    if member.bot or project is None:
        return

    if is_famq_activity_guild(member.guild.id):
        if before.channel != after.channel:
            if before.channel is None and after.channel is not None:
                await send_activity_log(
                    member.guild,
                    title="Голосовая активность",
                    description=f"{VOICE_EMOJI_ADD_SLOT_TEXT} пользователь подключился к голосовому каналу",
                    author_name=f"{member} ({member.id})",
                    author_icon_url=member.display_avatar.url,
                    fields=[
                        ("Пользователь", member.mention, True),
                        ("Канал", format_channel_label(after.channel), True),
                    ],
                    footer_parts=[f"ID пользователя: {member.id}", format_log_time_msk()],
                )
            elif before.channel is not None and after.channel is None:
                actor, _entry = await fetch_optional_audit_executor(member.guild, "member_disconnect", target_id=member.id)
                description = (
                    f"{VOICE_EMOJI_KICK_TEXT} пользователь был исключён из голосового канала"
                    if actor is not None
                    else f"{VOICE_EMOJI_REMOVE_SLOT_TEXT} пользователь покинул голосовой канал"
                )
                fields = [
                    ("Пользователь", member.mention, True),
                    ("Канал", format_channel_label(before.channel), True),
                ]
                if actor is not None:
                    fields.append(("Изменил", actor.mention, True))
                await send_activity_log(
                    member.guild,
                    title="Голосовая активность",
                    description=description,
                    author_name=f"{member} ({member.id})",
                    author_icon_url=member.display_avatar.url,
                    fields=fields,
                    footer_parts=[f"ID пользователя: {member.id}", format_log_time_msk()],
                )
            elif before.channel is not None and after.channel is not None:
                await send_activity_log(
                    member.guild,
                    title="Голосовая активность",
                    description=f"{VOICE_EMOJI_TRANSFER_TEXT} пользователь перешёл в другой голосовой канал",
                    author_name=f"{member} ({member.id})",
                    author_icon_url=member.display_avatar.url,
                    fields=[
                        ("Пользователь", member.mention, True),
                        ("Из", format_channel_label(before.channel), True),
                        ("В", format_channel_label(after.channel), True),
                    ],
                    footer_parts=[f"ID пользователя: {member.id}", format_log_time_msk()],
                )

        if before.self_stream != after.self_stream:
            await send_activity_log(
                member.guild,
                title="Стрим в голосовом канале",
                description=(
                    f"{VOICE_EMOJI_BITRATE_TEXT} пользователь начал стрим"
                    if after.self_stream
                    else f"{VOICE_EMOJI_BITRATE_TEXT} пользователь закончил стрим"
                ),
                author_name=f"{member} ({member.id})",
                author_icon_url=member.display_avatar.url,
                fields=[
                    ("Пользователь", member.mention, True),
                    ("Канал", format_channel_label(after.channel or before.channel), True),
                ],
                footer_parts=[f"ID пользователя: {member.id}", format_log_time_msk()],
            )

        if before.self_video != after.self_video:
            await send_activity_log(
                member.guild,
                title="Камера в голосовом канале",
                description=(
                    f"{VOICE_EMOJI_ACCESS_TEXT} пользователь включил камеру"
                    if after.self_video
                    else f"{VOICE_EMOJI_ACCESS_TEXT} пользователь выключил камеру"
                ),
                author_name=f"{member} ({member.id})",
                author_icon_url=member.display_avatar.url,
                fields=[
                    ("Пользователь", member.mention, True),
                    ("Канал", format_channel_label(after.channel or before.channel), True),
                ],
                footer_parts=[f"ID пользователя: {member.id}", format_log_time_msk()],
            )

    if before.channel is not None and before.channel != after.channel:
        await cleanup_voice_room_if_empty(before.channel)

    if after.channel is None or after.channel.id != int(project["voice_trigger_channel_id"]):
        return

    target_channel = await create_temporary_voice_room(member)
    if target_channel is None:
        return

    try:
        await member.move_to(target_channel, reason="Создание временной голосовой комнаты")
    except Exception:
        pass


@bot.event
async def on_member_join(member: discord.Member) -> None:
    if member.bot or not is_allowed_guild_id(member.guild.id):
        return

    record_member_join_activity(member)
    current = time.time()
    prune_security_caches(current)
    guild_join_cache = join_cache.setdefault(member.guild.id, deque())
    guild_join_cache.append(current)
    prune_deque(guild_join_cache, 10, current)
    join_count = len(guild_join_cache)
    guild_alert_state = join_alert_state.setdefault(member.guild.id, {"warning": 0.0, "alert": 0.0})

    if join_count >= JOIN_THRESHOLD_ALERT:
        if current - guild_alert_state["alert"] >= 10:
            guild_alert_state["alert"] = current
            applied = await apply_timeout_to_member(member, 10 * 60, "Anti-raid join spike")
            await send_security_log(
                member.guild,
                title="🚨 Possible raid detected",
                color=0xE74C3C,
                user_id=member.id,
                action_label="Join Raid",
                count_label=f"{join_count} / 10 sec",
                result_label="Alert sent + newcomer timeout 10 min" if applied else "High risk alert sent, timeout failed",
                extra_lines=[
                    f"👥 Joins: {join_count} / 10 sec",
                    "📊 Status: High Risk",
                    f"🛡️ Auto-timeout: {'applied' if applied else 'failed'}",
                ],
                ping_alert_role=True,
            )

    if join_count >= JOIN_THRESHOLD_WARNING and current - guild_alert_state["warning"] >= 10:
        guild_alert_state["warning"] = current
        await send_security_log(
            member.guild,
            title="⚠️ Possible raid detected",
            color=0xF1C40F,
            user_id=member.id,
            action_label="Join Raid",
            count_label=f"{join_count} / 10 sec",
            result_label="Suspicious activity warning sent",
            extra_lines=[
                f"👥 Joins: {join_count} / 10 sec",
                "📊 Status: Suspicious",
            ],
            ping_alert_role=True,
        )

    if is_famq_activity_guild(member.guild.id):
        await send_activity_log(
            member.guild,
            title="Участник присоединился",
            description=f"{EMOJI_ACCEPT_TEXT} пользователь зашёл на сервер",
            author_name=f"{member} ({member.id})",
            author_icon_url=member.display_avatar.url,
            fields=[
                ("Пользователь", member.mention, True),
                ("Аккаунт создан", format_datetime_msk(member.created_at), True),
            ],
            footer_parts=[f"ID пользователя: {member.id}", format_log_time_msk()],
            thumbnail_url=member.display_avatar.url,
        )

    await send_famq_welcome_message(member)


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member) -> None:
    if after.bot or not is_allowed_guild_id(after.guild.id):
        return
    if is_famq_activity_guild(after.guild.id):
        if before.nick != after.nick:
            actor, _entry = await fetch_optional_audit_executor(after.guild, "member_update", target_id=after.id)
            await send_activity_log(
                after.guild,
                title="Смена никнейма",
                description=f"{VOICE_EMOJI_RENAME_TEXT} пользователь сменил ник на сервере",
                author_name=f"{after} ({after.id})",
                author_icon_url=after.display_avatar.url,
                fields=[
                    ("Пользователь", after.mention, True),
                    ("Старый ник", f"`{before.display_name}`", True),
                    ("Новый ник", f"`{after.display_name}`", True),
                    ("Изменил", actor.mention if actor is not None else "сам пользователь", True),
                ],
                footer_parts=[f"ID пользователя: {after.id}", format_log_time_msk()],
            )

        before_role_ids = {role.id for role in before.roles if role != before.guild.default_role}
        after_role_ids = {role.id for role in after.roles if role != after.guild.default_role}
        if before_role_ids != after_role_ids:
            actor, _entry = await fetch_optional_audit_executor(after.guild, "member_role_update", target_id=after.id)
            added_roles = [role for role in after.roles if role.id not in before_role_ids and role != after.guild.default_role]
            removed_roles = [role for role in before.roles if role.id not in after_role_ids and role != before.guild.default_role]
            if added_roles:
                await send_activity_log(
                    after.guild,
                    title="Выдача ролей",
                    description="└ пользователю была **выдана** роль(и)",
                    author_name=f"{after} ({after.id})",
                    author_icon_url=after.display_avatar.url,
                    fields=[
                        ("Пользователь", after.mention, True),
                        ("Изменил", actor.mention if actor is not None else "неизвестно", True),
                        ("Выданы", format_roles_label(added_roles), False),
                    ],
                    footer_parts=[f"ID пользователя: {after.id}", format_log_time_msk()],
                )
            if removed_roles:
                await send_activity_log(
                    after.guild,
                    title="Снятие ролей",
                    description="└ пользователю была **снята** роль(и)",
                    author_name=f"{after} ({after.id})",
                    author_icon_url=after.display_avatar.url,
                    fields=[
                        ("Пользователь", after.mention, True),
                        ("Изменил", actor.mention if actor is not None else "неизвестно", True),
                        ("Сняты", format_roles_label(removed_roles), False),
                    ],
                    footer_parts=[f"ID пользователя: {after.id}", format_log_time_msk()],
                )

        before_timeout = get_member_timeout_until(before)
        after_timeout = get_member_timeout_until(after)
        if before_timeout != after_timeout:
            actor, _entry = await fetch_optional_audit_executor(after.guild, "member_update", target_id=after.id)
            if after_timeout is not None:
                duration_text = format_datetime_msk(after_timeout)
                description = f"{VOICE_EMOJI_LOCK_TEXT} пользователь был замучен"
            else:
                duration_text = "мут снят"
                description = f"{VOICE_EMOJI_ACCESS_TEXT} пользователю сняли мут"
            await send_activity_log(
                after.guild,
                title="Изменение timeout",
                description=description,
                author_name=f"{after} ({after.id})",
                author_icon_url=after.display_avatar.url,
                fields=[
                    ("Пользователь", after.mention, True),
                    ("Длительность", duration_text, True),
                    ("Изменил", actor.mention if actor is not None else "неизвестно", True),
                ],
                footer_parts=[f"ID пользователя: {after.id}", format_log_time_msk()],
            )

        if safe_asset_url(getattr(before, "guild_avatar", None)) != safe_asset_url(getattr(after, "guild_avatar", None)):
            await send_activity_log(
                after.guild,
                title="Смена серверного аватара",
                description=f"{VOICE_EMOJI_ACCESS_TEXT} пользователь сменил серверный аватар",
                author_name=f"{after} ({after.id})",
                author_icon_url=after.display_avatar.url,
                fields=[("Пользователь", after.mention, True)],
                footer_parts=[f"ID пользователя: {after.id}", format_log_time_msk()],
                thumbnail_url=safe_asset_url(getattr(before, 'guild_avatar', None)) or after.display_avatar.url,
                image_url=safe_asset_url(getattr(after, 'guild_avatar', None)) or after.display_avatar.url,
            )
    update_member_activity_profile(after)
    save_member_activity()


@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel) -> None:
    guild = getattr(channel, "guild", None)
    if guild is None or not is_famq_activity_guild(guild.id):
        return
    actor, _entry = await fetch_optional_audit_executor(guild, "channel_create", target_id=channel.id)
    await send_activity_log(
        guild,
        title="Канал создан",
        description="└ канал был **создан**",
        fields=[
            ("Канал", format_channel_label(channel), True),
            ("Тип канала", f"`{format_channel_type_label(channel)}`", True),
            ("Создал", actor.mention if actor is not None else "неизвестно", True),
        ],
        footer_parts=[f"ID канала: {channel.id}", format_log_time_msk()],
    )


@bot.event
async def on_guild_channel_update(before: discord.abc.GuildChannel, after: discord.abc.GuildChannel) -> None:
    guild = getattr(after, "guild", None)
    if guild is None or not is_famq_activity_guild(guild.id):
        return
    changes = get_channel_update_changes(before, after)
    if not changes:
        return
    actor, _entry = await fetch_optional_audit_executor(guild, "channel_update", target_id=after.id)
    await send_activity_log(
        guild,
        title="Канал обновлён",
        description="└ канал был **изменён** на сервере",
        fields=[
            ("Канал", format_channel_label(after), True),
            ("Тип канала", f"`{format_channel_type_label(after)}`", True),
            ("Изменил", actor.mention if actor is not None else "неизвестно", True),
            ("Изменения", "\n".join(f"• {line}" for line in changes[:12]), False),
        ],
        footer_parts=[f"ID канала: {after.id}", format_log_time_msk()],
    )


@bot.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel) -> None:
    guild = getattr(channel, "guild", None)
    if guild is None or not is_allowed_guild_id(guild.id):
        return
    if is_famq_activity_guild(guild.id):
        actor, _entry = await fetch_optional_audit_executor(guild, "channel_delete", target_id=channel.id)
        await send_activity_log(
            guild,
            title="Канал удалён",
            description="└ канал был **удалён**",
            fields=[
                ("Название", f"`{getattr(channel, 'name', 'неизвестно')}`", True),
                ("Тип канала", f"`{format_channel_type_label(channel)}`", True),
                ("Удалил", actor.mention if actor is not None else "неизвестно", True),
            ],
            footer_parts=[f"ID канала: {channel.id}", format_log_time_msk()],
        )
    await maybe_timeout_admin_actor(guild, "channel_delete", "Channel Delete", target_id=channel.id)


@bot.event
async def on_guild_role_create(role: discord.Role) -> None:
    guild = role.guild
    if not is_famq_activity_guild(guild.id):
        return
    actor, _entry = await fetch_optional_audit_executor(guild, "role_create", target_id=role.id)
    await send_activity_log(
        guild,
        title="Роль создана",
        description="└ на сервере была **создана** роль",
        fields=[
            ("Роль", role.mention, True),
            ("Создал", actor.mention if actor is not None else "неизвестно", True),
            ("Цвет", f"`{role.colour}`", True),
        ],
        footer_parts=[f"ID роли: {role.id}", format_log_time_msk()],
    )


@bot.event
async def on_guild_role_update(before: discord.Role, after: discord.Role) -> None:
    guild = after.guild
    if not is_famq_activity_guild(guild.id):
        return
    changes = get_role_update_changes(before, after)
    if not changes:
        return
    actor, _entry = await fetch_optional_audit_executor(guild, "role_update", target_id=after.id)
    await send_activity_log(
        guild,
        title="Роль обновлена",
        description="└ роль была **изменена**",
        fields=[
            ("Роль", after.mention, True),
            ("Изменил", actor.mention if actor is not None else "неизвестно", True),
            ("Изменения", "\n".join(f"• {line}" for line in changes[:10]), False),
        ],
        footer_parts=[f"ID роли: {after.id}", format_log_time_msk()],
    )


@bot.event
async def on_guild_role_delete(role: discord.Role) -> None:
    guild = role.guild
    if not is_allowed_guild_id(guild.id):
        return
    if is_famq_activity_guild(guild.id):
        actor, _entry = await fetch_optional_audit_executor(guild, "role_delete", target_id=role.id)
        await send_activity_log(
            guild,
            title="Роль удалена",
            description="└ роль была **удалена**",
            fields=[
                ("Роль", f"`{role.name}`", True),
                ("Удалил", actor.mention if actor is not None else "неизвестно", True),
            ],
            footer_parts=[f"ID роли: {role.id}", format_log_time_msk()],
        )
    await maybe_timeout_admin_actor(guild, "role_delete", "Role Delete", target_id=role.id)


@bot.event
async def on_member_remove(member: discord.Member) -> None:
    guild = member.guild
    if not is_allowed_guild_id(guild.id):
        return
    await send_famq_leave_message(member)
    reason, actor_id, audit_reason = await detect_leave_reason(guild, member.id)
    record_member_leave_activity(
        guild.id,
        member.id,
        reason=reason,
        actor_id=actor_id,
        audit_reason=audit_reason,
        role_names=get_member_role_names(member),
        nickname=member.display_name,
        username=member.name,
        global_name=member.global_name or "",
    )
    if is_famq_activity_guild(guild.id) and reason != "ban":
        description = "└ пользователь покинул сервер"
        if reason == "kick":
            description = "└ пользователь был **кикнут** с сервера"
        fields = [("Пользователь", member.mention, True)]
        if actor_id:
            fields.append(("Изменил", f"<@{actor_id}>", True))
        if audit_reason:
            fields.append(("Причина", audit_reason, False))
        await send_activity_log(
            guild,
            title="Выход с сервера",
            description=description,
            author_name=f"{member} ({member.id})",
            author_icon_url=member.display_avatar.url,
            fields=fields,
            footer_parts=[f"ID пользователя: {member.id}", format_log_time_msk()],
        )
    await maybe_restrict_kick_actor(guild, member.id)


@bot.event
async def on_member_ban(guild: discord.Guild, user: discord.User | discord.Member) -> None:
    if not is_allowed_guild_id(guild.id):
        return
    record_member_leave_activity(
        guild.id,
        user.id,
        reason="ban",
        role_names=get_member_role_names(user) if isinstance(user, discord.Member) else None,
        nickname=user.display_name if isinstance(user, discord.Member) else "",
        username=user.name,
        global_name=getattr(user, "global_name", "") or "",
    )
    if is_famq_activity_guild(guild.id):
        actor, entry = await fetch_optional_audit_executor(guild, "ban", target_id=user.id)
        fields = [("Пользователь", f"<@{user.id}>", True)]
        if actor is not None:
            fields.append(("Изменил", actor.mention, True))
        if entry is not None and entry.reason:
            fields.append(("Причина", entry.reason, False))
        await send_activity_log(
            guild,
            title="Бан участника",
            description="└ пользователь был **забанен**",
            author_name=f"{user} ({user.id})",
            author_icon_url=getattr(user.display_avatar, "url", None),
            fields=fields,
            footer_parts=[f"ID пользователя: {user.id}", format_log_time_msk()],
        )
    await maybe_timeout_admin_actor(guild, "ban", "Member Ban", target_id=user.id)


@bot.event
async def on_thread_create(thread: discord.Thread) -> None:
    if not is_famq_activity_guild(thread.guild.id):
        return
    actor, _entry = await fetch_optional_audit_executor(thread.guild, "thread_create", target_id=thread.id)
    creator = actor.mention if actor is not None else (f"<@{thread.owner_id}>" if thread.owner_id else "неизвестно")
    await send_activity_log(
        thread.guild,
        title="Ветка создана",
        description="└ ветка была **создана**",
        fields=[
            ("Ветка", thread.mention if thread.mention else f"`{thread.name}`", True),
            ("Родительский канал", format_thread_parent_label(thread), True),
            ("Создал", creator, True),
        ],
        footer_parts=[f"ID ветки: {thread.id}", format_log_time_msk()],
    )


@bot.event
async def on_thread_update(before: discord.Thread, after: discord.Thread) -> None:
    if not is_famq_activity_guild(after.guild.id):
        return
    actor, _entry = await fetch_optional_audit_executor(after.guild, "thread_update", target_id=after.id)
    if before.archived != after.archived:
        await send_activity_log(
            after.guild,
            title="Архивация ветки",
            description=(
                "└ ветка была **архивирована**"
                if after.archived
                else "└ ветка была **разархивирована**"
            ),
            fields=[
                ("Ветка", after.mention if after.mention else f"`{after.name}`", True),
                ("Родительский канал", format_thread_parent_label(after), True),
                ("Изменил", actor.mention if actor is not None else "неизвестно", True),
            ],
            footer_parts=[f"ID ветки: {after.id}", format_log_time_msk()],
        )
        return

    changes: list[str] = []
    if before.name != after.name:
        changes.append(f"Имя: `{before.name}` → `{after.name}`")
    if before.locked != after.locked:
        changes.append(f"Locked: `{before.locked}` → `{after.locked}`")
    if before.slowmode_delay != after.slowmode_delay:
        changes.append(f"Слоумод: `{before.slowmode_delay}` → `{after.slowmode_delay}`")
    if not changes:
        return
    await send_activity_log(
        after.guild,
        title="Ветка обновлена",
        description="└ ветка была **изменена**",
        fields=[
            ("Ветка", after.mention if after.mention else f"`{after.name}`", True),
            ("Родительский канал", format_thread_parent_label(after), True),
            ("Изменил", actor.mention if actor is not None else "неизвестно", True),
            ("Изменения", "\n".join(f"• {line}" for line in changes), False),
        ],
        footer_parts=[f"ID ветки: {after.id}", format_log_time_msk()],
    )


@bot.event
async def on_thread_delete(thread: discord.Thread) -> None:
    if not is_famq_activity_guild(thread.guild.id):
        return
    actor, _entry = await fetch_optional_audit_executor(thread.guild, "thread_delete", target_id=thread.id)
    await send_activity_log(
        thread.guild,
        title="Ветка удалена",
        description="└ ветка была **удалена**",
        fields=[
            ("Ветка", f"`{thread.name}`", True),
            ("Родительский канал", format_thread_parent_label(thread), True),
            ("Удалил", actor.mention if actor is not None else "неизвестно", True),
        ],
        footer_parts=[f"ID ветки: {thread.id}", format_log_time_msk()],
    )


@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message) -> None:
    if before.author.bot or before.guild is None or not is_famq_activity_guild(before.guild.id):
        return
    if before.content == after.content:
        return
    await send_activity_log(
        before.guild,
        title="Сообщение изменено",
        description="└ сообщение было **изменено**",
        author_name=f"{before.author} ({before.author.id})",
        author_icon_url=before.author.display_avatar.url,
        fields=[
            ("Автор", before.author.mention, True),
            ("Канал", format_channel_label(before.channel), True),
            ("До изменения", format_text_block(before.content, fallback="Нет текста"), False),
            ("После изменения", format_text_block(after.content, fallback="Нет текста"), False),
        ],
        footer_parts=[
            f"ID пользователя: {before.author.id}",
            f"ID сообщения: {before.id}",
            format_log_time_msk(),
        ],
    )


@bot.event
async def on_message_delete(message: discord.Message) -> None:
    if message.author.bot or message.guild is None or not is_famq_activity_guild(message.guild.id):
        return
    await send_activity_log(
        message.guild,
        title="Сообщение удалено",
        description="└ сообщение было **удалено**",
        author_name=f"{message.author} ({message.author.id})",
        author_icon_url=message.author.display_avatar.url,
        fields=[
            ("Автор", message.author.mention, True),
            ("Канал", format_channel_label(message.channel), True),
            ("Содержимое удалённого сообщения", format_text_block(message.content, fallback="Нет текста"), False),
        ],
        footer_parts=[
            f"ID пользователя: {message.author.id}",
            f"ID сообщения: {message.id}",
            format_log_time_msk(),
        ],
    )


@bot.event
async def on_bulk_message_delete(messages: list[discord.Message]) -> None:
    if not messages:
        return
    sample = messages[0]
    if sample.guild is None or not is_famq_activity_guild(sample.guild.id):
        return
    actor, _entry = await fetch_optional_audit_executor(sample.guild, "message_bulk_delete", target_id=sample.channel.id)
    await send_activity_log(
        sample.guild,
        title="Массовое удаление сообщений",
        description="└ произошло **массовое удаление** сообщений",
        fields=[
            ("Канал", format_channel_label(sample.channel), True),
            ("Количество", f"`{len(messages)}`", True),
            ("Удалил", actor.mention if actor is not None else "неизвестно", True),
        ],
        footer_parts=[format_log_time_msk()],
    )


@bot.event
async def on_guild_channel_pins_update(channel: discord.abc.GuildChannel, last_pin: datetime | None) -> None:
    guild = getattr(channel, "guild", None)
    if guild is None or not is_famq_activity_guild(guild.id):
        return
    await send_activity_log(
        guild,
        title="Обновлены закрепы",
        description="└ закреплённые сообщения в канале были **обновлены**",
        fields=[
            ("Канал", format_channel_label(channel), True),
            ("Последний закреп", format_datetime_msk(last_pin), True),
        ],
        footer_parts=[format_log_time_msk()],
    )


@bot.event
async def on_user_update(before: discord.User, after: discord.User) -> None:
    for guild in bot.guilds:
        if not is_famq_activity_guild(guild.id):
            continue
        member = guild.get_member(after.id)
        if member is None:
            continue

        if safe_asset_url(before.display_avatar) != safe_asset_url(after.display_avatar):
            await send_activity_log(
                guild,
                title="Смена аватара",
                description="└ пользователь сменил **аватар**",
                author_name=f"{after} ({after.id})",
                author_icon_url=after.display_avatar.url,
                fields=[("Пользователь", member.mention, True)],
                footer_parts=[f"ID пользователя: {after.id}", format_log_time_msk()],
                thumbnail_url=safe_asset_url(before.display_avatar),
                image_url=safe_asset_url(after.display_avatar),
            )

        if safe_asset_url(before.banner) != safe_asset_url(after.banner):
            await send_activity_log(
                guild,
                title="Смена баннера",
                description="└ пользователь сменил **баннер**",
                author_name=f"{after} ({after.id})",
                author_icon_url=after.display_avatar.url,
                fields=[("Пользователь", member.mention, True)],
                footer_parts=[f"ID пользователя: {after.id}", format_log_time_msk()],
                thumbnail_url=safe_asset_url(before.banner) or after.display_avatar.url,
                image_url=safe_asset_url(after.banner),
            )
        update_member_activity_profile(member)
    save_member_activity()


@bot.event
async def on_guild_update(before: discord.Guild, after: discord.Guild) -> None:
    if not is_famq_activity_guild(after.id):
        return
    changes = get_guild_update_changes(before, after)
    if not changes:
        return
    actor, _entry = await fetch_optional_audit_executor(after, "guild_update", target_id=after.id)
    await send_activity_log(
        after,
        title="Настройки сервера обновлены",
        description="└ настройки сервера были **изменены**",
        fields=[
            ("Сервер", f"`{after.name}`", True),
            ("Изменил", actor.mention if actor is not None else "неизвестно", True),
            ("Изменения", "\n".join(f"• {line}" for line in changes[:12]), False),
        ],
        footer_parts=[f"ID сервера: {after.id}", format_log_time_msk()],
        thumbnail_url=safe_asset_url(before.icon) or safe_asset_url(after.icon),
        image_url=safe_asset_url(after.banner) or safe_asset_url(after.icon),
    )


@bot.event
async def on_message(message: discord.Message) -> None:
    current = time.time()
    prune_security_caches(current)

    if message.author.bot:
        await bot.process_commands(message)
        return

    if not isinstance(message.author, discord.Member) or message.guild is None:
        await bot.process_commands(message)
        return

    if not is_allowed_guild_id(message.guild.id):
        if message.content.startswith(str(bot.command_prefix)):
            await message.channel.send(
                f"Этот сервер отсутствует в whitelist бота. Чтобы получить доступ, свяжитесь с: `{WHITELIST_CONTACT_ID}`"
            )
        await bot.process_commands(message)
        return

    if is_protected_target(message.guild, message.author.id):
        await bot.process_commands(message)
        return

    count = register_user_message(message.guild.id, message.author.id, current)
    if count >= SPAM_LIMIT:
        cache_key = (message.guild.id, message.author.id)
        last_triggered_at = spam_action_cache.get(cache_key, 0.0)
        if current - last_triggered_at < 5:
            return
        spam_action_cache[cache_key] = current

        purged_count = 0
        try:
            deleted_messages = await message.channel.purge(
                limit=10,
                check=lambda item: (
                    item.author.id == message.author.id
                    and current - item.created_at.replace(tzinfo=timezone.utc).timestamp() <= 5
                ),
            )
            purged_count = len(deleted_messages)
        except Exception:
            await delete_message_safely(message)
            purged_count = 1

        applied = await apply_timeout_to_member(message.author, 60, "Anti-spam trigger")
        await send_security_log(
            message.guild,
            title="💬 Anti-Spam Triggered",
            color=0xE74C3C,
            user_id=message.author.id,
            action_label="Message Spam",
            count_label=f"{count} / 5 sec",
            result_label=(
                f"Purged {purged_count} messages + timeout 60 sec"
                if applied
                else f"Purged {purged_count} messages, timeout could not be applied"
            ),
            source_message_id=message.id,
            ping_alert_role=False,
        )
        return

    await bot.process_commands(message)


@bot.event
async def on_guild_join(guild: discord.Guild) -> None:
    if is_allowed_guild_id(guild.id):
        return
    await notify_unwhitelisted_guild(guild)


@bot.event
async def on_ready() -> None:
    global startup_done, restart_task, command_sync_done
    ensure_restart_task()
    await restore_persistent_views()

    if startup_done:
        console_log(f"Reconnected as {bot.user}")
        return

    apply_default_closed_application_servers()

    if not command_sync_done:
        total_synced = 0
        for guild_scope in GUILD_SCOPES:
            synced = await bot.tree.sync(guild=guild_scope)
            total_synced += len(synced)
        console_log(f"Slash commands synced: {total_synced}")
        command_sync_done = True

    for guild in list(bot.guilds):
        if not is_allowed_guild_id(guild.id):
            await notify_unwhitelisted_guild(guild)

    for guild_id in PROJECT_GUILD_IDS:
        guild = bot.get_guild(guild_id)
        if guild is None:
            try:
                guild = await bot.fetch_guild(guild_id)
            except Exception:
                console_log(f"Project setup skipped: guild {guild_id} not found.")
                continue

        if guild.id == FAMQ_GUILD_ID:
            asyncio.create_task(publish_staff_and_nickname_panels_later(guild))

        created_main = await create_or_update_main_panel(guild, force_recreate=True)
        created_info = await create_or_update_info_panel(guild, force_recreate=False)
        created_contracts = await create_or_update_contracts_panel(guild, force_recreate=False)
        created_fleet = await create_or_update_fleet_panel(guild, force_recreate=False)
        created_voice = await create_or_update_voice_panel(guild, force_recreate=True)
        setup_issues: list[str] = []
        await cleanup_stale_voice_rooms(guild)
        cleaned_resolved = await cleanup_resolved_application_channels(guild)
        refreshed_applications = await refresh_pending_application_messages(guild)
        await send_restart_status(guild, setup_issues)

        project = get_project(guild)
        project_name = project.get("project_name", str(guild.id)) if project else str(guild.id)
        console_log(f"{project_name} main panel " + ("created" if created_main else "updated"))
        console_log(f"{project_name} info panel " + ("created" if created_info else "updated"))
        console_log(f"{project_name} contracts panel " + ("created" if created_contracts else "updated"))
        console_log(f"{project_name} fleet panel " + ("created" if created_fleet else "updated"))
        console_log(f"{project_name} voice panel " + ("created" if created_voice else "updated"))
        console_log(f"{project_name} resolved application channels cleaned: {cleaned_resolved}")
        console_log(f"{project_name} pending applications refreshed: {refreshed_applications}")

    console_log(f"Logged in as {bot.user}")

    startup_done = True


def main() -> None:
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN or FAMQ_BOT_TOKEN is missing in famq-bot/.env")

    # Добавляем статус
    @bot.event
    async def on_ready():
        await bot.change_presence(
            status=discord.Status.online,
            activity=discord.Game(name="Работает благодаря Diamond!")
        )
        print(f"✅ Бот {bot.user} запущен!")

    bot.run(TOKEN)


if __name__ == "__main__":
    main()

