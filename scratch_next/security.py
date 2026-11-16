"""
scratch_next.security
=====================
F016-F030: アンチチート・HMAC署名・トークン暗号化・Nonceリプレイ防御
"""

import re
import hmac
import zlib
import time
import base64
import hashlib
import datetime
from collections import deque
from typing import Dict, List, Optional, Set, Tuple, Union
from .exceptions import SecurityViolationError


class CloudPacketSigner:
    """F017: HMAC-SHA256 パケット署名・改ざん検証"""
    def __init__(self, secret_key: str):
        self._key = secret_key.encode("utf-8")

    def sign(self, digits: str) -> str:
        digest = hmac.new(self._key, digits.encode("utf-8"), hashlib.sha256).hexdigest()
        sig10 = int(digest[:8], 16) % (10**10)
        return f"{digits}{sig10:010d}"

    def verify(self, signed_digits: str) -> Tuple[bool, str]:
        if len(signed_digits) <= 10:
            return False, ""
        payload, sig = signed_digits[:-10], signed_digits[-10:]
        expected = self.sign(payload)[-10:]
        return hmac.compare_digest(sig, expected), payload


class AntiCheatGuard:
    """F016/F018/F019/F022/F024: 速度チート検知・自動BAN・シャドウBAN・範囲検証"""
    def __init__(
        self,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        max_ops_per_sec: float = 10.0,
        whitelist: Optional[Set[str]] = None,
        shadow_ban_mode: bool = False,
    ):
        self.min_val = min_val
        self.max_val = max_val
        self.max_ops_per_sec = max_ops_per_sec
        self.whitelist = {u.lower() for u in whitelist} if whitelist else None
        self.shadow_ban_mode = shadow_ban_mode
        self.blacklist: Set[str] = set()
        self._history: Dict[str, deque] = {}

    def check(self, username: str, value: Union[int, float, str]) -> bool:
        u = username.lower()
        if self.whitelist is not None and u not in self.whitelist:
            if self.shadow_ban_mode:
                return False
            raise SecurityViolationError(f"User '{username}' not in whitelist")

        if u in self.blacklist:
            if self.shadow_ban_mode:
                return False
            raise SecurityViolationError(f"User '{username}' is blacklisted")

        now = time.monotonic()
        q = self._history.setdefault(u, deque())
        q.append(now)
        while q and now - q[0] > 1.0:
            q.popleft()
        if len(q) > self.max_ops_per_sec:
            self.blacklist.add(u)
            if self.shadow_ban_mode:
                return False
            raise SecurityViolationError(f"Speed cheat detected from '{username}' ({len(q)} ops/s)")

        try:
            num = float(value)
            if self.min_val is not None and num < self.min_val:
                raise SecurityViolationError(f"Value {num} < {self.min_val}")
            if self.max_val is not None and num > self.max_val:
                raise SecurityViolationError(f"Value {num} > {self.max_val}")
        except ValueError:
            pass
        return True


class TokenVault:
    """F020: セッションIDやAPIキーの暗号化ボールト"""
    @staticmethod
    def encrypt(secret_text: str, passphrase: str) -> str:
        key = hashlib.sha256(passphrase.encode("utf-8")).digest()
        raw = secret_text.encode("utf-8")
        xored = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
        return base64.urlsafe_b64encode(xored).decode("ascii")

    @staticmethod
    def decrypt(token_b64: str, passphrase: str) -> str:
        key = hashlib.sha256(passphrase.encode("utf-8")).digest()
        raw = base64.urlsafe_b64decode(token_b64.encode("ascii"))
        plain = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
        return plain.decode("utf-8")


class NonceReplayProtector:
    """F023: ノンスによるリプレイ攻撃防止"""
    def __init__(self, max_memory: int = 5000):
        self._seen: deque = deque(maxlen=max_memory)

    def accept(self, nonce: str) -> bool:
        if nonce in self._seen:
            return False
        self._seen.append(nonce)
        return True


class ChecksumGuard:
    """F026: CRC32チェックサム付与・検証"""
    @staticmethod
    def attach(digits: str) -> str:
        crc = zlib.crc32(digits.encode("utf-8")) % 100000
        return f"{digits}{crc:05d}"

    @staticmethod
    def verify(digits_with_crc: str) -> Tuple[bool, str]:
        if len(digits_with_crc) <= 5:
            return False, ""
        body, crc_str = digits_with_crc[:-5], digits_with_crc[-5:]
        expected = f"{zlib.crc32(body.encode('utf-8')) % 100000:05d}"
        return crc_str == expected, body


class SecurityUtils:
    """F021/F025/F027/F029: スパム判定・アカウント経過日数・マスク出力"""
    @staticmethod
    def is_spam_comment(text: str, banned_words: Optional[List[str]] = None) -> bool:
        t = text.lower()
        if re.search(r"(https?://|discord\.gg/|bit\.ly/)", t):
            return True
        for w in (banned_words or ["free followers", "f4f spam"]):
            if w.lower() in t:
                return True
        return False

    @staticmethod
    def account_age_days(joined_iso: str) -> int:
        try:
            dt = datetime.datetime.fromisoformat(joined_iso.replace("Z", "+00:00"))
            now = datetime.datetime.now(datetime.timezone.utc)
            return max(0, (now - dt).days)
        except Exception:
            return 0

    @staticmethod
    def mask_token(token: str) -> str:
        if len(token) <= 6:
            return "***"
        return f"{token[:3]}...{token[-3:]}"
