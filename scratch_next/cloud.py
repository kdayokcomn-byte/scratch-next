"""
scratch_next.cloud
==================
F001-F015: 高速クラウドエンジン・多重化・スナップショット・リプレイ・TurboWarp対応
"""

import json
import time
import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Union
from .cache_http import HTTPClient
from .exceptions import ScratchNextError, CloudConnectionError


@dataclass
class CloudEvent:
    user: str
    var: str
    value: str
    timestamp: float = field(default_factory=time.time)


class VirtualCloudSandbox:
    """F009: オフライン高速テスト用の仮想クラウドサーバー"""
    def __init__(self, project_id: int = 0):
        self.project_id = project_id
        self._vars: Dict[str, str] = {}
        self.audit_log: List[CloudEvent] = []

    def set_var(self, variable: str, value: Union[int, float, str], user: str = "local_tester") -> None:
        name = variable if variable.startswith("☁ ") else f"☁ {variable}"
        val_str = str(value)
        self._vars[name] = val_str
        self.audit_log.append(CloudEvent(user=user, var=name, value=val_str))

    def get_var(self, variable: str) -> Optional[str]:
        name = variable if variable.startswith("☁ ") else f"☁ {variable}"
        return self._vars.get(name)

    def get_all_vars(self) -> Dict[str, str]:
        return dict(self._vars)


class CloudVariableMultiplexer:
    """F011: 1つのクラウド変数(256桁)に最大40個のサブ変数をパッキング多重化"""
    @staticmethod
    def pack(slots: Dict[str, int], width: int = 6) -> str:
        parts = [f"{len(slots):02d}"]
        for key in sorted(slots.keys()):
            val = max(0, min(10**width - 1, int(slots[key])))
            parts.append(f"{val:0{width}d}")
        return "".join(parts)

    @staticmethod
    def unpack(packed_digits: str, keys: List[str], width: int = 6) -> Dict[str, int]:
        s = str(packed_digits)
        if len(s) < 2:
            return {}
        res = {}
        idx = 2
        for k in sorted(keys):
            if idx + width <= len(s):
                res[k] = int(s[idx : idx + width])
                idx += width
        return res


