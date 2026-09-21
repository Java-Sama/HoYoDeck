"""
游戏安装检测器 — 扫描 Wine 注册表和文件系统

检测原理:
  1. 读取 Wine 前缀的 user.reg 文件，查找 GameBiz 和 GameInstallPath 键值
  2. 根据 GameBiz 匹配到已知的游戏 ID（如 hk4e_cn → genshin_cn）
  3. 验证安装路径下是否存在对应的游戏可执行文件

Wine 注册表路径:
  ~/.local/share/hoyodeck/prefixes/{prefix_name}/user.reg
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from .games import ALL_GAMES, MIHOYO_LAUNCHER_CONFIG, HOYOPLAY_LAUNCHER_CONFIG
from .models import GameInfo, GameInstallInfo, GameStatus, JsonObject

_REGISTRY_SECTION = re.compile(
    r"(?ms)^\[(?P<header>[^\n]+)\]\s*(?P<body>.*?)(?=^\[|\Z)"
)
_REGISTRY_VALUE = re.compile(r'^"(?P<name>[^"]+)"="(?P<value>(?:\\\\.|[^"])*)"$', re.MULTILINE)
_WINE_DRIVE_PATH = re.compile(r"^(?P<drive>[A-Za-z]):\\(?P<path>.*)$")


def _registry_sections(contents: str) -> list[tuple[str, dict[str, str]]]:
    """解析 Wine 注册表文件，返回 (header, {name: value}) 列表"""
    return [
        (
            match.group("header"),
            {
                m.group("name"): m.group("value").replace("\\\\", "\\")
                for m in _REGISTRY_VALUE.finditer(match.group("body"))
            },
        )
        for match in _REGISTRY_SECTION.finditer(contents)
    ]


def _resolve_wine_path(prefix_dir: Path, value: str) -> Path | None:
    """将 Wine 路径 (如 C:\\Games\\Genshin) 解析为 Linux 路径"""
    match = _WINE_DRIVE_PATH.fullmatch(value)
    if match is None:
        return None
    drive = match.group("drive").lower()
    parts = tuple(p for p in match.group("path").split("\\") if p and p not in (".", ".."))
    if not parts:
        return None
    drive_link = prefix_dir / "dosdevices" / f"{drive}:"
    try:
        drive_root = drive_link.resolve(strict=False)
        candidate = drive_root.joinpath(*parts)
        resolved = candidate.resolve(strict=True)
        if resolved != drive_root and resolved.is_relative_to(drive_root):
            return resolved
    except OSError:
        pass
    return None


def _find_launcher_executable(prefix_dir: Path, candidates: tuple[str, ...]) -> Path | None:
    """在 Wine 前缀中查找启动器可执行文件"""
    for relative in candidates:
        candidate = prefix_dir / relative
        if candidate.is_file():
            return candidate
    return None


def _read_game_version(install_path: Path) -> str | None:
    """从 config.ini 读取游戏版本"""
    config = install_path / "config.ini"
    try:
        if config.stat().st_size > 64 * 1024:
            return None
        contents = config.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    match = re.search(r"(?mi)^game_version\s*=\s*([^\r\n]+)$", contents)
    return match.group(1).strip() if match else None


class GameDetector:
    """扫描 Wine 前缀，检测已安装的米哈游游戏"""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)

    @property
    def cn_prefix(self) -> Path:
        return self.data_dir / "prefixes" / "mihoyo-cn"

    @property
    def global_prefix(self) -> Path:
        return self.data_dir / "prefixes" / "hoyoplay-global"

    def _detect_games_in_prefix(
        self,
        prefix_dir: Path,
        launcher_config: dict[str, Any],
        region: str,
    ) -> list[GameInstallInfo]:
        """扫描一个 Wine 前缀中的游戏安装"""
        results: list[GameInstallInfo] = []

        launcher_exe = None
        reg_contents = ""
        registry_games: dict[str, str] = {}

        if prefix_dir.is_dir():
            launcher_exe = _find_launcher_executable(
                prefix_dir, launcher_config["executable_candidates"]
            )
            user_reg = prefix_dir / "user.reg"
            try:
                reg_contents = user_reg.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass
            for _header, values in _registry_sections(reg_contents):
                biz = values.get("GameBiz", "")
                install_path = values.get("GameInstallPath", "")
                if biz and install_path:
                    registry_games[biz.casefold()] = install_path

        for game_info in self._games_for_region(region):
            info = GameInstallInfo(
                game_id=game_info.game_id,
                title=game_info.title,
                region=region,
            )

            # 从注册表查找安装路径
            raw_path = registry_games.get(game_info.game_id.casefold())
            install_path = None
            if raw_path:
                install_path = _resolve_wine_path(prefix_dir, raw_path)

            # 搜索可执行文件
            executable = None
            if install_path and install_path.is_dir():
                for name in game_info.executable_names:
                    candidate = install_path / name
                    if candidate.is_file():
                        executable = candidate
                        break

            if executable:
                info.status = GameStatus.INSTALLED
                info.installed = True
                info.install_path = str(install_path)
                info.executable = str(executable)
                info.installed_version = _read_game_version(install_path)
            elif install_path and install_path.is_dir():
                # 目录存在但没有可执行文件 → 部分安装
                has_markers = any(
                    (install_path / m).exists()
                    for m in ("chunk", "staging", "pkg_version", "config.ini")
                )
                if has_markers:
                    info.status = GameStatus.PARTIAL
                    info.install_path = str(install_path)
            else:
                info.status = GameStatus.NOT_INSTALLED

            results.append(info)

        return results

    def _games_for_region(self, region: str) -> list[GameInfo]:
        return [g for g in ALL_GAMES.values() if g.region.value == region]

    def detect_all(self) -> list[GameInstallInfo]:
        """检测所有区域的游戏安装状态"""
        results: list[GameInstallInfo] = []
        results.extend(
            self._detect_games_in_prefix(self.cn_prefix, MIHOYO_LAUNCHER_CONFIG, "cn")
        )
        results.extend(
            self._detect_games_in_prefix(self.global_prefix, HOYOPLAY_LAUNCHER_CONFIG, "global")
        )
        return results

    def find_executable(self, game_id: str) -> Path | None:
        """查找指定游戏的可执行文件路径"""
        game_info = ALL_GAMES.get(game_id)
        if game_info is None:
            return None
        region = game_info.region.value
        prefix = self.cn_prefix if region == "cn" else self.global_prefix
        config = MIHOYO_LAUNCHER_CONFIG if region == "cn" else HOYOPLAY_LAUNCHER_CONFIG

        # 先查注册表
        user_reg = prefix / "user.reg"
        try:
            reg_contents = user_reg.read_text(encoding="utf-8", errors="replace")
        except OSError:
            reg_contents = ""

        for _header, values in _registry_sections(reg_contents):
            if values.get("GameBiz", "").casefold() == game_id.casefold():
                raw_path = values.get("GameInstallPath", "")
                if raw_path:
                    install_path = _resolve_wine_path(prefix, raw_path)
                    if install_path and install_path.is_dir():
                        for name in game_info.executable_names:
                            exe = install_path / name
                            if exe.is_file():
                                return exe
        return None

    def find_launcher(self, region: str) -> Path | None:
        """查找官方启动器可执行文件"""
        if region == "cn":
            return _find_launcher_executable(self.cn_prefix, MIHOYO_LAUNCHER_CONFIG["executable_candidates"])
        return _find_launcher_executable(self.global_prefix, HOYOPLAY_LAUNCHER_CONFIG["executable_candidates"])
