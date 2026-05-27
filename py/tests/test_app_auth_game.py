import sys
import time
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

    def register_user(self, username: str) -> str:
        captcha = self.client.get("/api/v1/captchaImage")
        self.assertEqual(200, captcha.status_code)
        payload = captcha.json()["data"]
        response = self.client.post(
            "/api/v1/register",
            json={
                "username": username,
                "password": "123456",
                "confirmPassword": "123456",
                "code": "TEST",
                "uuid": payload["uuid"],
                "userType": "sys_user",
            },
        )
        self.assertEqual(200, response.status_code)
        return response.json()["data"]["token"]

    def test_auth_flow(self):
        suffix = str(int(time.time() * 1000))
        token = self.register_user(f"auth_{suffix}")
        response = self.client.get("/api/v1/getInfo", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(200, response.status_code)
        self.assertEqual(f"auth_{suffix}", response.json()["data"]["user"]["username"])

        logout = self.client.post("/api/v1/logout", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(200, logout.status_code)

        after_logout = self.client.get("/api/v1/getInfo", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(401, after_logout.status_code)

    def test_admin_user_management(self):
        suffix = str(int(time.time() * 1000))
        user_token = self.register_user(f"managed_{suffix}")
        admin_token = self.login_admin()
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        user_headers = {"Authorization": f"Bearer {user_token}"}

        forbidden = self.client.get("/api/v1/admin/users", headers=user_headers)
        self.assertEqual(403, forbidden.status_code)

        users = self.client.get("/api/v1/admin/users", headers=admin_headers)
        self.assertEqual(200, users.status_code)
        managed_user = next(
            item for item in users.json()["data"]
            if item["username"] == f"managed_{suffix}"
        )

        reset = self.client.put(
            f"/api/v1/admin/users/{managed_user['user_id']}/password",
            headers=admin_headers,
            json={"newPassword": "654321", "confirmPassword": "654321"},
        )
        self.assertEqual(200, reset.status_code)

        old_session = self.client.get("/api/v1/getInfo", headers=user_headers)
        self.assertEqual(401, old_session.status_code)

        captcha = self.client.get("/api/v1/captchaImage").json()["data"]
        login = self.client.post(
            "/api/v1/login",
            json={
                "username": f"managed_{suffix}",
                "password": "654321",
                "code": "TEST",
                "uuid": captcha["uuid"],
            },
        )
        self.assertEqual(200, login.status_code)

        update = self.client.put(
            f"/api/v1/admin/users/{managed_user['user_id']}",
            headers=admin_headers,
            json={"status": "disabled", "roles": ["user"], "permissions": []},
        )
        self.assertEqual(200, update.status_code)
        self.assertEqual("disabled", update.json()["data"]["status"])

        disabled_login = self.client.post(
            "/api/v1/login",
            json={
                "username": f"managed_{suffix}",
                "password": "654321",
                "code": "TEST",
                "uuid": captcha["uuid"],
            },
        )
        self.assertEqual(401, disabled_login.status_code)

    def test_game_room_lifecycle(self):
        suffix = str(int(time.time() * 1000))
        token = self.register_user(f"room_{suffix}")
        headers = {"Authorization": f"Bearer {token}"}

        create_room = self.client.post("/api/v1/game/create-room", headers=headers)
        self.assertEqual(200, create_room.status_code)
        room_id = create_room.json()["data"]

        get_room = self.client.get(f"/api/v1/game/room/{room_id}", headers=headers)
        self.assertEqual(200, get_room.status_code)
        self.assertEqual(room_id, get_room.json()["data"]["room_id"])

        leave_room = self.client.post("/api/v1/game/leave-room", headers=headers)
        self.assertEqual(200, leave_room.status_code)

    def test_gomoku_room_match_flow(self):
        suffix = str(int(time.time() * 1000))
        host_token = self.register_user(f"host_{suffix}")
        guest_token = self.register_user(f"guest_{suffix}")
        host_headers = {"Authorization": f"Bearer {host_token}"}
        guest_headers = {"Authorization": f"Bearer {guest_token}"}

        create_room = self.client.post("/api/v1/game/create-room", headers=host_headers)
        self.assertEqual(200, create_room.status_code)
        room_id = create_room.json()["data"]

        join_room = self.client.post(
            "/api/v1/game/join-room",
            headers=guest_headers,
            json={"room_id": room_id},
        )
        self.assertEqual(200, join_room.status_code)

        room = self.client.get(f"/api/v1/game/room/{room_id}", headers=host_headers)
        self.assertEqual(200, room.status_code)
        room_data = room.json()["data"]
        self.assertEqual("black", room_data["host"]["color"])
        self.assertEqual("white", room_data["guest"]["color"])
        self.assertIn(room_data["game_state"]["status"], ["ready", "playing"])

        start = self.client.post(f"/api/v1/game/start-game?room_id={room_id}", headers=host_headers)
        self.assertEqual(200, start.status_code)

        host_move = self.client.post(
            "/api/v1/game/make-move",
            headers=host_headers,
            json={"room_id": room_id, "x": 7, "y": 7},
        )
        self.assertEqual(200, host_move.status_code)

        guest_move = self.client.post(
            "/api/v1/game/make-move",
            headers=guest_headers,
            json={"room_id": room_id, "x": 8, "y": 7},
        )
        self.assertEqual(200, guest_move.status_code)

        room_after_moves = self.client.get(f"/api/v1/game/room/{room_id}", headers=host_headers)
        self.assertEqual(200, room_after_moves.status_code)
        board = room_after_moves.json()["data"]["game_state"]["board"]
        self.assertEqual(1, board[7][7])
        self.assertEqual(2, board[7][8])


if __name__ == "__main__":
    unittest.main()
