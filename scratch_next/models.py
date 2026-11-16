"""
scratch_next.models
===================
scratchattach 完全互換の User / Project / Studio リッチモデル
"""

from typing import Any, Dict, List, Optional
from .cache_http import HTTPClient
from .exceptions import AuthenticationError


class User:
    def __init__(self, username: str, http: HTTPClient):
        self.username = username
        self._http = http
        self._raw: Optional[Dict[str, Any]] = None

    def update(self) -> Dict[str, Any]:
        self._raw = self._http.request("GET", f"{HTTPClient.BASE_API}/users/{self.username}", use_cache=True)
        return self._raw or {}

    @property
    def id(self) -> Optional[int]:
        return (self._raw or self.update()).get("id")

    @property
    def scratchteam(self) -> bool:
        return bool((self._raw or self.update()).get("scratchteam", False))

    @property
    def about_me(self) -> str:
        return (self._raw or self.update()).get("profile", {}).get("bio", "")

    @property
    def wiwo(self) -> str:
        return (self._raw or self.update()).get("profile", {}).get("status", "")

    @property
    def joined_date(self) -> str:
        return (self._raw or self.update()).get("history", {}).get("joined", "")

    def projects(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        return self._http.request(
            "GET", f"{HTTPClient.BASE_API}/users/{self.username}/projects?limit={limit}&offset={offset}", use_cache=True
        )

    def followers(self, limit: int = 40, offset: int = 0) -> List[Dict[str, Any]]:
        return self._http.request(
            "GET", f"{HTTPClient.BASE_API}/users/{self.username}/followers?limit={limit}&offset={offset}", use_cache=True
        )

    def following(self, limit: int = 40, offset: int = 0) -> List[Dict[str, Any]]:
        return self._http.request(
            "GET", f"{HTTPClient.BASE_API}/users/{self.username}/following?limit={limit}&offset={offset}", use_cache=True
        )

    def follow(self) -> Any:
        if not self._http.username:
            raise AuthenticationError("Login required")
        return self._http.request(
            "PUT", f"{HTTPClient.BASE_SITE}/site-api/users/followers/{self.username}/add/?usernames={self._http.username}"
        )

    def unfollow(self) -> Any:
        if not self._http.username:
            raise AuthenticationError("Login required")
        return self._http.request(
            "PUT", f"{HTTPClient.BASE_SITE}/site-api/users/followers/{self.username}/remove/?usernames={self._http.username}"
        )

    def post_comment(self, content: str, parent_id: str = "", commentee_id: str = "") -> Any:
        return self._http.request(
            "POST",
            f"{HTTPClient.BASE_SITE}/site-api/comments/user/{self.username}/add/",
            {"content": content, "parent_id": parent_id, "commentee_id": commentee_id},
        )


class Project:
    def __init__(self, project_id: int, http: HTTPClient):
        self.id = int(project_id)
        self._http = http
        self._raw: Optional[Dict[str, Any]] = None

    def update(self) -> Dict[str, Any]:
        self._raw = self._http.request("GET", f"{HTTPClient.BASE_API}/projects/{self.id}", use_cache=True)
        return self._raw or {}

    @property
    def title(self) -> str:
        return (self._raw or self.update()).get("title", "")

    @property
    def instructions(self) -> str:
        return (self._raw or self.update()).get("instructions", "")

    @property
    def notes(self) -> str:
        return (self._raw or self.update()).get("description", "")

    @property
    def author(self) -> str:
        return (self._raw or self.update()).get("author", {}).get("username", "")

    @property
    def stats(self) -> Dict[str, int]:
        return (self._raw or self.update()).get("stats", {})

    def get_json(self) -> Dict[str, Any]:
        meta = self.update()
        token = meta.get("project_token", "")
        url = f"https://projects.scratch.mit.edu/{self.id}" + (f"?token={token}" if token else "")
        return self._http.request("GET", url)

    def get_ast_toolkit(self):
        from .ast_tools import ProjectJSONToolkit
        return ProjectJSONToolkit(self.get_json())

    def love(self) -> Any:
        return self._http.request("POST", f"{HTTPClient.BASE_API}/proxy/projects/{self.id}/loves/user/{self._http.username}")

    def unlove(self) -> Any:
        return self._http.request("DELETE", f"{HTTPClient.BASE_API}/proxy/projects/{self.id}/loves/user/{self._http.username}")

    def favorite(self) -> Any:
        return self._http.request("POST", f"{HTTPClient.BASE_API}/proxy/projects/{self.id}/favorites/user/{self._http.username}")

    def post_comment(self, content: str, parent_id: str = "", commentee_id: str = "") -> Any:
        return self._http.request(
            "POST",
            f"{HTTPClient.BASE_API}/proxy/comments/project/{self.id}",
            {"content": content, "parent_id": parent_id, "commentee_id": commentee_id},
        )

    def comments(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        return self._http.request(
            "GET", f"{HTTPClient.BASE_API}/users/{self.author}/projects/{self.id}/comments?limit={limit}&offset={offset}"
        )


class Studio:
    def __init__(self, studio_id: int, http: HTTPClient):
        self.id = int(studio_id)
        self._http = http
        self._raw: Optional[Dict[str, Any]] = None

    def update(self) -> Dict[str, Any]:
        self._raw = self._http.request("GET", f"{HTTPClient.BASE_API}/studios/{self.id}", use_cache=True)
        return self._raw or {}

    @property
    def title(self) -> str:
        return (self._raw or self.update()).get("title", "")

    def projects(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        return self._http.request(
            "GET", f"{HTTPClient.BASE_API}/studios/{self.id}/projects?limit={limit}&offset={offset}", use_cache=True
        )

    def add_project(self, project_id: int) -> Any:
        return self._http.request("POST", f"{HTTPClient.BASE_API}/studios/{self.id}/project/{project_id}")

    def remove_project(self, project_id: int) -> Any:
        return self._http.request("DELETE", f"{HTTPClient.BASE_API}/studios/{self.id}/project/{project_id}")

    def post_comment(self, content: str, parent_id: str = "", commentee_id: str = "") -> Any:
        return self._http.request(
            "POST",
            f"{HTTPClient.BASE_API}/proxy/comments/studio/{self.id}",
            {"content": content, "parent_id": parent_id, "commentee_id": commentee_id},
        )
