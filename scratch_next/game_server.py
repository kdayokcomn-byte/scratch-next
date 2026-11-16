"""
scratch_next.game_server
========================
F076-F090: マルチプレイロビー・無限ランキング・通貨台帳・イロレーティング・20TPSサーバー
"""

import json
import time
import random
import threading
from typing import Callable, Dict, List, Optional, Tuple
from .ai_integrations import SQLiteCloudStorage


class MatchmakingLobby:
    """F076: オンライン自動マッチングロビー"""
    def __init__(self, room_size: int = 2):
        self.room_size = room_size
        self._queue: List[str] = []
        self.rooms: Dict[str, List[str]] = {}

    def join_queue(self, username: str) -> Optional[str]:
        u = username.lower()
        if u not in self._queue:
            self._queue.append(u)
        if len(self._queue) >= self.room_size:
            members = [self._queue.pop(0) for _ in range(self.room_size)]
            room_id = f"room_{int(time.time() * 1000)}_{random.randint(100, 999)}"
            self.rooms[room_id] = members
            return room_id
        return None


class GlobalLeaderboard:
    """F077: 無制限グローバルリーダーボード"""
    def __init__(self, storage: Optional[SQLiteCloudStorage] = None):
        self.db = storage or SQLiteCloudStorage()

    def submit(self, board_name: str, username: str, score: float) -> float:
        curr = self.db.get(f"lb_{board_name}", username, default=None)
        best = max(float(curr), float(score)) if curr is not None else float(score)
        self.db.put(f"lb_{board_name}", username, best)
        return best

    def get_top(self, board_name: str, limit: int = 10) -> List[Tuple[str, float]]:
        with self.db._lock:
            cur = self.db.conn.execute("SELECT key, val FROM kv_saves WHERE namespace=?", (f"lb_{board_name}",))
            items = [(r[0], float(json.loads(r[1]))) for r in cur.fetchall()]
        items.sort(key=lambda x: x[1], reverse=True)
        return items[:limit]


class PlayerPresenceTracker:
    """F080: ハートビート生存確認＆自動タイムアウト離脱"""
    def __init__(self, timeout_sec: float = 15.0):
        self.timeout_sec = timeout_sec
        self._last_seen: Dict[str, float] = {}

    def heartbeat(self, username: str) -> None:
        self._last_seen[username.lower()] = time.monotonic()

    def online_players(self) -> List[str]:
        now = time.monotonic()
        active = [u for u, ts in self._last_seen.items() if now - ts <= self.timeout_sec]
        self._last_seen = {u: self._last_seen[u] for u in active}
        return active


class VirtualEconomyLedger:
    """F081: ゲーム内通貨・アイテム取引台帳"""
    def __init__(self, storage: Optional[SQLiteCloudStorage] = None):
        self.db = storage or SQLiteCloudStorage()

    def balance(self, username: str) -> int:
        return int(self.db.get("economy_coins", username, default=0))

    def grant(self, username: str, amount: int) -> int:
        new_bal = max(0, self.balance(username) + amount)
        self.db.put("economy_coins", username, new_bal)
        return new_bal

    def transfer(self, sender: str, receiver: str, amount: int) -> bool:
        if amount <= 0 or self.balance(sender) < amount:
            return False
        self.grant(sender, -amount)
        self.grant(receiver, amount)
        return True


class GameSystemsPack:
    """F084: ガチャ抽選 / F086: PvPイロレーティング / F088: 大会トーナメント表生成"""
    @staticmethod
    def roll_gacha(pool: Dict[str, float]) -> str:
        return random.choices(list(pool.keys()), weights=list(pool.values()), k=1)[0]

    @staticmethod
    def calculate_elo(rating_a: float, rating_b: float, a_won: bool, k: float = 32.0) -> Tuple[float, float]:
        expected_a = 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))
        score_a = 1.0 if a_won else 0.0
        new_a = round(rating_a + k * (score_a - expected_a), 1)
        new_b = round(rating_b + k * ((1.0 - score_a) - (1.0 - expected_a)), 1)
        return new_a, new_b

    @staticmethod
    def generate_tournament_bracket(players: List[str]) -> List[Tuple[str, str]]:
        shuffled = list(players)
        random.shuffle(shuffled)
        if len(shuffled) % 2 == 1:
            shuffled.append("BYE (不戦勝)")
        return [(shuffled[i], shuffled[i + 1]) for i in range(0, len(shuffled), 2)]


class ServerTickLoop:
    """F087: 20TPS 固定レートサーバーゲームループ"""
    def __init__(self, tps: int = 20):
        self.tps = max(1, tps)
        self._running = False

    def start(self, on_tick: Callable[[int], None]) -> None:
        self._running = True
        dt = 1.0 / self.tps
        def _run():
            tick = 0
            while self._running:
                t0 = time.perf_counter()
                on_tick(tick)
                tick += 1
                sleep_time = dt - (time.perf_counter() - t0)
                if sleep_time > 0:
                    time.sleep(sleep_time)
        threading.Thread(target=_run, daemon=True).start()

    def stop(self) -> None:
        self._running = False
