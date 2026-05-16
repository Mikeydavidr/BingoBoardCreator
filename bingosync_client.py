import base64
import json
import uuid
from enum import IntFlag
from typing import AsyncIterator, Optional

import httpx
import websockets


class Color(IntFlag):
    BLANK  = 1
    RED    = 2
    BLUE   = 4
    GREEN  = 8
    ORANGE = 16
    PURPLE = 32
    NAVY   = 64
    TEAL   = 128
    PINK   = 256
    BROWN  = 512
    YELLOW = 1024


def _encode_uuid(uid: str) -> str:
    return base64.urlsafe_b64encode(uuid.UUID(uid).bytes).rstrip(b"=").decode()


def _decode_uuid(encoded: str) -> str:
    padding = (4 - len(encoded) % 4) % 4
    return str(uuid.UUID(bytes=base64.urlsafe_b64decode(encoded + "=" * padding)))


def _normalize_room_id(room_id: str) -> str:
    try:
        return _encode_uuid(room_id)
    except (ValueError, AttributeError):
        return room_id


class BingoSyncClient:
    BASE_URL = "https://bingosync.com"
    WS_URL   = "wss://sockets.bingosync.com/broadcast"

    def __init__(self):
        self._client: httpx.AsyncClient = httpx.AsyncClient()
        self._room_id: Optional[str] = None
        self._player_id: Optional[str] = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def close(self):
        await self._client.aclose()

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _require_room(self):
        if not self._room_id:
            raise RuntimeError("No room joined — call join_room or create_room first")

    async def _get(self, path: str) -> httpx.Response:
        response = await self._client.get(self.BASE_URL + path)
        if not response.is_success:
            raise RuntimeError(f"GET {path} failed ({response.status_code}): {response.text}")
        return response

    async def _post(self, path: str, data: dict) -> httpx.Response:
        response = await self._client.post(self.BASE_URL + path, json=data)
        if not response.is_success:
            raise RuntimeError(f"POST {path} failed ({response.status_code}): {response.text}")
        return response

    # ------------------------------------------------------------------ #
    # Room management                                                      #
    # ------------------------------------------------------------------ #

    async def join_room(self, room_id: str, nickname: str, password: str, spectator: bool = False):
        encoded = _normalize_room_id(room_id)
        response = await self._client.post(
            self.BASE_URL + "/api/join-room",
            json={
                "room": encoded,
                "nickname": nickname,
                "password": password,
                "is_specator": spectator,  # intentional typo matching BingoSync source
            }
        )
        if not response.is_success and response.status_code != 302:
            raise RuntimeError(f"POST /api/join-room failed ({response.status_code}): {response.text}")
        self._room_id = encoded

    async def create_room(
        self,
        room_name: str,
        nickname: str,
        password: str,
        board: list,
        lockout: bool = False,
        hide_card: bool = False,
        seed: Optional[int] = None,
    ) -> str:
        # GET first to acquire Django CSRF cookie
        await self._client.get(self.BASE_URL + "/")
        csrf_token = self._client.cookies.get("csrftoken")

        form_data = {
            "room_name": room_name,
            "passphrase": password,
            "nickname": nickname,
            "game_type": "custom",
            "custom_json": json.dumps(board),
            "lockout_mode": "lockout" if lockout else "non_lockout",
            "hide_card": str(hide_card).lower(),
            "csrfmiddlewaretoken": csrf_token,
        }
        if seed is not None:
            form_data["seed"] = seed

        response = await self._client.post(
            self.BASE_URL + "/",
            data=form_data,
            headers={"Referer": self.BASE_URL + "/"},
            follow_redirects=False,
        )
        if response.status_code not in (301, 302):
            raise RuntimeError(f"Room creation failed ({response.status_code}): {response.text}")

        # Extract encoded room UUID from redirect: /room/<encoded_uuid>
        location = response.headers.get("location", "")
        encoded_room_id = location.rstrip("/").split("/")[-1]
        self._room_id = encoded_room_id
        return encoded_room_id

    # ------------------------------------------------------------------ #
    # Board                                                                #
    # ------------------------------------------------------------------ #

    async def post_board(
        self,
        board: list,
        lockout: bool = False,
        hide_card: bool = False,
        seed: Optional[int] = None,
    ):
        self._require_room()
        data = {
            "room": self._room_id,
            "lockout_mode": "2" if lockout else "1",
            "hide_card": hide_card,
            "custom_json": json.dumps(board),
        }
        if seed is not None:
            data["seed"] = seed
        await self._post("/api/new-card", data)

    async def get_board(self) -> list:
        self._require_room()
        response = await self._get(f"/room/{self._room_id}/board")
        return response.json()

    # ------------------------------------------------------------------ #
    # Game actions                                                         #
    # ------------------------------------------------------------------ #

    async def select_cell(self, slot: int, color: Color, remove: bool = False):
        self._require_room()
        await self._post("/api/select", {
            "room": self._room_id,
            "slot": slot,
            "color": int(color),
            "remove_color": remove,
        })

    async def send_chat(self, message: str):
        self._require_room()
        await self._post("/api/chat", {"room": self._room_id, "text": message})

    async def change_color(self, color: Color):
        self._require_room()
        await self._post("/api/color", {"room": self._room_id, "color": int(color)})

    async def reveal_board(self):
        self._require_room()
        await self._post("/api/revealed", {"room": self._room_id})

    # ------------------------------------------------------------------ #
    # Real-time events                                                     #
    # ------------------------------------------------------------------ #

    async def events(self) -> AsyncIterator[dict]:
        self._require_room()
        response = await self._get(f"/api/get-socket-key/{self._room_id}")
        socket_key = response.json()["socket_key"]

        async with websockets.connect(self.WS_URL) as ws:
            await ws.send(json.dumps({"socket_key": socket_key}))
            async for message in ws:
                event = json.loads(message)
                if event.get("type") == "error":
                    raise ConnectionError(f"BingoSync WebSocket: {event.get('error')}")
                yield event
