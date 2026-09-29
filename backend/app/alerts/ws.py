"""Authenticated, jurisdiction-aware WebSocket alert delivery."""
from __future__ import annotations

import asyncio
import json

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[WebSocket, dict[str, str | None]] = {}
        self._lock = asyncio.Lock()

    async def connect(
        self,
        ws: WebSocket,
        *,
        state: str | None = None,
        bank: str | None = None,
    ) -> None:
        await ws.accept()
        async with self._lock:
            self._connections[ws] = {"state": state, "bank": bank}

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._connections.pop(ws, None)

    async def broadcast(self, payload: dict) -> None:
        data = json.dumps(payload, default=str)
        dead = []
        for ws, scope in list(self._connections.items()):
            if scope["state"] and payload.get("state") not in (None, scope["state"]):
                continue
            if scope["bank"] and payload.get("bank_name") != scope["bank"]:
                continue
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.pop(ws, None)


manager = ConnectionManager()
