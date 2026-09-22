"""
Steam 美术资源管理 — 下载游戏封面并安装到 Steam 自定义网格

封面存储路径:
  ~/.steam/steam/userdata/{user_id}/config/grid/{app_id}p.jpg

封面来源:
  米哈游官方启动器 API 动态获取美术资源 URL，
  结果缓存在本地 JSON 文件中（24 小时过期）。
  当 API 不可用时回退到硬编码的备用 URL。
"""
from __future__ import annotations

import json
import os
import shutil
import ssl
import time
import urllib.request
from pathlib import Path
from typing import Any


# ─── 启动器 API 配置 ────────────────────────────────────────────
_LAUNCHER_API_PATH = "/hyp/hyp-connect/api/getGames"

# (API 基础 URL, launcher_id) 组合，按优先级排列
_LAUNCHER_CONFIGS: list[tuple[str, str]] = [
    ("https://hyp-api.mihoyo.com", "jGHBHlcOq1"),      # CN 米哈游启动器
    ("https://sg-hyp-api.hoyoverse.com", "VYTpXlbWo8"),  # HoYoPlay Global
]

# launcher API display 字段 → Steam artwork 类型映射
_API_FIELD_MAP: dict[str, str] = {
    "capsule": "thumbnail",   # 600x900 → thumbnail（方形封面）
    "hero": "background",     # 1920x620 → background（宽背景）
    "header": "thumbnail",    # 460x215 → thumbnail（小封面）
    "logo": "logo",           # 1280x360 → logo（透明 logo）
    "icon": "icon",           # 256x256 → icon（小图标）
}

_CACHE_TTL = 86400  # 24 小时


# ─── 硬编码备用 URL（当 API 不可用时使用）─────────────────────────
# CN 游戏：来自 launcher-webstatic.mihoyo.com 官方 CDN
# Global 游戏：来自 fastcdn.hoyoverse.com 官方 CDN
_FALLBACK_URLS: dict[str, dict[str, str]] = {
    # ── 国服 ──
    "hk4e_cn": {
        "capsule": "https://launcher-webstatic.mihoyo.com/launcher-public/2026/03/30/f7efc9377669a4053c92e8a376cfff22_5729908482600033870.png",
        "hero": "https://launcher-webstatic.mihoyo.com/launcher-public/2026/07/22/a36b618a05cc80cb87c2955351abd67b_2358889847008472507.webp",
        "logo": "https://launcher-webstatic.mihoyo.com/launcher-public/2026/03/30/ff975d44eba6e32d449b5112a4b0eaa9_2796941706357054178.png",
        "icon": "https://launcher-webstatic.mihoyo.com/launcher-public/2025/10/14/9ebf1bc5af2d83ca5fca21adb49cf341_1713549758249501746.png",
    },
    "hkrpg_cn": {
        "capsule": "https://launcher-webstatic.mihoyo.com/launcher-public/2024/04/25/c45dd543cc497fd0a8d2e9494cc2d234_6530308602543767965.png",
        "hero": "https://launcher-webstatic.mihoyo.com/launcher-public/2026/08/17/b3811afc4a6a4e7e3879c830329f8ae2_4041979032811000021.webp",
        "logo": "https://launcher-webstatic.mihoyo.com/launcher-public/2026/04/09/8c10964dfd8f0fbac27237527e7ebb7b_7520718333461102699.png",
        "icon": "https://launcher-webstatic.mihoyo.com/launcher-public/2026/05/14/d824123e77e762a0f350df1b560dcad0_8859327557457118203.png",
    },
    "nap_cn": {
        "capsule": "https://launcher-webstatic.mihoyo.com/launcher-public/2026/04/09/5d0c30a75a33603d47ce2951fe01f818_1629932358960850634.jpg",
        "hero": "https://launcher-webstatic.mihoyo.com/launcher-public/2026/08/26/86fa3b52c96b8835f8b7f1f967efac28_8820261911238438183.webp",
        "logo": "https://launcher-webstatic.mihoyo.com/launcher-public/2026/04/09/63f536d767f12f1288b3a0f4bb9e24b0_440224496418550097.png",
        "icon": "https://launcher-webstatic.mihoyo.com/launcher-public/2026/09/02/894b89b5aaea805f6420156c7c07a1a3_1073444568422177775.png",
    },
    "bh3_cn": {
        "capsule": "https://launcher-webstatic.mihoyo.com/launcher-public/2024/04/15/cc7803752504e6b23a9aded8b60596cf_9002191729191829924.png",
        "hero": "https://launcher-webstatic.mihoyo.com/launcher-public/2026/07/16/ffdd42e098046b7bea134907a2ea04b2_352028468613440724.webp",
        "logo": "https://launcher-webstatic.mihoyo.com/launcher-public/2026/04/10/ce3bbd2c7adde87fcabf9c75bca31fbb_9072784838338386061.png",
        "icon": "https://launcher-webstatic.mihoyo.com/launcher-public/2024/12/18/fdc95c839e7c750d41e1c208d8cf1223_156217938794052481.png",
    },
    # ── 国际服 ──
    "hk4e_global": {
        "capsule": "https://fastcdn.hoyoverse.com/content-v2/hk4e/100478/023d12e3e5c54338b65b9fa32d84f6bd_600_900.jpg",
        "hero": "https://fastcdn.hoyoverse.com/content-v2/hk4e/100478/023d12e3e5c54338b65b9fa32d84f6bd_1920_620.jpg",
        "header": "https://fastcdn.hoyoverse.com/content-v2/hk4e/100478/023d12e3e5c54338b65b9fa32d84f6bd_460_215.jpg",
    },
}


