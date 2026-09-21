#!/usr/bin/env python3
"""
HoYoDeck 打包脚本

用法:
  python3 scripts/build_plugin_zip.py              # 在线版
  python3 scripts/build_plugin_zip.py --full        # 离线版（含 UMU + GE-Proton）
  python3 scripts/build_plugin_zip.py --both        # 两个都打
  python3 scripts/build_plugin_zip.py --skip-build  # 跳过前端构建
"""
import argparse
import subprocess
import sys
import zipfile
from pathlib import Path

PLUGIN = "hoyodeck"
ROOT = Path(__file__).resolve().parent.parent

REQUIRED = [
    f"{PLUGIN}/dist/index.js",
    f"{PLUGIN}/main.py",
    f"{PLUGIN}/plugin.json",
    f"{PLUGIN}/package.json",
]

INCLUDE_FILES = ["main.py", "plugin.json", "package.json", "README.md", "LICENSE"]
INCLUDE_DIRS = [("backend", [".py"])]


def build_frontend() -> bool:
    print("🔨 构建前端...")
    r = subprocess.run(["pnpm", "run", "build"], cwd=ROOT, capture_output=True)
    if r.returncode != 0:
        print(f"✗ 前端构建失败:\n{r.stderr.decode()}")
        return False
    if not (ROOT / "dist" / "index.js").is_file():
        print("✗ dist/index.js 未生成")
        return False
    print("✓ 前端构建完成")
    return True


def collect(include_vendor: bool) -> list[tuple[str, Path]]:
    entries: list[tuple[str, Path]] = []

    # 前端
    dist = ROOT / "dist" / "index.js"
    if dist.is_file():
        entries.append((f"{PLUGIN}/dist/index.js", dist))

    # 根级文件
    for name in INCLUDE_FILES:
        p = ROOT / name
        if p.is_file():
            entries.append((f"{PLUGIN}/{name}", p))

    # 后端
    for d, exts in INCLUDE_DIRS:
        dp = ROOT / d
        if not dp.is_dir():
            continue
        for f in sorted(dp.rglob("*")):
            if f.is_file() and f.suffix in exts:
                entries.append((f"{PLUGIN}/{f.relative_to(ROOT)}", f))

    # vendor（离线版）
    if include_vendor:
        v = ROOT / "vendor"
        if v.is_dir():
            for f in sorted(v.rglob("*")):
                if f.is_file():
                    entries.append((f"{PLUGIN}/vendor/{f.relative_to(v)}", f))

    return entries


def build_zip(output: Path, include_vendor: bool) -> bool:
    entries = collect(include_vendor)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        for arc, local in entries:
            zf.write(local, arc)
    with zipfile.ZipFile(output, "r") as zf:
        names = set(zf.namelist())
        missing = [e for e in REQUIRED if e not in names]
        if missing:
            print(f"✗ 缺少: {missing}")
            return False
    size = output.stat().st_size
    unit = f"{size/1048576:.1f} MB" if size > 1048576 else f"{size/1024:.1f} KB"
    print(f"✓ {output.name} ({unit}, {len(entries)} 文件)")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="离线版（含依赖）")
    ap.add_argument("--both", action="store_true", help="同时打包两个版本")
    ap.add_argument("--skip-build", action="store_true", help="跳过前端构建")
    args = ap.parse_args()

    if not args.skip_build:
        if not build_frontend():
            sys.exit(1)

    out = ROOT / "releases"
    out.mkdir(exist_ok=True)
    ok = True

    if args.both or not args.full:
        ok &= build_zip(out / "hoyodeck.zip", include_vendor=False)

    if args.both or args.full:
        v = ROOT / "vendor"
        umu = (v / "umu" / "umu-launcher.tar").is_file()
        proton = any((v / "proton").glob("*.tar.gz"))
        if not umu or not proton:
            print(f"⚠ vendor 不完整: UMU={'✓' if umu else '✗'} Proton={'✓' if proton else '✗'}")
        ok &= build_zip(out / "hoyodeck-full.zip", include_vendor=True)

    if ok:
        print(f"\n📦 产物:")
        for f in sorted(out.glob("*.zip")):
            s = f.stat().st_size / 1048576
            print(f"  {f.name} ({s:.1f} MB)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
