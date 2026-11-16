"""
scratch_next.ai_integrations
============================
F061-F075: 感情分析・FAQ自動応答・Discord Webhook・SQLite ORM・外部データ変換
"""

import ast
import json
import time
import hashlib
import sqlite3
import operator
import threading
import urllib.request
import urllib.parse
from typing import Any, Dict, List, Optional


class SentimentAnalyzer:
    """F062: コメント感情スコア分析 (-1.0〜+1.0)"""
    POS = {"すごい", "神", "最高", "楽しい", "面白い", "ありがとう", "好き", "awesome", "great", "cool", "love", "amazing", "gg"}
    NEG = {"つまらない", "クソ", "ゴミ", "バグ", "動かない", "嫌い", "bad", "boring", "lag", "broken", "hate", "worst"}

    @classmethod
    def score(cls, text: str) -> float:
        t = text.lower()
        p = sum(1 for w in cls.POS if w in t)
        n = sum(1 for w in cls.NEG if w in t)
        if p + n == 0:
            return 0.0
        return round((p - n) / (p + n), 2)


class SmartFAQResponder:
    """F064: キーワードルール型 FAQ 自動返信ボット"""
    def __init__(self, faq_map: Dict[str, str]):
        self.faq_map = faq_map

    def reply_for(self, comment_text: str) -> Optional[str]:
        t = comment_text.lower()
        for kw, answer in self.faq_map.items():
            if kw.lower() in t:
                return answer
        return None


class DiscordWebhookBridge:
    """F065: Discord Webhook リアルタイム通知"""
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, content: str, username: str = "scratch-next") -> None:
        data = json.dumps({"content": content, "username": username}).encode("utf-8")
        req = urllib.request.Request(
            self.webhook_url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "scratch-next/3.0"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10):
            pass


class SQLiteCloudStorage:
    """F066 & F078: SQLite 永続化セーブデータORM"""
    def __init__(self, db_path: str = "scratch_next.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._lock = threading.Lock()
        with self.conn:
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS kv_saves (namespace TEXT, key TEXT, val TEXT, updated REAL, PRIMARY KEY(namespace, key))"
            )

    def put(self, namespace: str, key: str, value: Any) -> None:
        with self._lock, self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO kv_saves VALUES (?, ?, ?, ?)",
                (namespace, key.lower(), json.dumps(value, ensure_ascii=False), time.time()),
            )

    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        with self._lock:
            cur = self.conn.execute("SELECT val FROM kv_saves WHERE namespace=? AND key=?", (namespace, key.lower()))
            row = cur.fetchone()
            return json.loads(row[0]) if row else default


class ExternalDataBridge:
    """F068: Wikipedia要約 / F070: ペン描画用ビットマップ / F071: 安全数式評価エンジン"""
    @staticmethod
    def fetch_wikipedia_summary(title: str, lang: str = "ja") -> str:
        encoded = urllib.parse.quote(title)
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded}"
        req = urllib.request.Request(url, headers={"User-Agent": "scratch-next/3.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("extract", "")

    @staticmethod
    def safe_eval_math(expr: str) -> float:
        ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
        }
        def _eval(node):
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return float(node.value)
            if isinstance(node, ast.BinOp) and type(node.op) in ops:
                return ops[type(node.op)](_eval(node.left), _eval(node.right))
            if isinstance(node, ast.UnaryOp) and type(node.op) in ops:
                return ops[type(node.op)](_eval(node.operand))
            raise ValueError("Unsupported math expression")
        tree = ast.parse(expr, mode="eval")
        return _eval(tree.body)

    @staticmethod
    def text_to_bitmap_matrix(text: str, size: int = 16) -> List[List[int]]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        bits = "".join(f"{b:08b}" for b in digest)
        return [[int(bits[(r * size + c) % len(bits)]) for c in range(size)] for r in range(size)]