class ArtworkManager:
    """管理游戏美术资源下载和安装"""

    STEAM_ARTWORK_TYPES = {
        "capsule": 0,   # 600x900
        "hero": 1,      # 1920x620
        "logo": 2,      # 1280x360
        "header": 3,    # 460x215
        "icon": 4,      # 256x256
    }

    def __init__(self, data_dir) -> None:
        self.data_dir = Path(data_dir)
        self.cache_dir = self.data_dir / "artwork-cache"
        self._urls_cache_file = self.cache_dir / "launcher-urls.json"
        self._urls_cache: dict[str, dict[str, str]] | None = None

    # ─── SSL ─────────────────────────────────────────────────

    @staticmethod
    def _ssl_context() -> ssl.SSLContext:
        """创建 SSL 上下文（SteamOS / Arch Linux 兼容）"""
        for ca in ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt",
                   "/etc/pki/tls/certs/ca-bundle.crt"):
            if Path(ca).is_file():
                return ssl.create_default_context(cafile=ca)
        return ssl.create_default_context()

    # ─── URL 获取（启动器 API + 缓存）─────────────────────────

    def _fetch_from_api(self, api_base: str, launcher_id: str) -> dict[str, dict[str, str]]:
        """从单个启动器 API 获取所有游戏的美术资源 URL"""
        try:
            url = f"{api_base}{_LAUNCHER_API_PATH}?launcher_id={launcher_id}&language=zh-cn"
            req = urllib.request.Request(url, headers={"User-Agent": "HoYoDeck/1.0"})
            with urllib.request.urlopen(req, timeout=15, context=self._ssl_context()) as resp:
                data = json.loads(resp.read())

            if data.get("retcode") != 0:
                return {}

            result: dict[str, dict[str, str]] = {}
            for game in data.get("data", {}).get("games", []):
                biz = game.get("biz", "")
                display = game.get("display", {})
                if not biz or not display:
                    continue

                urls: dict[str, str] = {}
                for art_type, api_field in _API_FIELD_MAP.items():
                    field_data = display.get(api_field)
                    if isinstance(field_data, dict):
                        img_url = field_data.get("url", "")
                        if img_url:
                            urls[art_type] = img_url

                if urls:
                    result[biz] = urls

            return result
        except Exception:
            return {}

    def _ensure_urls_loaded(self) -> dict[str, dict[str, str]]:
        """确保 URL 缓存已加载（内存 → 文件缓存 → API）"""
        if self._urls_cache is not None:
            return self._urls_cache

        # 尝试从缓存文件加载
        if self._urls_cache_file.is_file():
            try:
                with open(self._urls_cache_file) as f:
                    cached = json.load(f)
                if time.time() - cached.get("timestamp", 0) < _CACHE_TTL:
                    self._urls_cache = cached.get("urls", {})
                    return self._urls_cache
            except (json.JSONDecodeError, OSError, KeyError):
                pass

        # 缓存过期或不存在，从 API 刷新
        self._refresh_from_api()
        return self._urls_cache or {}

    def _refresh_from_api(self) -> None:
        """从所有启动器 API 刷新美术资源 URL 并写入缓存文件"""
        combined: dict[str, dict[str, str]] = {}
        for api_base, launcher_id in _LAUNCHER_CONFIGS:
            fetched = self._fetch_from_api(api_base, launcher_id)
            combined.update(fetched)

        self._urls_cache = combined if combined else {}

        if combined:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            try:
                with open(self._urls_cache_file, "w") as f:
                    json.dump({"timestamp": time.time(), "urls": combined}, f, ensure_ascii=False)
            except OSError:
                pass

    def refresh_artwork(self) -> dict[str, int]:
        """强制刷新美术资源 URL（供前端调用）"""
        self._urls_cache = None
        if self._urls_cache_file.is_file():
            self._urls_cache_file.unlink(missing_ok=True)
        self._refresh_from_api()
        return {"games_loaded": len(self._urls_cache or {})}

    def get_artwork_urls(self, game_id: str) -> dict[str, str | None]:
        """获取游戏的美术资源 URL（API/缓存 → 备用 URL）"""
        api_urls = self._ensure_urls_loaded().get(game_id, {})
        fallback = _FALLBACK_URLS.get(game_id, {})

        return {
            art_type: api_urls.get(art_type) or fallback.get(art_type)
            for art_type in ("capsule", "hero", "header", "logo", "icon")
        }

    # ─── 下载 ─────────────────────────────────────────────────

    def download_artwork(self, url: str, cache_key: str) -> Path | None:
        """下载美术资源到缓存目录"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        ext = url.rsplit(".", 1)[-1].split("?")[0] if "." in url else "jpg"
        target = self.cache_dir / f"{cache_key}.{ext}"
        if target.is_file():
            return target

        staged = target.with_suffix(f".{ext}.download")
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "HoYoDeck/1.0"})
            with urllib.request.urlopen(request, timeout=30, context=self._ssl_context()) as response:
                staged.write_bytes(response.read())
                os.replace(staged, target)
                return target
        except Exception:
            return None
        finally:
            if staged.exists():
                staged.unlink(missing_ok=True)

    # ─── 安装到 Steam ─────────────────────────────────────────

    _SUFFIX_MAP = {
        "capsule": "",
        "hero": "_hero",
        "header": "_header",
        "logo": "_logo",
        "icon": "_icon",
    }

    def install_artwork_to_steam(
        self,
        steam_userdata_dir: Path,
        app_id: int,
        game_id: str,
    ) -> dict[str, bool]:
        """将美术资源安装到 Steam 的自定义封面目录"""
        urls = self.get_artwork_urls(game_id)
        results: dict[str, bool] = {}

        grid_dir = steam_userdata_dir / "config" / "grid"
        grid_dir.mkdir(parents=True, exist_ok=True)

        for art_type, url in urls.items():
            if not url:
                results[art_type] = False
                continue

            cached = self.download_artwork(url, f"{game_id}_{art_type}")
            if cached is None:
                results[art_type] = False
                continue

            suffix = cached.suffix
            tag = self._SUFFIX_MAP.get(art_type, f"_{art_type}")
            target = grid_dir / f"{app_id}{tag}{suffix}"

            try:
                staged = target.with_suffix(f".new{suffix}")
                shutil.copyfile(cached, staged)
                os.replace(staged, target)
                results[art_type] = True
            except OSError:
                results[art_type] = False

        return results