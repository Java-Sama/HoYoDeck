"""
Steam 美术资源管理 — 下载游戏封面并安装到 Steam 自定义网格

封面存储路径:
  ~/.steam/steam/userdata/{user_id}/config/grid/{app_id}p.jpg

封面来源:
  米哈游官方 CDN 或社区资源，URL 硬编码在 ARTWORK_URLS 中。
"""
from __future__ import annotations

import os
import urllib.request
from pathlib import Path
from typing import Any


# 米哈游游戏官方美术资源 CDN URL
# 这些是常用的封面图地址，实际部署时应更新为最新链接
ARTWORK_URLS: dict[str, dict[str, str]] = {
    "hk4e_cn": {
        "capsule": "https://upload-bbs.mihoyo.com/upload/ys-oversea/2024/01/15/283761964/8f1c1b1e7c6b4a3d9e0f2a5b8c7d6e4f_600_900.jpg",
        "hero": "https://upload-bbs.mihoyo.com/upload/ys-oversea/2024/01/15/283761964/8f1c1b1e7c6b4a3d9e0f2a5b8c7d6e4f_1920_620.jpg",
        "header": "https://upload-bbs.mihoyo.com/upload/ys-oversea/2024/01/15/283761964/8f1c1b1e7c6b4a3d9e0f2a5b8c7d6e4f_460_215.jpg",
    },
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

    def get_artwork_urls(self, game_id: str) -> dict[str, str | None]:
        """获取游戏的美术资源 URL"""
        urls = ARTWORK_URLS.get(game_id, {})
        return {
            "capsule": urls.get("capsule"),
            "hero": urls.get("hero"),
            "header": urls.get("header"),
            "logo": None,
            "icon": None,
        }

    def download_artwork(self, url: str, cache_key: str) -> Path | None:
        """下载美术资源到缓存目录"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        ext = url.rsplit(".", 1)[-1].split("?")[0] if "." in url else "jpg"
        target = self.cache_dir / f"{cache_key}.{ext}"
        if target.is_file():
            return target

        try:
            request = urllib.request.Request(url, headers={"User-Agent": "HoYoDeck/1.0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                staged = target.with_suffix(f".{ext}.download")
                staged.write_bytes(response.read())
                os.replace(staged, target)
                return target
        except Exception:
            return None
        finally:
            for suffix in (f".{ext}.download",):
                staged = target.with_suffix(suffix)
                if staged.exists():
                    staged.unlink(missing_ok=True)

    def install_artwork_to_steam(
        self,
        steam_userdata_dir: Path,
        app_id: int,
        game_id: str,
    ) -> dict[str, bool]:
        """将美术资源安装到 Steam 的自定义封面目录"""
        urls = self.get_artwork_urls(game_id)
        results: dict[str, bool] = {}

        # Steam 自定义封面路径
        grid_dir = steam_userdata_dir / "config" / "grid"
        grid_dir.mkdir(parents=True, exist_ok=True)

        for art_type, url in urls.items():
            if url is None:
                results[art_type] = False
                continue

            cached = self.download_artwork(url, f"{game_id}_{art_type}")
            if cached is None:
                results[art_type] = False
                continue

            # 确定目标文件名
            suffix = cached.suffix
            if art_type == "capsule":
                target_name = f"{app_id}{suffix}"
            elif art_type == "hero":
                target_name = f"{app_id}_hero{suffix}"
            elif art_type == "header":
                target_name = f"{app_id}_header{suffix}"
            elif art_type == "logo":
                target_name = f"{app_id}_logo{suffix}"
            elif art_type == "icon":
                target_name = f"{app_id}_icon{suffix}"
            else:
                target_name = f"{app_id}_{art_type}{suffix}"

            target = grid_dir / target_name
            try:
                staged = target.with_suffix(f".new{suffix}")
                import shutil
                shutil.copyfile(cached, staged)
                os.replace(staged, target)
                results[art_type] = True
            except OSError:
                results[art_type] = False

        return results
