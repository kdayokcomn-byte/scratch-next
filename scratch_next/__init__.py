"""
scratch-next v3.0.0: High-Performance Modular Scratch Library
"""
from .exceptions import *
from .cache_http import SmartCache, HTTPClient
from .models import User, Project, Studio
from .session import Session, login, login_by_id, get_user, get_project, get_studio, search_projects
from .cloud import (
    CloudEvent,
    VirtualCloudSandbox,
    CloudVariableMultiplexer,
    CloudConnection,
    TurboWarpCloudConnection,
    MultiProjectCloudMesh,
)
from .security import (
    CloudPacketSigner,
    AntiCheatGuard,
    TokenVault,
    NonceReplayProtector,
    ChecksumGuard,
    SecurityUtils,
)
from .ast_tools import ProjectJSONToolkit
from .async_engine import AsyncSession, StreamEventBus, TaskScheduler, BenchmarkProfiler
from .ai_integrations import (
    SentimentAnalyzer,
    SmartFAQResponder,
    DiscordWebhookBridge,
    SQLiteCloudStorage,
    ExternalDataBridge,
)
from .game_server import (
    MatchmakingLobby,
    GlobalLeaderboard,
    PlayerPresenceTracker,
    VirtualEconomyLedger,
    GameSystemsPack,
    ServerTickLoop,
)
from .analytics_encoding import AnalyticsToolkit, Encoding, ScratchUtilities

__version__ = "3.0.0"
