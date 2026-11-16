"""
scratch_next.exceptions
=======================
詳細エラー診断用の例外クラス階層
"""


class ScratchNextError(Exception):
    """scratch-next 基底例外"""


class AuthenticationError(ScratchNextError):
    """認証・ログイン・セッションエラー"""


class CloudConnectionError(ScratchNextError):
    """クラウド変数・WebSocket通信エラー"""


class RateLimitError(ScratchNextError):
    """Scratch API レート制限 (HTTP 429) エラー"""


class SecurityViolationError(ScratchNextError):
    """アンチチート・署名検証・セーフモード違反"""


class ProjectASTError(ScratchNextError):
    """project.json 構文解析・操作エラー"""
