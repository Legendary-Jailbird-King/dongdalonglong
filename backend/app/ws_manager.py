"""
WebSocket 连接管理器（独立模块，避免循环导入）。

按角色 & 用户 ID 管理 WebSocket 连接，支持向指定商家/骑手推送消息。
"""
from typing import Dict, List

from fastapi import WebSocket


class ConnectionManager:
    """简易 WebSocket 连接管理器。"""

    def __init__(self):
        self._connections: Dict[str, Dict[int, List[WebSocket]]] = {
            "merchant": {},
            "courier": {},
            "customer": {},
        }

    async def connect(self, ws: WebSocket, role: str, user_id: int):
        await ws.accept()
        self._connections.setdefault(role, {}).setdefault(user_id, []).append(ws)

    def disconnect(self, ws: WebSocket, role: str, user_id: int):
        bucket = self._connections.get(role, {}).get(user_id, [])
        if ws in bucket:
            bucket.remove(ws)

    async def send_to_merchant(self, merchant_id: int, message: dict):
        """向指定商家推送消息。"""
        for ws in self._connections.get("merchant", {}).get(merchant_id, []):
            try:
                await ws.send_json(message)
            except Exception:
                pass

    async def send_to_courier(self, courier_id: int, message: dict):
        """向指定骑手推送消息。"""
        for ws in self._connections.get("courier", {}).get(courier_id, []):
            try:
                await ws.send_json(message)
            except Exception:
                pass


# ── 全局单例 ──────────────────────────────────────────────
manager = ConnectionManager()
