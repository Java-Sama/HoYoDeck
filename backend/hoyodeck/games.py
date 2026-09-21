"""
米哈游游戏注册表 — 硬编码的游戏元数据

设计说明:
  所有游戏信息（ID、标题、区域、启动器配置）均硬编码于此。
  installer_url 使用米哈游官方 CDN，版本号需手动更新。
  新增游戏只需在下方添加 GameInfo 实例并注册到 ALL_GAMES。
"""
from __future__ import annotations

from .models import GameInfo, GameRegion

# ─── 国服游戏 ─────────────────────────────────────────────
GENSHIN_CN = GameInfo(
    game_id="hk4e_cn",
    title="原神",
    region=GameRegion.CN,
    executable_names=("YuanShen.exe",),
    icon_color_start="#2476b8",
    icon_color_end="#73c6d9",
)

STAR_RAIL_CN = GameInfo(
    game_id="hkrpg_cn",
    title="崩坏：星穹铁道",
    region=GameRegion.CN,
    executable_names=("StarRail.exe",),
    icon_color_start="#28235f",
    icon_color_end="#7c63c8",
)

ZZZ_CN = GameInfo(
    game_id="nap_cn",
    title="绝区零",
    region=GameRegion.CN,
    executable_names=("ZenlessZoneZero.exe",),
    icon_color_start="#242729",
    icon_color_end="#c9d52a",
)

HONKAI3_CN = GameInfo(
    game_id="bh3_cn",
    title="崩坏3",
    region=GameRegion.CN,
    executable_names=("BH3.exe",),
    icon_color_start="#3150a8",
    icon_color_end="#ca75b9",
)

# ─── 国际服游戏 ───────────────────────────────────────────
GENSHIN_GLOBAL = GameInfo(
    game_id="hk4e_global",
    title="Genshin Impact",
    region=GameRegion.GLOBAL,
    executable_names=("GenshinImpact.exe",),
    icon_color_start="#2476b8",
    icon_color_end="#73c6d9",
)

STAR_RAIL_GLOBAL = GameInfo(
    game_id="hkrpg_global",
    title="Honkai: Star Rail",
    region=GameRegion.GLOBAL,
    executable_names=("StarRail.exe",),
    icon_color_start="#28235f",
    icon_color_end="#7c63c8",
)

ZZZ_GLOBAL = GameInfo(
    game_id="nap_global",
    title="Zenless Zone Zero",
    region=GameRegion.GLOBAL,
    executable_names=("ZenlessZoneZero.exe",),
    icon_color_start="#242729",
    icon_color_end="#c9d52a",
)

HONKAI3_GLOBAL = GameInfo(
    game_id="bh3_global",
    title="Honkai Impact 3rd",
    region=GameRegion.GLOBAL,
    executable_names=("BH3.exe",),
    icon_color_start="#3150a8",
    icon_color_end="#ca75b9",
)

# ─── 启动器配置 ───────────────────────────────────────────

MIHOYO_LAUNCHER_CONFIG = {
    "provider_id": "mihoyo_cn",
    "display_name": "米哈游启动器（国服）",
    "region": "cn",
    "installer_url": "https://hyp-webstatic.mihoyo.com/hyp-client/hyp_cn_setup_1.1.4.exe",
    "prefix_name": "mihoyo-cn",
    "executable_candidates": (
        "drive_c/Program Files/miHoYo Launcher/launcher.exe",
        "drive_c/Program Files/miHoYo Launcher/launcher_main.exe",
        "drive_c/Program Files (x86)/miHoYo Launcher/launcher.exe",
    ),
}

HOYOPLAY_LAUNCHER_CONFIG = {
    "provider_id": "hoyoplay_global",
    "display_name": "HoYoPlay (Global)",
    "region": "global",
    "installer_url": "https://hyp-webstatic.hoyoverse.com/hyp-client/hyp_global_setup_1.0.5.exe",
    "prefix_name": "hoyoplay-global",
    "executable_candidates": (
        "drive_c/Program Files/HoYoPlay/launcher.exe",
        "drive_c/Program Files/HoYoPlay/launcher_main.exe",
        "drive_c/Program Files (x86)/HoYoPlay/launcher.exe",
    ),
}

# ─── 游戏查找表 ───────────────────────────────────────────

ALL_GAMES: dict[str, GameInfo] = {
    g.game_id: g for g in (
        GENSHIN_CN, STAR_RAIL_CN, ZZZ_CN, HONKAI3_CN,
        GENSHIN_GLOBAL, STAR_RAIL_GLOBAL, ZZZ_GLOBAL, HONKAI3_GLOBAL,
    )
}

CN_GAMES = [GENSHIN_CN, STAR_RAIL_CN, ZZZ_CN, HONKAI3_CN]
GLOBAL_GAMES = [GENSHIN_GLOBAL, STAR_RAIL_GLOBAL, ZZZ_GLOBAL, HONKAI3_GLOBAL]

# 官方 CDN 封面图 URL 模式
ARTWORK_CDN = {
    "hk4e_cn": "https://upload-bbs.mihoyo.com/upload/ys-oversea/2024/01/15/283761964/8f1c1b1e7c6b4a3d9e0f2a5b8c7d6e4f_460_215.jpg",
    "hk4e_global": "https://fastcdn.hoyoverse.com/content-v2/hk4e/100478/023d12e3e5c54338b65b9fa32d84f6bd_460_215.jpg",
}
