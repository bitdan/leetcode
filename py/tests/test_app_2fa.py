import base64
import os
import sys
import unittest
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from fastapi.testclient import TestClient

from app import create_app
from core.settings import get_settings
from auth.totp_service import TotpService
from auth.totp_store import MemoryTotpStore


class TotpServiceTest(unittest.TestCase):
    def test_rfc6238_sha1_vector(self):
        service = TotpService(MemoryTotpStore(), issuer_name="Test")
        account = service.create_account(
            "user-a",
            {
                "issuer": "RFC",
                "accountName": "demo@example.com",
                "secret": "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ",
                "digits": 8,
                "period": 30,
                "algorithm": "SHA1",
            },
        )

        code, remaining = service._generate_code(account, 59)
        self.assertEqual("94287082", code)
        self.assertEqual(1, remaining)

    def test_google_migration_uri(self):
        service = TotpService(MemoryTotpStore(), issuer_name="Test")
        migration_uri = build_google_migration_uri(
            secret=b"Hello!\xde\xad\xbe\xef",
            name="demo@gmail.com",
            issuer="Google",
        )
        imported = service.import_accounts("user-a", {"text": migration_uri, "mergeMode": "append"})
        self.assertEqual(1, imported["imported"])
        item = imported["items"][0]
        self.assertEqual("Google", item["issuer"])
        self.assertEqual("demo@gmail.com", item["accountName"])
        self.assertEqual("SHA1", item["algorithm"])
        self.assertEqual(6, item["digits"])


class TwoFactorApiTest(unittest.TestCase):
    def setUp(self):
        os.environ["USE_REDIS_SESSIONS"] = "false"
        get_settings.cache_clear()
        app = create_app()
        self.client = TestClient(app)
        self.token = self._login()
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def _login(self) -> str:
        captcha = self.client.get("/api/v1/captchaImage")
        self.assertEqual(200, captcha.status_code)
        uuid_value = captcha.json()["data"]["uuid"]
        response = self.client.post(
            "/api/v1/login",
            json={"username": "admin", "password": "123456", "code": "TEST", "uuid": uuid_value},
        )
        self.assertEqual(200, response.status_code)
        return response.json()["data"]["token"]

    def test_two_factor_crud_and_export(self):
        create_resp = self.client.post(
            "/api/v1/2fa/accounts",
            json={
                "issuer": "GitHub",
                "accountName": "admin@example.com",
                "secret": "JBSWY3DPEHPK3PXP",
                "digits": 6,
                "period": 30,
                "algorithm": "SHA1",
            },
            headers=self.headers,
        )
        self.assertEqual(200, create_resp.status_code)
        account_id = create_resp.json()["data"]["id"]

        list_resp = self.client.get("/api/v1/2fa/accounts", headers=self.headers)
        self.assertEqual(200, list_resp.status_code)
        accounts = list_resp.json()["data"]
        self.assertEqual(1, len(accounts))
        self.assertEqual("GitHub", accounts[0]["issuer"])
        self.assertEqual(6, len(accounts[0]["code"]))
        self.assertNotIn("secret", accounts[0])

        detail_resp = self.client.get(f"/api/v1/2fa/accounts/{account_id}", headers=self.headers)
        self.assertEqual(200, detail_resp.status_code)
        self.assertEqual("JBSWY3DPEHPK3PXP", detail_resp.json()["data"]["secret"])

        import_resp = self.client.post(
            "/api/v1/2fa/accounts/import",
            json={
                "text": "otpauth://totp/Google:demo@example.com?secret=JBSWY3DPEHPK3PXA&issuer=Google&algorithm=SHA1&digits=6&period=30",
                "mergeMode": "append",
            },
            headers=self.headers,
        )
        self.assertEqual(200, import_resp.status_code)
        self.assertEqual(2, import_resp.json()["data"]["total"])

        export_resp = self.client.get("/api/v1/2fa/accounts/export?exportFormat=otpauth", headers=self.headers)
        self.assertEqual(200, export_resp.status_code)
        self.assertIn("otpauth://totp/", export_resp.json()["data"]["content"])

        delete_resp = self.client.delete(f"/api/v1/2fa/accounts/{account_id}", headers=self.headers)
        self.assertEqual(200, delete_resp.status_code)

    def test_profile_update_and_change_password(self):
        update_resp = self.client.put(
            "/api/v1/profile",
            json={"email": "updated@example.com", "avatar": "https://example.com/avatar.png"},
            headers=self.headers,
        )
        self.assertEqual(200, update_resp.status_code)
        self.assertEqual("updated@example.com", update_resp.json()["data"]["user"]["email"])
        self.assertEqual("https://example.com/avatar.png", update_resp.json()["data"]["user"]["avatar"])

        change_resp = self.client.put(
            "/api/v1/profile/password",
            json={
                "oldPassword": "123456",
                "newPassword": "12345678",
                "confirmPassword": "12345678",
            },
            headers=self.headers,
        )
        self.assertEqual(200, change_resp.status_code)

        captcha = self.client.get("/api/v1/captchaImage")
        uuid_value = captcha.json()["data"]["uuid"]
        old_login = self.client.post(
            "/api/v1/login",
            json={"username": "admin", "password": "123456", "code": "TEST", "uuid": uuid_value},
        )
        self.assertEqual(401, old_login.status_code)

        captcha = self.client.get("/api/v1/captchaImage")
        uuid_value = captcha.json()["data"]["uuid"]
        new_login = self.client.post(
            "/api/v1/login",
            json={"username": "admin", "password": "12345678", "code": "TEST", "uuid": uuid_value},
        )
        self.assertEqual(200, new_login.status_code)


def encode_varint(value: int) -> bytes:
    parts = bytearray()
    while True:
        to_write = value & 0x7F
        value >>= 7
        if value:
            parts.append(to_write | 0x80)
        else:
            parts.append(to_write)
            return bytes(parts)


def encode_length_delimited(field_number: int, value: bytes) -> bytes:
    return encode_varint((field_number << 3) | 2) + encode_varint(len(value)) + value


def encode_varint_field(field_number: int, value: int) -> bytes:
    return encode_varint((field_number << 3) | 0) + encode_varint(value)


def build_google_migration_uri(secret: bytes, name: str, issuer: str) -> str:
    otp_parameters = b"".join(
        [
            encode_length_delimited(1, secret),
            encode_length_delimited(2, name.encode("utf-8")),
            encode_length_delimited(3, issuer.encode("utf-8")),
            encode_varint_field(4, 1),
            encode_varint_field(5, 1),
            encode_varint_field(6, 2),
        ]
    )
    payload = b"".join(
        [
            encode_length_delimited(1, otp_parameters),
            encode_varint_field(2, 1),
            encode_varint_field(3, 1),
            encode_varint_field(4, 0),
            encode_varint_field(5, 1),
        ]
    )
    encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    return f"otpauth-migration://offline?data={encoded}"


if __name__ == "__main__":
    unittest.main()
