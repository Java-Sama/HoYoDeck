"""
Steam 快捷方式管理 — 读写 shortcuts.vdf 二进制格式

VDF 格式说明:
  Steam 的 shortcuts.vdf 是二进制格式，非 JSON。
  此模块实现了完整的读写器，支持增删查改。

数据路径:
  ~/.steam/steam/userdata/{user_id}/config/shortcuts.vdf

注意事项:
  Steam 可能有多个用户目录，此模块会遍历所有用户。
  写入时使用原子替换（tempfile + os.replace）防止数据损坏。
"""
from __future__ import annotations

import os
import struct
import shutil
from pathlib import Path
from typing import Any

from .models import JsonObject


def _find_steam_userdata_dirs() -> list[Path]:
    """查找 Steam userdata 目录"""
    home = Path.home()
    candidates = [
        home / ".local" / "share" / "Steam" / "userdata",
        home / ".steam" / "steam" / "userdata",
    ]
    for path in candidates:
        if path.is_dir():
            return list(path.iterdir()) if any(path.iterdir()) else []
    return []


def _read_shortcuts_vdf(path: Path) -> dict[int, dict[str, Any]]:
    """读取 shortcuts.vdf 二进制文件"""
    shortcuts: dict[int, dict[str, Any]] = {}
    try:
        data = path.read_bytes()
    except OSError:
        return shortcuts

    pos = 0
    index = 0

    def read_byte() -> int:
        nonlocal pos
        if pos >= len(data):
            return 0
        val = data[pos]
        pos += 1
        return val

    def read_string() -> str:
        nonlocal pos
        parts = []
        while pos < len(data) and data[pos] != 0:
            parts.append(chr(data[pos]))
            pos += 1
        pos += 1  # skip null terminator
        return "".join(parts)

    def read_int() -> int:
        nonlocal pos
        if pos + 4 > len(data):
            return 0
        val = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        return val

    def skip_until_end() -> dict[str, Any]:
        nonlocal pos
        entry: dict[str, Any] = {}
        while pos < len(data):
            type_byte = read_byte()
            if type_byte == 0x08:  # end of table
                break
            name = read_string()
            if type_byte == 0x01:  # string
                entry[name] = read_string()
            elif type_byte == 0x02:  # int32
                entry[name] = read_int()
            else:
                # unknown type, try to skip
                break
        return entry

    # Skip header
    if data and data[0] == 0x00:
        pos = 1
        header_name = read_string()
        if header_name != "shortcuts":
            return shortcuts

    while pos < len(data):
        type_byte = read_byte()
        if type_byte == 0x08:  # end of table
            break
        if type_byte != 0x00:  # expect sub-table
            break
        key = read_string()
        entry = skip_until_end()
        if entry:
            shortcuts[index] = entry
            index += 1

    return shortcuts


def _write_shortcuts_vdf(path: Path, shortcuts: dict[int, dict[str, Any]]) -> None:
    """写入 shortcuts.vdf 二进制文件"""
    parts: list[bytes] = []

    def write_byte(val: int) -> None:
        parts.append(struct.pack("B", val))

    def write_string(name: str, value: str) -> None:
        write_byte(0x01)
        parts.append(name.encode("utf-8") + b"\x00")
        parts.append(value.encode("utf-8") + b"\x00")

    def write_int(name: str, value: int) -> None:
        write_byte(0x02)
        parts.append(name.encode("utf-8") + b"\x00")
        parts.append(struct.pack("<I", value))

    write_byte(0x00)
    parts.append(b"shortcuts\x00")

    for _index, entry in sorted(shortcuts.items()):
        write_byte(0x00)
        parts.append(f"{_index}\x00".encode("utf-8"))
        for key, value in entry.items():
            if isinstance(value, str):
                write_string(key, value)
            elif isinstance(value, int):
                write_int(key, value)
        write_byte(0x08)
    write_byte(0x08)

    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_suffix(".vdf.new")
    staged.write_bytes(b"".join(parts))
    os.replace(staged, path)


