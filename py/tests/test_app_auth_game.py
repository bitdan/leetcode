import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from api.main import app


class AuthAndGameApiTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def login_admin(self) -> str:
        captcha = self.client.get("/api/v1/captchaImage")
        self.assertEqual(200, captcha.status_code)
        payload = captcha.json()["data"]
        response = self.client.post(
            "/api/v1/login",
            json={
                "username": "admin",
                "password": "123456",
                "code": "TEST",
                "uuid": payload["uuid"],
            },
        )
        self.assertEqual(200, response.status_code)
        return response.json()["data"]["token"]

    def test_auth_flow(self):
        token = self.login_admin()
        response = self.client.get("/api/v1/getInfo", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(200, response.status_code)
        self.assertEqual("admin", response.json()["data"]["user"]["username"])

        logout = self.client.post("/api/v1/logout", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(200, logout.status_code)

        after_logout = self.client.get("/api/v1/getInfo", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(401, after_logout.status_code)

    def test_game_room_lifecycle(self):
        token = self.login_admin()
        headers = {"Authorization": f"Bearer {token}"}

        create_room = self.client.post("/api/v1/game/create-room", headers=headers)
        self.assertEqual(200, create_room.status_code)
        room_id = create_room.json()["data"]

        get_room = self.client.get(f"/api/v1/game/room/{room_id}", headers=headers)
        self.assertEqual(200, get_room.status_code)
        self.assertEqual(room_id, get_room.json()["data"]["room_id"])

        leave_room = self.client.post("/api/v1/game/leave-room", headers=headers)
        self.assertEqual(200, leave_room.status_code)


if __name__ == "__main__":
    unittest.main()
