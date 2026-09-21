#!/usr/bin/env python3
"""HoYoDeck 启动器脚本 — 由 Steam 快捷方式调用

用法:
    python3 backend/launcher.py --provider cn --game-id installer
    python3 backend/launcher.py --provider cn --game-id launcher
    python3 backend/launcher.py --provider cn --game-id genshin
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# 插件根目录
PLUGIN_ROOT = Path(__file__).resolve().parent.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from backend.hoyodeck.compatibility import CompatibilityManager
from backend.hoyodeck.detector import GameDetector
from backend.hoyodeck.games import MIHOYO_LAUNCHER_CONFIG, HOYOPLAY_LAUNCHER_CONFIG


def main() -> int:
    parser = argparse.ArgumentParser(description="HoYoDeck Game Launcher")
    parser.add_argument("--provider", required=True, choices=["cn", "global"],
                        help="区域: cn=国服, global=国际服")
    parser.add_argument("--game-id", required=True,
                        help="installer, launcher, 或游戏ID (genshin/hsr/zzz/hi3)")
    args = parser.parse_args()

    data_dir = Path.home() / ".local" / "share" / "hoyodeck"
    data_dir.mkdir(parents=True, exist_ok=True)

    config = MIHOYO_LAUNCHER_CONFIG if args.provider == "cn" else HOYOPLAY_LAUNCHER_CONFIG
    prefix = data_dir / "prefixes" / config["prefix_name"]
    prefix.mkdir(parents=True, exist_ok=True)

    # 兼容层（CompatibilityManager 内部会拼接 /tools）
    compatibility = CompatibilityManager(data_dir)
    umu = compatibility.umu_executable
    if not umu.is_file():
        print("UMU 未安装，请先在 HoYoDeck 中安装运行时", file=sys.stderr)
        return 1

    # Proton（优先 DW-Proton，其次 GE-Proton）
    proton = compatibility.selected_proton(config["provider_id"], args.game_id)
    if proton is None:
        print("未找到 Proton 兼容层，请先在 HoYoDeck 中安装", file=sys.stderr)
        return 1

    proton_name, proton_path = proton
    detector = GameDetector(data_dir)

    # 确定要启动的可执行文件
    if args.game_id == "installer":
        installer_name = f"{config['provider_id']}-setup.exe"
        installer = data_dir / "installers" / installer_name
        if not installer.is_file():
            # 自动下载安装包
            print(f"[HoYoDeck] 安装包不存在，开始下载...")
            installer.parent.mkdir(parents=True, exist_ok=True)
            import urllib.request, ssl
            url = config["installer_url"]
            ca_files = ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt", "/etc/pki/tls/certs/ca-bundle.crt")
            ctx = ssl.create_default_context()
            for cf in ca_files:
                if Path(cf).is_file():
                    ctx.load_verify_locations(cf)
                    break
            try:
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=300, context=ctx) as resp:
                    total = int(resp.headers.get("Content-Length", 0))
                    downloaded = 0
                    with open(installer, "wb") as f:
                        while True:
                            chunk = resp.read(1024 * 1024)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total:
                                print(f"\r[HoYoDeck] 下载中: {downloaded*100//total}% ({downloaded//1024//1024}MB/{total//1024//1024}MB)", end="", flush=True)
                print(f"\n[HoYoDeck] 下载完成: {installer}")
            except Exception as e:
                print(f"下载失败: {e}", file=sys.stderr)
                installer.unlink(missing_ok=True)
                return 2
        exe = str(installer)
        work_dir = str(installer.parent)
    elif args.game_id == "launcher":
        launcher = detector.find_launcher(args.provider)
        if launcher is None:
            print("启动器未安装", file=sys.stderr)
            return 3
        exe = str(launcher)
        work_dir = str(launcher.parent)
    else:
        # 具体游戏 → 通过启动器启动
        launcher = detector.find_launcher(args.provider)
        if launcher is None:
            print("启动器未安装，请先安装启动器", file=sys.stderr)
            return 3
        exe = str(launcher)
        work_dir = str(launcher.parent)

    # 设置环境变量
    env = os.environ.copy()
    env.update({
        "WINEPREFIX": str(prefix),
        "GAMEID": "umu-default",
        "STORE": "none",
        "PROTONPATH": str(proton_path),
        "PROTON_VERB": "waitforexitandrun",
        "LANG": "zh_CN.UTF-8",
        "LANGUAGE": "zh_CN:zh",
        "LC_ALL": "zh_CN.UTF-8",
    })

    print(f"[HoYoDeck] 启动: {exe}")
    print(f"[HoYoDeck] 前缀: {prefix}")
    print(f"[HoYoDeck] Proton: {proton_name}")

    # 通过 UMU 启动，保持进程存活直到退出
    result = subprocess.run([str(umu), exe], env=env, cwd=work_dir)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
