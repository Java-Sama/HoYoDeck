"""
兼容层管理 — UMU 和 Proton 层的检测与安装

组件:
  UMU Runtime   — umu-launcher zipapp，用于在 Linux 上运行 Windows 游戏
  GE-Proton     — GloriousEggroll 的 Proton 构建，兼容性更好

下载策略（中国网络优化）:
  1. ghfast.top 镜像（GitHub 文件加速）
  2. gh-proxy.com 镜像
  3. GitHub 原始链接

SSL 证书:
  SteamOS 的 CA 证书在 /etc/ssl/cert.pem，需手动加载。
"""
from __future__ import annotations

import hashlib
import os
import platform
import re
import shutil
import ssl
import subprocess
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

from .models import RuntimeStatus

# ─── SSL（SteamOS 系统 CA 证书路径） ───────────────────────
SYSTEM_CA_FILES = (
    "/etc/ssl/cert.pem",
    "/etc/ssl/certs/ca-certificates.crt",
    "/etc/pki/tls/certs/ca-bundle.crt",
)


def _ssl_context() -> ssl.SSLContext:
    for candidate in SYSTEM_CA_FILES:
        if Path(candidate).is_file():
            return ssl.create_default_context(cafile=candidate)
    return ssl.create_default_context()


# ─── Proton 匹配 ────────────────────────────────────────────
DWPROTON_PATTERN = re.compile(r"DW-Proton", re.IGNORECASE)
GE_PROTON_PATTERN = re.compile(r"GE-Proton", re.IGNORECASE)
# Proton 版本通过 detect_proton_layers() 动态检测

# ─── 下载地址（中国 CDN 镜像 + GitHub 源站） ────────────────
_UMU_URL = "https://github.com/Open-Wine-Components/umu-launcher/releases/download/1.4.4/umu-launcher-1.4.4-zipapp.tar"
_UMU_GATEWAY = "https://1300823591-fyjwaget5r.ap-guangzhou.tencentscf.com/download/umu"

_ARCH = "aarch64" if platform.machine() == "aarch64" else "x86_64"
_GE_VER = "GE-Proton11-7"
_GE_URL = f"https://github.com/GloriousEggroll/proton-ge-custom/releases/download/{_GE_VER}/{_GE_VER}-{_ARCH}.tar.gz"
_GE_GATEWAY = "https://1300823591-fyjwaget5r.ap-guangzhou.tencentscf.com/download/ge"

# 系统级 umu-run
_SYSTEM_UMU = [
    Path("/usr/bin/umu-run"),
    Path("/usr/local/bin/umu-run"),
    Path.home() / ".local" / "bin" / "umu-run",
]


def _find_system_umu() -> Path | None:
    for p in _SYSTEM_UMU:
        if p.is_file() and os.access(p, os.X_OK):
            return p
    w = shutil.which("umu-run")
    return Path(w) if w else None


def _download_file(urls: list[str], target: Path, timeout: int = 120,
                   max_size: int = 200 * 1024 * 1024,
                   sha256: str | None = None,
                   progress_cb=None) -> bool:
    """下载文件：urllib + 系统 SSL，支持多 URL 回退和 SHA256 校验"""
    for url in urls:
        staged = None
        try:
            request = urllib.request.Request(url, headers={
                "User-Agent": "HoYoDeck/1.0 (+https://github.com/Open-Wine-Components)",
            })
            with urllib.request.urlopen(request, timeout=timeout, context=_ssl_context()) as response:
                declared = int(response.headers.get("Content-Length", "0") or 0)
                if declared > max_size:
                    continue

                fd, tmp = tempfile.mkstemp(prefix=".hoyodeck-dl-", dir=target.parent)
                staged = Path(tmp)
                digest = hashlib.sha256() if sha256 else None
                size = 0

                with os.fdopen(fd, "wb") as f:
                    while chunk := response.read(1024 * 1024):
                        size += len(chunk)
                        if size > max_size:
                            raise RuntimeError("下载文件过大")
                        if digest:
                            digest.update(chunk)
                        f.write(chunk)
                        if progress_cb and declared:
                            progress_cb(size, declared)
                    f.flush()
                    os.fsync(f.fileno())

            if sha256 and digest and digest.hexdigest() != sha256:
                raise RuntimeError("SHA256 校验失败")

            os.replace(staged, target)
            return True
        except Exception:
            # Proton 目录格式不符，跳过
            continue
        finally:
            if staged and staged.exists():
                staged.unlink(missing_ok=True)
    return False


# ─── CompatibilityManager ───────────────────────────────────

