import base64
import json
import tempfile
import unittest
from pathlib import Path

from auth import username_from_verified_token
from database import get_all_reports, get_reports_for_username, initialize_database


def fake_verified_header(username: str) -> str:
    payload = base64.urlsafe_b64encode(
        json.dumps({"preferred_username": username}).encode()
    ).decode().rstrip("=")
    return f"Bearer header.{payload}.signature"


class AccessControlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        initialize_database(self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_vulnerable_query_crosses_user_boundary(self) -> None:
        reports = get_all_reports(self.db_path)
        self.assertEqual({report["owner"] for report in reports}, {"alice", "bob"})

    def test_fixed_query_returns_only_token_owner(self) -> None:
        username = username_from_verified_token(fake_verified_header("alice"))
        reports = get_reports_for_username(username, self.db_path)
        self.assertEqual(len(reports), 2)
        self.assertEqual({report["owner"] for report in reports}, {"alice"})

    def test_unknown_authenticated_user_gets_no_rows(self) -> None:
        reports = get_reports_for_username("mallory", self.db_path)
        self.assertEqual(reports, [])


if __name__ == "__main__":
    unittest.main()