class CloudConnection:
    """
    F001: 指数バックオフ自動リトライ
    F002: 0.1秒レート制限自動回避キュー
    F004: スナップショット保存・復元
    F005: 差分ウォッチャー (@cloud.on_set)
    F007: RTT遅延計測
    F012: 監査ログ
    F013: 不正値検知時の自動ロールバック
    F015: リプレイ再生
    """
    CLOUDDATA_URL = "https://clouddata.scratch.mit.edu"

    def __init__(self, project_id: int, http: HTTPClient, ws_host: str = "wss://clouddata.scratch.mit.edu"):
        self.project_id = int(project_id)
        self._http = http
        self.ws_host = ws_host
        self._vars: Dict[str, str] = {}
        self._snapshots: Dict[str, Dict[str, str]] = {}
        self._listeners: Dict[str, List[Callable[[CloudEvent], None]]] = {}
        self._validators: Dict[str, Callable[[str], bool]] = {}
        self.audit_logs: List[CloudEvent] = []
        self._last_send_time = 0.0
        self._lock = threading.Lock()
        self.refresh_from_logs()

    @staticmethod
    def _norm(variable: str) -> str:
        return variable if variable.startswith("☁ ") else f"☁ {variable}"

    def measure_latency_ms(self) -> float:
        t0 = time.perf_counter()
        url = f"{self.CLOUDDATA_URL}/logs?projectid={self.project_id}&limit=1&offset=0"
        self._http.request("GET", url)
        return round((time.perf_counter() - t0) * 1000, 2)

    def refresh_from_logs(self, limit: int = 100) -> List[CloudEvent]:
        url = f"{self.CLOUDDATA_URL}/logs?projectid={self.project_id}&limit={limit}&offset=0"
        logs = self._http.request("GET", url)
        events: List[CloudEvent] = []
        if isinstance(logs, list):
            for entry in reversed(logs):
                var_name = entry.get("name", "")
                val = str(entry.get("value", ""))
                user = entry.get("user", "unknown")
                ts = float(entry.get("timestamp", time.time() * 1000)) / 1000.0
                old_val = self._vars.get(var_name)

                if var_name in self._validators and not self._validators[var_name](val):
                    if old_val is not None:
                        self.set_var(var_name, old_val)
                    continue

                self._vars[var_name] = val
                ev = CloudEvent(user=user, var=var_name, value=val, timestamp=ts)
                events.append(ev)
                self.audit_logs.append(ev)
                if old_val != val:
                    for cb in self._listeners.get(var_name, []) + self._listeners.get("*", []):
                        cb(ev)
        return events

    def set_validator(self, variable: str, predicate: Callable[[str], bool]) -> None:
        self._validators[self._norm(variable)] = predicate

    def get_var(self, variable: str) -> Optional[str]:
        self.refresh_from_logs(limit=25)
        return self._vars.get(self._norm(variable))

    def get_all_vars(self) -> Dict[str, str]:
        self.refresh_from_logs(limit=100)
        return dict(self._vars)

    def set_var(self, variable: str, value: Union[int, float, str], max_retries: int = 3) -> None:
        val_str = str(value)
        if len(val_str) > 256:
            raise ScratchNextError(f"Value length {len(val_str)} > 256 limit")

        with self._lock:
            elapsed = time.monotonic() - self._last_send_time
            if elapsed < 0.105:
                time.sleep(0.105 - elapsed)

            var_name = self._norm(variable)
            for attempt in range(max_retries):
                try:
                    import websockets.sync.client as ws_sync  # type: ignore
                    headers = {
                        "Cookie": f'scratchsessionsid="{self._http.session_id}";',
                        "Origin": "https://scratch.mit.edu",
                    }
                    with ws_sync.connect(self.ws_host, additional_headers=headers, open_timeout=8) as ws:
                        handshake_msg = json.dumps({
                            "method": "handshake",
                            "user": self._http.username,
                            "project_id": str(self.project_id),
                        }) + "\n"
                        set_msg = json.dumps({
                            "method": "set",
                            "user": self._http.username,
                            "project_id": str(self.project_id),
                            "name": var_name,
                            "value": val_str,
                        }) + "\n"
                        ws.send(handshake_msg)
                        ws.send(set_msg)
                    self._vars[var_name] = val_str
                    self._last_send_time = time.monotonic()
                    return
                except ImportError:
                    raise CloudConnectionError("Install `websockets` (`pip install websockets`) for live WS writes.")
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise CloudConnectionError(f"Failed after {max_retries} attempts: {e}") from e
                    time.sleep(0.3 * (2 ** attempt))

    def save_snapshot(self, name: str = "default") -> Dict[str, str]:
        self._snapshots[name] = dict(self._vars)
        return dict(self._vars)

    def restore_snapshot(self, name: str = "default") -> None:
        if name not in self._snapshots:
            raise ScratchNextError(f"Snapshot '{name}' does not exist")
        for k, v in self._snapshots[name].items():
            self.set_var(k, v)

    def on_set(self, variable: str = "*") -> Callable:
        key = "*" if variable == "*" else self._norm(variable)
        def decorator(fn: Callable[[CloudEvent], None]) -> Callable[[CloudEvent], None]:
            self._listeners.setdefault(key, []).append(fn)
            return fn
        return decorator

    def replay_events(self, events: List[CloudEvent], speed: float = 1.0) -> None:
        for i, ev in enumerate(events):
            if i > 0 and speed > 0:
                dt = max(0.0, min(2.0, (ev.timestamp - events[i - 1].timestamp) / speed))
                time.sleep(dt)
            for cb in self._listeners.get(ev.var, []) + self._listeners.get("*", []):
                cb(ev)


class TurboWarpCloudConnection(CloudConnection):
    """F003: TurboWarp クラウドサーバー接続"""
    def __init__(self, project_id: int, http: HTTPClient):
        super().__init__(project_id=project_id, http=http, ws_host="wss://clouddata.turbowarp.org")


class MultiProjectCloudMesh:
    """F006: 複数プロジェクト間のクラウド変数双方向メッシュ同期"""
    def __init__(self, connections: List[CloudConnection]):
        self.connections = connections

    def sync_variable(self, variable: str, source_index: int = 0) -> None:
        val = self.connections[source_index].get_var(variable)
        if val is None:
            return
        for idx, conn in enumerate(self.connections):
            if idx != source_index:
                conn.set_var(variable, val)
