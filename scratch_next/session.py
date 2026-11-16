"""
scratch_next.session
====================
ログイン・セッション管理・グローバルショートカット関数
"""

import re
import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Any, Dict, List, Optional
from .cache_http import HTTPClient
from .models import User, Project, Studio
from .exceptions import AuthenticationError


class Session:
    def __init__(self, session_id: str, username: Optional[str] = None, csrf_token: str = "a"):
        self.session_id = session_id
        self.username = username
        self._http = HTTPClient(session_id=session_id, csrf_token=csrf_token, username=username)

    def enable_safe_mode(self, enabled: bool = True) -> None:
        """F028: 書き込み系APIをロックして誤操作を防止"""
        self._http.read_only_mode = enabled

    def cache_stats(self) -> Dict[str, Any]:
        return self._http.cache.stats()

    def connect_cloud(self, project_id: int):
        from .cloud import CloudConnection
        return CloudConnection(project_id=project_id, http=self._http)

    def connect_turbowarp_cloud(self, project_id: int):
        from .cloud import TurboWarpCloudConnection
        return TurboWarpCloudConnection(project_id=project_id, http=self._http)

    def connect_user(self, username: str) -> User:
        return User(username=username, http=self._http)

    def connect_project(self, project_id: int) -> Project:
        return Project(project_id=project_id, http=self._http)

    def connect_studio(self, studio_id: int) -> Studio:
        return Studio(studio_id=studio_id, http=self._http)

    def messages(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        if not self.username:
            raise AuthenticationError("Username required")
        return self._http.request("GET", f"{HTTPClient.BASE_API}/users/{self.username}/messages?limit={limit}&offset={offset}")


_anon_http = HTTPClient()


def login(username: str, password: str) -> Session:
    url = "https://scratch.mit.edu/login/"
    payload = json.dumps({"username": username, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "User-Agent": "Mozilla/5.0 (Scratch-Next/3.0.0)",
            "Content-Type": "application/json",
            "X-CSRFToken": "a",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://scratch.mit.edu/",
            "Cookie": "scratchcsrftoken=a;",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            cookies = resp.headers.get_all("Set-Cookie") or []
            session_id = ""
            for c in cookies:
                m = re.search(r'scratchsessionsid="([^"]+)"', c)
                if m:
                    session_id = m.group(1)
                    break
            if not session_id:
                raise AuthenticationError("scratchsessionsid cookie not returned.")
            return Session(session_id=session_id, username=username)
    except urllib.error.HTTPError as e:
        raise AuthenticationError(f"Login failed (HTTP {e.code})") from e


def login_by_id(session_id: str, username: Optional[str] = None) -> Session:
    return Session(session_id=session_id, username=username)


def get_user(username: str) -> User:
    return User(username=username, http=_anon_http)


def get_project(project_id: int) -> Project:
    return Project(project_id=project_id, http=_anon_http)


def get_studio(studio_id: int) -> Studio:
    return Studio(studio_id=studio_id, http=_anon_http)


def search_projects(query: str, mode: str = "popular", limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    q = urllib.parse.quote(query)
    return _anon_http.request(
        "GET", f"{HTTPClient.BASE_API}/search/projects?q={q}&mode={mode}&limit={limit}&offset={offset}", use_cache=True
    )
