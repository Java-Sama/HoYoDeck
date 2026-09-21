"""数据模型定义"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import StrEnum
from typing import Any

JsonObject = dict[str, Any]


class GameRegion(StrEnum):
    CN = "cn"
    GLOBAL = "global"


class GameStatus(StrEnum):
    NOT_INSTALLED = "not_installed"
    INSTALLED = "installed"
    PARTIAL = "partial"
    UPDATE_AVAILABLE = "update_available"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class GameInfo:
    """单个米哈游游戏的元数据"""
    game_id: str            # e.g. "hk4e_cn", "hkrpg_global"
    title: str              # 显示名称
    region: GameRegion
    executable_names: tuple[str, ...]  # 可能的可执行文件名
    icon_color_start: str   # 封面渐变色
    icon_color_end: str

    def to_dict(self) -> JsonObject:
        return {
            "game_id": self.game_id,
            "title": self.title,
            "region": self.region.value,
            "executable_names": list(self.executable_names),
            "icon_color_start": self.icon_color_start,
            "icon_color_end": self.icon_color_end,
        }


@dataclass(slots=True)
class GameInstallInfo:
    """游戏安装状态详情"""
    game_id: str
    title: str
    region: str
    status: GameStatus = GameStatus.UNKNOWN
    installed: bool = False
    install_path: str | None = None
    executable: str | None = None
    installed_version: str | None = None
    steam_app_id: int | None = None
    has_steam_shortcut: bool = False
    artwork_url: str | None = None

    def to_dict(self) -> JsonObject:
        return {
            "game_id": self.game_id,
            "title": self.title,
            "region": self.region,
            "status": self.status.value,
            "installed": self.installed,
            "install_path": self.install_path,
            "executable": self.executable,
            "installed_version": self.installed_version,
            "steam_app_id": self.steam_app_id,
            "has_steam_shortcut": self.has_steam_shortcut,
            "artwork_url": self.artwork_url,
        }


@dataclass(slots=True)
class RuntimeStatus:
    """兼容层运行时状态"""
    umu_installed: bool = False
    umu_path: str | None = None
    proton_layers: list[dict[str, Any]] = field(default_factory=list)
    ready: bool = False

    def to_dict(self) -> JsonObject:
        return {
            "umu_installed": self.umu_installed,
            "umu_path": self.umu_path,
            "proton_layers": self.proton_layers,
            "ready": self.ready,
        }


@dataclass(slots=True)
class Dashboard:
    """主面板状态"""
    version: str = "1.0.0"
    game_count: int = 0
    installed_count: int = 0
    runtime: RuntimeStatus = field(default_factory=RuntimeStatus)
    games: list[GameInstallInfo] = field(default_factory=list)

    def to_dict(self) -> JsonObject:
        return {
            "version": self.version,
            "game_count": self.game_count,
            "installed_count": self.installed_count,
            "runtime": self.runtime.to_dict(),
            "games": [g.to_dict() for g in self.games],
        }
