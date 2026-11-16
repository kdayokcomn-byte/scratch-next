"""
scratch_next.async_engine
=========================
F046-F060: AsyncIO並列セッション・PubSubイベントバス・スケジューラ・プロファイラ
"""

import time
import asyncio
import threading
from typing import Any, Callable, Dict, List
from .session import Session


class AsyncSession:
    """F046 & F047: ノンブロッキング非同期セッション＆一括並列バッチ取得"""
    def __init__(self, session: Session):
        self._sync = session

    async def get_user(self, username: str) -> Dict[str, Any]:
        return await asyncio.to_thread(self._sync.connect_user(username).update)

    async def get_project(self, project_id: int) -> Dict[str, Any]:
        return await asyncio.to_thread(self._sync.connect_project(project_id).update)

    async def batch_users(self, usernames: List[str]) -> List[Dict[str, Any]]:
        return list(await asyncio.gather(*(self.get_user(u) for u in usernames)))

    async def batch_projects(self, project_ids: List[int]) -> List[Dict[str, Any]]:
        return list(await asyncio.gather(*(self.get_project(pid) for pid in project_ids)))


class StreamEventBus:
    """F054: トピック駆動型 Pub/Sub イベントバス"""
    def __init__(self):
        self._subs: Dict[str, List[Callable[[Any], None]]] = {}

    def subscribe(self, topic: str, handler: Callable[[Any], None]) -> None:
        self._subs.setdefault(topic, []).append(handler)

    def publish(self, topic: str, payload: Any) -> None:
        for fn in self._subs.get(topic, []):
            fn(payload)


class TaskScheduler:
    """F050: バックグラウンド定期実行スケジューラ"""
    def __init__(self):
        self._running = False
        self._threads: List[threading.Thread] = []

    def every(self, interval_sec: float, fn: Callable[[], None]) -> None:
        self._running = True
        def _loop():
            while self._running:
                time.sleep(interval_sec)
                if self._running:
                    fn()
        t = threading.Thread(target=_loop, daemon=True)
        t.start()
        self._threads.append(t)

    def stop_all(self) -> None:
        self._running = False


class BenchmarkProfiler:
    """F056: ミリ秒精度の関数実行時間プロファイラ"""
    def __init__(self):
        self.records: Dict[str, List[float]] = {}

    def measure(self, label: str, fn: Callable, *args, **kwargs) -> Any:
        t0 = time.perf_counter()
        res = fn(*args, **kwargs)
        ms = (time.perf_counter() - t0) * 1000.0
        self.records.setdefault(label, []).append(round(ms, 3))
        return res