def _generate_shortcut(
    name: str,
    exe: str,
    start_dir: str,
    launch_options: str,
    icon: str = "",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """生成一个快捷方式条目"""
    entry: dict[str, Any] = {
        "appid": 0,
        "AppName": name,
        "Exe": f'"{exe}"',
        "StartDir": f'"{start_dir}"',
        "LaunchOptions": launch_options,
        "ShortcutPath": "",
        "IsHidden": 0,
        "AllowDesktopConfig": 1,
        "OpenVR": 0,
        "Devkit": 0,
        "DevkitGameID": "",
        "DevkitOverrideAppID": 0,
        "LastPlayTime": 0,
        "FlatpakAppID": "",
        "icon": icon,
        "IsGame": 1,
    }
    if tags:
        for i, tag in enumerate(tags):
            entry[f"tags_{i}"] = tag
    return entry


class SteamShortcutManager:
    """管理 Steam 非游戏快捷方式"""

    PLUGIN_ENTRY = "/usr/bin/python3"
    PLUGIN_DIR = str(Path.home() / "homebrew/plugins/hoyodeck")

    def __init__(self) -> None:
        self._userdata_dirs = _find_steam_userdata_dirs()

    def _shortcuts_path(self, user_dir: Path) -> Path:
        return user_dir / "config" / "shortcuts.vdf"

    def list_shortcuts(self) -> dict[int, dict[str, Any]]:
        """合并所有用户的快捷方式"""
        all_shortcuts: dict[int, dict[str, Any]] = {}
        for user_dir in self._userdata_dirs:
            path = self._shortcuts_path(user_dir)
            if path.is_file():
                shortcuts = _read_shortcuts_vdf(path)
                all_shortcuts.update(shortcuts)
        return all_shortcuts

    def find_shortcut_by_game_id(self, game_id: str) -> tuple[Path, int, dict[str, Any]] | None:
        """根据 game_id 查找已有的快捷方式"""
        for user_dir in self._userdata_dirs:
            path = self._shortcuts_path(user_dir)
            if not path.is_file():
                continue
            shortcuts = _read_shortcuts_vdf(path)
            for idx, entry in shortcuts.items():
                options = entry.get("LaunchOptions", "")
                if game_id in options:
                    return path, idx, entry
        return None

    def add_shortcut(
        self,
        game_id: str,
        title: str,
        exe: str,
        start_dir: str,
        launch_options: str,
        icon: str = "",
    ) -> int | None:
        """添加非 Steam 游戏快捷方式，返回 AppID"""
        if not self._userdata_dirs:
            return None

        user_dir = self._userdata_dirs[0]
        path = self._shortcuts_path(user_dir)
        shortcuts = _read_shortcuts_vdf(path) if path.is_file() else {}

        # 检查是否已存在
        for idx, entry in shortcuts.items():
            if game_id in entry.get("LaunchOptions", ""):
                # 更新现有条目
                entry["AppName"] = title
                entry["Exe"] = f'"{exe}"'
                entry["StartDir"] = f'"{start_dir}"'
                entry["LaunchOptions"] = launch_options
                if icon:
                    entry["icon"] = icon
                _write_shortcuts_vdf(path, shortcuts)
                return entry.get("appid", 0)

        # 添加新条目
        new_idx = max(shortcuts.keys(), default=-1) + 1
        shortcuts[new_idx] = _generate_shortcut(
            name=title,
            exe=exe,
            start_dir=start_dir,
            launch_options=launch_options,
            icon=icon,
            tags=["hoyodeck", "mihoyo"],
        )
        _write_shortcuts_vdf(path, shortcuts)
        return shortcuts[new_idx].get("appid", 0)

    def remove_shortcut(self, game_id: str) -> bool:
        """移除指定游戏的快捷方式"""
        result = self.find_shortcut_by_game_id(game_id)
        if result is None:
            return False
        path, idx, _entry = result
        shortcuts = _read_shortcuts_vdf(path)
        if idx in shortcuts:
            del shortcuts[idx]
            # 重新编号
            reindexed = dict(enumerate(shortcuts.values()))
            _write_shortcuts_vdf(path, reindexed)
            return True
        return False

    def create_game_shortcut(self, game_id: str, title: str, region: str) -> int | None:
        """为米哈游游戏创建标准快捷方式"""
        launch_options = f'--provider {region} --game-id "{game_id}"'
        return self.add_shortcut(
            game_id=game_id,
            title=title,
            exe=self.PLUGIN_ENTRY,
            start_dir=self.PLUGIN_DIR,
            launch_options=f'"backend/launcher.py" {launch_options}',
        )
