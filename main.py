"""
HoYoDeck — Decky Loader 插件主入口

架构概览:
  Plugin 类     — Decky 插件生命周期管理，暴露 RPC 方法给前端调用
  后端模块       — backend/hoyodeck/ 下的各模块处理实际业务逻辑
  启动器脚本     — backend/launcher.py 由 Steam 快捷方式直接调用

RPC 方法:
  get_dashboard()          — 获取仪表盘数据（版本、游戏统计）
  check_environment()      — 检查运行环境（UMU、Proton、启动器）
  install_component(name)  — 安装/重装指定组件
  get_download_progress()  — 查询下载进度
  get_games()              — 获取游戏列表及安装状态
  launch_game(game_id)     — 获取游戏的 Steam 快捷方式配置
  launch_installer(region) — 获取安装器的快捷方式配置
  add_to_steam(game_id)    — 添加游戏到 Steam 库
  remove_from_steam()      — 从 Steam 库移除
  refresh_artwork()        — 刷新游戏封面
  cleanup_environment()    — 移除插件环境
  cleanup_all()            — 移除环境 + 游戏 + 快捷方式
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import decky

# 确保插件根目录在 sys.path 中
PLUGIN_ROOT = os.path.dirname(os.path.abspath(__file__))
if PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, PLUGIN_ROOT)

from backend.hoyodeck.artwork import ArtworkManager
from backend.hoyodeck.compatibility import CompatibilityManager
from backend.hoyodeck.detector import GameDetector
from backend.hoyodeck.games import ALL_GAMES, CN_GAMES, GLOBAL_GAMES, MIHOYO_LAUNCHER_CONFIG, HOYOPLAY_LAUNCHER_CONFIG
from backend.hoyodeck.launcher import GameLauncher
from backend.hoyodeck.models import Dashboard, GameInstallInfo, RuntimeStatus
from backend.hoyodeck.steam_shortcuts import SteamShortcutManager


class Plugin:
    """HoYoDeck Decky 插件"""

    async def _main(self) -> None:
        """插件加载时初始化。Decky Loader 在插件启动时自动调用。"""
        self.data_dir = Path(decky.DECKY_USER_HOME) / ".local" / "share" / "hoyodeck"
        self.detector = GameDetector(self.data_dir)
        self.compatibility = CompatibilityManager(self.data_dir)
        self.launcher = GameLauncher(self.data_dir)
        self.shortcuts = SteamShortcutManager()
        self.artwork = ArtworkManager(self.data_dir)
        self._dl_progress = {}  # {component: {pct, downloaded_mb, total_mb, status}}
        decky.logger.info("HoYoDeck 插件已加载")

    async def _unload(self) -> None:
        """插件卸载时清理。Decky Loader 在插件关闭时自动调用。"""
        decky.logger.info("HoYoDeck 插件已卸载")

    # ─── 仪表盘 ────────────────────────────────────────────

    async def get_dashboard(self) -> dict:
        """获取主面板状态"""
        decky.logger.info("get_dashboard 被调用")
        try:
            runtime = self.compatibility.get_status()
            games = self.detector.detect_all()
            installed_count = sum(1 for g in games if g.installed)

            dashboard = Dashboard(
                version="1.0.0",
                game_count=len(games),
                installed_count=installed_count,
                runtime=runtime,
                games=games,
            )
            result = dashboard.to_dict()
            decky.logger.info(f"get_dashboard 返回: games={len(games)}, runtime_ready={runtime.ready}")
            return result
        except Exception as e:
            decky.logger.exception(f"get_dashboard 异常: {e}")
            raise

    # ─── 兼容层 ────────────────────────────────────────────

    async def get_runtime_status(self) -> dict:
        """获取兼容层状态"""
        return self.compatibility.get_status().to_dict()

    async def check_environment(self) -> dict:
        """环境检查：逐项检测"""
        import shutil as sh
        from pathlib import Path as P
        umu_path = sh.which("umu-run") or str(self.compatibility.umu_executable)
        umu_ok = self.compatibility.umu_executable.is_file() or sh.which("umu-run") is not None
        proton_layers = self.compatibility.detect_proton_layers()
        steam_dir = P.home() / ".local" / "share" / "Steam" / "compatibilitytools.d"

        # 检查启动器状态
        cn_launcher = self.detector.find_launcher("cn")
        global_launcher = self.detector.find_launcher("global")

        # 检查安装包是否已下载
        installer_dir = P(self.data_dir) / "installers"
        cn_installer_exists = (installer_dir / f"{MIHOYO_LAUNCHER_CONFIG['provider_id']}-setup.exe").is_file()
        global_installer_exists = (installer_dir / f"{HOYOPLAY_LAUNCHER_CONFIG['provider_id']}-setup.exe").is_file()

        def _launcher_detail(installed, installer_exists):
            if installed:
                return "已安装"
            if installer_exists:
                return "已下载，点游戏卡片安装"
            return "未安装"

        return {
            "umu": {
                "name": "UMU Runtime",
                "ready": umu_ok,
                "detail": umu_path if umu_ok else "未安装",
            },
            "proton": {
                "name": "Proton 兼容层",
                "ready": len(proton_layers) > 0,
                "detail": ", ".join(l["name"] for l in proton_layers) if proton_layers else "未安装",
                "count": len(proton_layers),
            },
            "launcher_cn": {
                "name": "国服启动器",
                "ready": cn_launcher is not None,
                "detail": _launcher_detail(cn_launcher is not None, cn_installer_exists),
            },
            "launcher_global": {
                "name": "国际服启动器",
                "ready": global_launcher is not None,
                "detail": _launcher_detail(global_launcher is not None, global_installer_exists),
            },
            "steam_compat_dir": {
                "name": "Steam 兼容工具目录",
                "ready": steam_dir.is_dir(),
                "detail": str(steam_dir),
            },
        }

    async def install_component(self, component: str) -> dict:
        """安装/重装指定组件（下载类任务放线程，不阻塞 RPC）"""
        import threading
        decky.logger.info(f"install_component 被调用: {component}")
        try:
            if component == "umu":
                ok = self.compatibility.install_umu()
                if ok:
                    return {"success": True, "detail": "UMU 安装成功"}
                return {"success": False, "detail": "UMU 安装失败，请手动安装"}
            elif component == "proton":
                ok = self.compatibility.install_proton()
                if ok:
                    layers = self.compatibility.detect_proton_layers()
                    return {"success": True, "detail": f"Proton 安装成功: {layers[0]['name'] if layers else 'unknown'}"}
                return {"success": False, "detail": "Proton 安装失败，请手动下载"}
            elif component in ("launcher", "launcher_cn", "launcher_global"):
                region = component.replace("launcher_", "") or "cn"
                config = MIHOYO_LAUNCHER_CONFIG if region == "cn" else HOYOPLAY_LAUNCHER_CONFIG
                installer = Path(self.data_dir) / "installers" / f"{config['provider_id']}-setup.exe"
                if installer.is_file():
                    return {"success": True, "detail": f"官方启动器已存在 ({installer.name})"}
                self._dl_progress[component] = {"pct": 0, "downloaded_mb": 0, "total_mb": 0, "status": "downloading"}
                threading.Thread(target=self._download_launcher_sync, args=(region, component), daemon=True).start()
                return {"success": True, "detail": "开始下载，请等待..."}
            else:
                return {"success": False, "detail": f"未知组件: {component}"}
        except Exception as e:
            decky.logger.exception(f"install_component 异常: {component}")
            return {"success": False, "detail": str(e)}

    def _download_launcher_sync(self, region: str, component: str) -> None:
        """同步下载启动器（后台线程）"""
        import ssl
        import tempfile

        ca_files = ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt", "/etc/pki/tls/certs/ca-bundle.crt")
        ctx = None
        for c in ca_files:
            if Path(c).is_file():
                ctx = ssl.create_default_context(cafile=c)
                break
        if ctx is None:
            ctx = ssl.create_default_context()

        config = MIHOYO_LAUNCHER_CONFIG if region == "cn" else HOYOPLAY_LAUNCHER_CONFIG
        installer_dir = Path(self.data_dir) / "installers"
        installer_dir.mkdir(parents=True, exist_ok=True)
        installer = installer_dir / f"{config['provider_id']}-setup.exe"
        url = config["installer_url"]

        try:
            decky.logger.info(f"下载官方启动器: {url}")
            import urllib.request
            request = urllib.request.Request(url, headers={"User-Agent": "HoYoDeck/1.0"})
            with urllib.request.urlopen(request, timeout=300, context=ctx) as response:
                total = int(response.headers.get("Content-Length", 0))
                total_mb = round(total / 1024 / 1024, 1) if total else 0
                fd, tmp = tempfile.mkstemp(prefix=".hoyodeck-launcher-", dir=installer_dir)
                staged = Path(tmp)
                downloaded = 0
                with os.fdopen(fd, "wb") as f:
                    while chunk := response.read(256 * 1024):
                        f.write(chunk)
                        downloaded += len(chunk)
                        pct = int(downloaded * 100 / total) if total else 0
                        self._dl_progress[component] = {
                            "pct": pct,
                            "downloaded_mb": round(downloaded / 1024 / 1024, 1),
                            "total_mb": total_mb,
                            "status": "downloading",
                        }
                    f.flush()
                    os.fsync(f.fileno())
            if staged.exists() and staged.stat().st_size > 1024:
                os.replace(staged, installer)
                self._dl_progress[component] = {"pct": 100, "downloaded_mb": total_mb, "total_mb": total_mb, "status": "done"}
                decky.logger.info(f"官方启动器下载完成: {installer}")
            else:
                staged.unlink(missing_ok=True)
                self._dl_progress[component] = {"pct": 0, "downloaded_mb": 0, "total_mb": 0, "status": "error", "error": "文件太小"}
        except Exception as e:
            decky.logger.exception("下载官方启动器失败")
            self._dl_progress[component] = {"pct": 0, "downloaded_mb": 0, "total_mb": 0, "status": "error", "error": str(e)}

    async def get_download_progress(self, component: str) -> dict:
        """查询下载进度"""
        return self._dl_progress.get(component, {"pct": 0, "status": "idle"})

    async def prepare_compatibility(self) -> dict:
        """安装/准备兼容层"""
        decky.logger.info("prepare_compatibility 被调用")
        try:
            status = self.compatibility.prepare()
            decky.logger.info(f"prepare_compatibility 完成: ready={status.ready}, umu={status.umu_installed}, proton_layers={len(status.proton_layers)}")
            if not status.umu_installed:
                return {"error": "UMU 安装失败，请手动安装: sudo pacman -S umu-launcher 或 pip install umu-launcher"}
            if len(status.proton_layers) == 0:
                return {"error": "Proton 安装失败。请手动下载 GE-Proton 并解压到 ~/.local/share/Steam/compatibilitytools.d/"}
            return status.to_dict()
        except Exception as e:
            decky.logger.exception("准备兼容层失败")
            return {"error": str(e)}

    # ─── 游戏管理 ──────────────────────────────────────────

    async def get_games(self) -> list[dict]:
        """获取所有游戏列表"""
        games = self.detector.detect_all()
        result = []
        for g in games:
            d = g.to_dict()
            d["artwork_urls"] = self.artwork.get_artwork_urls(g.game_id)
            result.append(d)
        return result

    async def get_game_details(self, game_id: str) -> dict:
        """获取单个游戏详情"""
        games = self.detector.detect_all()
        for game in games:
            if game.game_id == game_id:
                result = game.to_dict()
                result["artwork_urls"] = self.artwork.get_artwork_urls(game_id)
                return result
        return {"error": f"未知游戏: {game_id}"}

    async def refresh_game_status(self, game_id: str) -> dict:
        """刷新单个游戏状态"""
        return await self.get_game_details(game_id)

    # ─── Steam 快捷方式 ────────────────────────────────────

    async def add_to_steam(self, game_id: str) -> dict:
        """将游戏添加到 Steam 库"""
        game_info = ALL_GAMES.get(game_id)
        if game_info is None:
            return {"success": False, "error": f"未知游戏: {game_id}"}

        try:
            app_id = self.shortcuts.create_game_shortcut(
                game_id=game_id,
                title=game_info.title,
                region=game_info.region.value,
            )
            if app_id is not None:
                # 尝试安装美术资源
                userdata_dirs = self.shortcuts._userdata_dirs
                if userdata_dirs:
                    self.artwork.install_artwork_to_steam(
                        userdata_dirs[0], app_id, game_id
                    )
                return {"success": True, "app_id": app_id}
            return {"success": False, "error": "创建快捷方式失败"}
        except Exception as e:
            decky.logger.exception("添加到 Steam 失败")
            return {"success": False, "error": str(e)}

    async def remove_from_steam(self, game_id: str) -> dict:
        """从 Steam 库移除游戏"""
        try:
            removed = self.shortcuts.remove_shortcut(game_id)
            return {"success": removed}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ─── 游戏启动 ──────────────────────────────────────────

    async def launch_game(self, game_id: str) -> dict:
        """获取游戏的 Steam 快捷方式配置"""
        try:
            return self.launcher.get_game_shortcut_config(game_id)
        except Exception as e:
            decky.logger.exception("获取游戏启动配置失败")
            return {"success": False, "error": str(e)}

    async def launch_installer(self, region: str) -> dict:
        """获取安装器的 Steam 快捷方式配置"""
        try:
            return self.launcher.get_installer_shortcut_config(region)
        except Exception as e:
            decky.logger.exception("获取安装器启动配置失败")
            return {"success": False, "error": str(e)}

    # ─── 美术资源 ──────────────────────────────────────────

    async def refresh_artwork(self, game_id: str) -> dict:
        """刷新游戏美术资源"""
        userdata_dirs = self.shortcuts._userdata_dirs
        if not userdata_dirs:
            return {"success": False, "error": "未找到 Steam 用户目录"}

        result = self.shortcuts.find_shortcut_by_game_id(game_id)
        if result is None:
            return {"success": False, "error": "游戏未添加到 Steam"}

        _path, _idx, entry = result
        app_id = entry.get("appid", 0)
        if app_id == 0:
            return {"success": False, "error": "无效的 AppID"}

        installed = self.artwork.install_artwork_to_steam(
            userdata_dirs[0], app_id, game_id
        )
        return {"success": True, "installed": installed}

    # ─── 环境清理 ──────────────────────────────────────────

    async def cleanup_environment(self) -> dict:
        """移除插件安装的环境（UMU、Proton、Wine 前缀、安装包）"""
        import shutil
        data = self.data_dir
        removed = []

        tools = data / "tools"
        if tools.exists():
            shutil.rmtree(tools)
            removed.append("tools")

        prefixes = data / "prefixes"
        if prefixes.exists():
            shutil.rmtree(prefixes)
            removed.append("prefixes")

        installers = data / "installers"
        if installers.exists():
            shutil.rmtree(installers)
            removed.append("installers")

        return {"success": True, "removed": removed, "detail": f"已清理: {', '.join(removed) if removed else '无'}"}

    async def cleanup_all(self) -> dict:
        """移除环境 + 安装的游戏 + Steam 快捷方式"""
        import shutil

        # 先清理 Steam 快捷方式
        games = self.detector.detect_all()
        removed_shortcuts = []
        for game in games:
            if game.has_steam_shortcut:
                try:
                    self.shortcuts.remove_game_shortcut(game.game_id)
                    removed_shortcuts.append(game.title)
                except Exception:
                    pass

        # 再清理整个数据目录
        if self.data_dir.exists():
            shutil.rmtree(self.data_dir)
            self.data_dir.mkdir(parents=True, exist_ok=True)

        # 重建子目录
        for sub in ["tools", "prefixes", "installers"]:
            (self.data_dir / sub).mkdir(exist_ok=True)

        return {
            "success": True,
            "removed_shortcuts": removed_shortcuts,
            "detail": f"已清理全部环境，移除了 {len(removed_shortcuts)} 个 Steam 快捷方式",
        }
