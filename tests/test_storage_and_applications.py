import asyncio
import tempfile
import unittest
from pathlib import Path

from applications import (
    build_asx_member_nickname,
    extract_nickname_and_static,
    sanitize_channel_name_component,
)
from storage import BotStorage


class ApplicationLogicTests(unittest.TestCase):
    def test_nickname_uses_irl_name_and_static_id(self) -> None:
        nickname = build_asx_member_nickname({"irlName": "Александр Иванов", "nameStatic": "Player 7654321"})
        self.assertEqual(nickname, "ASX | Александр Иванов | 7654321")

    def test_legacy_nickname_parser(self) -> None:
        self.assertEqual(extract_nickname_and_static("John Doe | 12345"), ("John", "12345"))

    def test_channel_name_is_safe_and_limited(self) -> None:
        self.assertEqual(sanitize_channel_name_component("  Name / Test!  "), "name-test")


class StorageTests(unittest.IsolatedAsyncioTestCase):
    async def test_store_is_reloaded_without_replacing_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            directory = Path(raw_directory)
            storage = BotStorage(
                applications_file=directory / "applications.json",
                panels_file=directory / "panels.json",
                giveaways_file=directory / "giveaways.json",
                voice_rooms_file=directory / "voice.json",
                member_activity_file=directory / "activity.json",
                legacy_applications_file=directory / "legacy.json",
            )
            applications = storage.applications
            applications["items"]["1"] = {"status": "pending"}
            applications.save()
            applications.reload()

            self.assertIs(applications, storage.applications)
            self.assertEqual(applications["items"]["1"]["status"], "pending")

    async def test_nearby_saves_are_coalesced_and_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            directory = Path(raw_directory)
            storage = BotStorage(
                applications_file=directory / "applications.json",
                panels_file=directory / "panels.json",
                giveaways_file=directory / "giveaways.json",
                voice_rooms_file=directory / "voice.json",
                member_activity_file=directory / "activity.json",
                legacy_applications_file=directory / "legacy.json",
            )
            storage.applications["items"]["2"] = {"status": "accepted"}
            storage.schedule_save("applications", delay_seconds=0.01)
            storage.schedule_save("applications", delay_seconds=0.01)
            await asyncio.sleep(0.03)

            reloaded = BotStorage(
                applications_file=directory / "applications.json",
                panels_file=directory / "panels.json",
                giveaways_file=directory / "giveaways.json",
                voice_rooms_file=directory / "voice.json",
                member_activity_file=directory / "activity.json",
                legacy_applications_file=directory / "legacy.json",
            )
            self.assertEqual(reloaded.applications["items"]["2"]["status"], "accepted")


if __name__ == "__main__":
    unittest.main()