class CompatibilityManager:

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.tools_dir = self.data_dir / "tools"
        self.proton_dir = Path.home() / ".local" / "share" / "Steam" / "compatibilitytools.d"
        # vendor 目录（离线版 ZIP）
        self._plugin_dir = Path(__file__).resolve().parent.parent.parent
        self._vendor_dir = self._plugin_dir / "vendor"
        self._progress_cb: Any = None

    def set_progress_callback(self, cb) -> None:
        self._progress_cb = cb

    def _report(self, phase: str, pct: float) -> None:
        if self._progress_cb:
            self._progress_cb(phase, pct)

    @property
    def umu_executable(self) -> Path:
        local = self.tools_dir / "umu-run"
        if local.is_file():
            return local
        s = _find_system_umu()
        return s if s else local

    def detect_proton_layers(self) -> list[dict[str, str]]:
        layers = []
        if not self.proton_dir.is_dir():
            return layers
        for e in sorted(self.proton_dir.iterdir()):
            if e.is_dir() and (e / "proton").is_file() and os.access(e / "proton", os.X_OK):
                layers.append({
                    "name": e.name, "path": str(e),
                    "recommended": bool(DWPROTON_PATTERN.search(e.name) or GE_PROTON_PATTERN.search(e.name)),
                })
        return layers

    def get_status(self) -> RuntimeStatus:
        layers = self.detect_proton_layers()
        ok = self.umu_executable.is_file() or _find_system_umu() is not None
        return RuntimeStatus(umu_installed=ok, umu_path=str(self.umu_executable) if ok else None,
                             proton_layers=layers, ready=ok and len(layers) > 0)

    # ─── UMU 安装（vendor → pacman → 在线下载） ─────────────

    def install_umu(self) -> bool:
        if _find_system_umu():
            return True

        # 1) vendor 离线包
        vendor_tar = self._vendor_dir / "umu" / "umu-launcher.tar"
        if vendor_tar.is_file():
            self._report("从离线包安装 UMU...", 0.3)
            return self._extract_umu_tar(vendor_tar)

        # 2) pacman（SteamOS，需要 root）
        if shutil.which("pacman"):
            try:
                r = subprocess.run(["pacman", "-S", "--noconfirm", "umu-launcher"],
                                   capture_output=True, timeout=120)
                if r.returncode == 0 and _find_system_umu():
                    return True
            except Exception:
                pass

        # 3) 在线下载（中国 CDN 优先，GitHub 备用）
        self.tools_dir.mkdir(parents=True, exist_ok=True)
        target = self.tools_dir / "umu-run"
        if target.is_file():
            return True

        self._report("正在下载 UMU...", 0.1)
        tar_path = self.tools_dir / "umu-launcher.tar"
        if not _download_file([_UMU_GATEWAY, _UMU_URL], tar_path, timeout=120):
            return False

        self._report("正在解压 UMU...", 0.5)
        ok = self._extract_umu_tar(tar_path)
        tar_path.unlink(missing_ok=True)
        return ok

    def _extract_umu_tar(self, tar_path: Path) -> bool:
        self.tools_dir.mkdir(parents=True, exist_ok=True)
        target = self.tools_dir / "umu-run"
        staged = target.with_suffix(".new")
        try:
            with tarfile.open(tar_path, "r:") as bundle:
                member = bundle.getmember("umu/umu-run")
                source = bundle.extractfile(member)
                if source is None:
                    return False
                with staged.open("wb") as dest:
                    while chunk := source.read(1024 * 1024):
                        dest.write(chunk)
                    dest.flush()
                    os.fsync(dest.fileno())
            staged.chmod(0o755)
            os.replace(staged, target)
            return True
        except Exception:
            return False
        finally:
            staged.unlink(missing_ok=True)

    # ─── Proton 安装（vendor → 在线下载） ───────────────────

    def install_proton(self) -> bool:
        if self.detect_proton_layers():
            return True

        self.proton_dir.mkdir(parents=True, exist_ok=True)

        # 1) vendor 离线包
        vendor_tar = next(iter((self._vendor_dir / "proton").glob("*.tar.gz")), None) \
            if (self._vendor_dir / "proton").is_dir() else None
        if vendor_tar and vendor_tar.is_file():
            self._report("从离线包安装 GE-Proton...", 0.3)
            return self._extract_proton_tar(vendor_tar)

        # 2) 在线下载（中国 CDN 优先，GitHub 备用）
        tar_path = self.proton_dir / "ge-proton.tar.gz"

        def on_progress(downloaded, total):
            pct = 0.05 + (downloaded / total) * 0.75
            self._report(f"正在下载 GE-Proton ({downloaded // (1024*1024)}MB/{total // (1024*1024)}MB)", pct)

        self._report("正在下载 GE-Proton...", 0.05)
        if not _download_file([_GE_GATEWAY, _GE_URL], tar_path,
                              timeout=900, max_size=700 * 1024 * 1024,
                              progress_cb=on_progress):
            return False

        self._report("正在解压 GE-Proton...", 0.85)
        ok = self._extract_proton_tar(tar_path)
        tar_path.unlink(missing_ok=True)
        return ok

    def _extract_proton_tar(self, tar_path: Path) -> bool:
        try:
            with tarfile.open(tar_path, "r:*") as bundle:
                members = bundle.getmembers()
                for m in members:
                    p = Path(m.name)
                    if p.is_absolute() or ".." in p.parts:
                        return False
                bundle.extractall(path=self.proton_dir, members=members, filter="fully_trusted")
            if self.detect_proton_layers():
                self._report("GE-Proton 安装完成!", 1.0)
                return True
            return False
        except Exception:
            return False

    # ─── 选择 & 准备 ───────────────────────────────────────

    def selected_proton(self, provider_id: str, game_id: str) -> tuple[str, Path] | None:
        layers = self.detect_proton_layers()
        if not layers:
            return None
        for l in layers:
            if DWPROTON_PATTERN.search(l["name"]):
                return l["name"], Path(l["path"])
        for l in layers:
            if GE_PROTON_PATTERN.search(l["name"]):
                return l["name"], Path(l["path"])
        return layers[0]["name"], Path(layers[0]["path"])

    def prepare(self) -> RuntimeStatus:
        if not self.umu_executable.is_file() and not _find_system_umu():
            if not self.install_umu():
                return self.get_status()
        if not self.detect_proton_layers():
            self.install_proton()
        return self.get_status()
