"""
游戏启动器 — 生成 Steam 快捷方式配置

两种启动方式:
  1. 已安装的启动器/游戏 → 返回 Steam 快捷方式配置（exe + args + proton_tool）
  2. 安装器 → 通过 launcher.py 脚本直接启动（设置 Wine 前缀环境变量）

launcher.py 脚本由 Steam 快捷方式调用，内部使用 umu-run 启动 Windows 程序。
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .compatibility import CompatibilityManager
from .detector import GameDetector
from .games import ALL_GAMES, MIHOYO_LAUNCHER_CONFIG, HOYOPLAY_LAUNCHER_CONFIG
from .models import JsonObject


class GameLauncher:
    """管理游戏启动流程 — 全部走 Steam 非Steam快捷方式"""

    def __init__(self, data_dir) -> None:
        self.data_dir = Path(data_dir)
        self.compatibility = CompatibilityManager(self.data_dir)
        self.detector = GameDetector(data_dir)

    def _get_proton(self, region: str, game_id: str = "launcher") -> tuple[str, Path] | None:
        return self.compatibility.selected_proton(region, game_id)

    def _prefix(self, region: str, game_id: str) -> Path:
        if region == "cn":
            return self.data_dir / "prefixes" / "mihoyo-cn"
        return self.data_dir / "prefixes" / "hoyoplay-global" / game_id

    def _download_installer(self, region: str) -> dict[str, Any]:
        """下载官方安装器（如果不存在）"""
        import ssl
        import tempfile

        SYSTEM_CA_FILES = ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt", "/etc/pki/tls/certs/ca-bundle.crt")

        def _ssl_ctx():
            for c in SYSTEM_CA_FILES:
                if Path(c).is_file():
                    return ssl.create_default_context(cafile=c)
            return ssl.create_default_context()

        config = MIHOYO_LAUNCHER_CONFIG if region == "cn" else HOYOPLAY_LAUNCHER_CONFIG
        installer_dir = self.data_dir / "installers"
        installer = installer_dir / f"{config['provider_id']}-setup.exe"

        if installer.is_file():
            return {"success": True, "path": str(installer)}

        installer_dir.mkdir(parents=True, exist_ok=True)
        url = config["installer_url"]

        # 用 urllib + 系统 CA 证书下载（SteamOS 兼容）
        try:
            import urllib.request
            request = urllib.request.Request(url, headers={"User-Agent": "HoYoDeck/1.0"})
            with urllib.request.urlopen(request, timeout=120, context=_ssl_ctx()) as response:
                fd, tmp = tempfile.mkstemp(prefix=".hoyodeck-installer-", dir=installer_dir)
                staged = Path(tmp)
                with os.fdopen(fd, "wb") as f:
                    while chunk := response.read(1024 * 1024):
                        f.write(chunk)
                    f.flush()
                    os.fsync(f.fileno())
            if staged.exists() and staged.stat().st_size > 1024:
                os.replace(staged, installer)
                return {"success": True, "path": str(installer)}
        except Exception:
            pass
        finally:
            if staged and staged.exists():
                staged.unlink(missing_ok=True)

        return {"success": False, "error": f"下载失败，请手动下载安装包到 {installer_dir}"}

    def get_game_shortcut_config(self, game_id: str) -> dict[str, Any]:
        """获取游戏的 Steam 快捷方式配置"""
        game_info = ALL_GAMES.get(game_id)
        if game_info is None:
            return {"success": False, "error": f"未知游戏: {game_id}"}

        executable = self.detector.find_executable(game_id)
        if executable is None:
            return {"success": False, "error": "游戏未安装或找不到可执行文件，请先通过官方启动器安装"}

        proton = self._get_proton(game_info.region.value, game_id)
        if proton is None:
            return {"success": False, "error": "未找到可用的 Proton 兼容层，请先在环境检查中安装"}

        proton_name, proton_path = proton
        prefix = self._prefix(game_info.region.value, game_id)
        prefix.mkdir(parents=True, exist_ok=True)

        umu = self.compatibility.umu_executable
        if umu.is_file():
            exe = str(umu)
            start_dir = str(executable.parent)
            launch_args = f'"{executable}"'
        else:
            exe = str(proton_path / "proton")
            start_dir = str(executable.parent)
            launch_args = f'waitforexitandrun "{executable}"'

        return {
            "success": True,
            "game_id": game_id,
            "title": game_info.title,
            "exe": exe,
            "start_dir": start_dir,
            "launch_args": launch_args,
            "proton_tool": proton_name,
            "prefix": str(prefix),
            "executable": str(executable),
        }

    def get_installer_shortcut_config(self, region: str) -> dict[str, Any]:
        """获取启动器的启动配置（已安装则走 Steam 快捷方式，未安装则直接启动安装器）"""
        config = MIHOYO_LAUNCHER_CONFIG if region == "cn" else HOYOPLAY_LAUNCHER_CONFIG
        prefix = self.data_dir / "prefixes" / config["prefix_name"]
        prefix.mkdir(parents=True, exist_ok=True)

        proton = self._get_proton(region, "launcher")
        if proton is None:
            return {"success": False, "error": "未找到可用的 Proton 兼容层，请先在环境检查中安装"}

        proton_name, proton_path = proton

        # 检查启动器是否已安装
        installed_launcher = self.detector.find_launcher(region)

        if installed_launcher is not None:
            # 已安装 → 返回 Steam 快捷方式配置
            umu = self.compatibility.umu_executable
            if umu.is_file():
                exe = str(umu)
                start_dir = str(installed_launcher.parent)
                launch_args = f'"{installed_launcher}"'
            else:
                exe = str(proton_path / "proton")
                start_dir = str(installed_launcher.parent)
                launch_args = f'waitforexitandrun "{installed_launcher}"'

            return {
                "success": True,
                "title": config["display_name"],
                "exe": exe,
                "start_dir": start_dir,
                "launch_args": launch_args,
                "proton_tool": proton_name,
                "prefix": str(prefix),
                "is_installed": True,
            }

        # 未安装 → 下载安装包并通过 UMU 直接启动（不走 Steam 快捷方式）
        dl = self._download_installer(region)
        if not dl["success"]:
            return dl

        installer = Path(dl["path"])

        # 通过 UMU 直接启动安装器，设置正确的环境变量
        umu = self.compatibility.umu_executable
        if not umu.is_file():
            return {"success": False, "error": "UMU 未安装，请先在环境检查中安装"}

        env = os.environ.copy()
        env.update({
            "WINEPREFIX": str(prefix),
            "GAMEID": "umu-default",
            "STORE": "none",
            "PROTONPATH": str(proton_path),
            "PROTON_VERB": "waitforexitandrun",
        })

        try:
            process = subprocess.Popen(
                [str(umu), str(installer)],
                env=env,
                cwd=str(installer.parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return {
                "success": True,
                "title": f"{config['display_name']} 安装器",
                "pid": process.pid,
                "is_installed": False,
                "launched_directly": True,
            }
        except Exception as e:
            return {"success": False, "error": f"启动安装器失败: {e}"}
