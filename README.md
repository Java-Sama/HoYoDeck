<p align="center">
  <h1 align="center">HoYoDeck</h1>
  <p align="center">🎮 Steam Deck 上的米哈游游戏管理器 — Decky Loader 插件</p>
  <p align="center">
    <a href="#安装">安装</a> · <a href="#快速开始">快速开始</a> · <a href="#支持的游戏">支持的游戏</a> · <a href="#从源码构建">从源码构建</a> · <a href="#工作原理">工作原理</a> · <a href="#故障排除">故障排除</a>
  </p>
</p>

---

HoYoDeck 是一款 [Decky Loader](https://decky.xyz/) 插件，让你在 Steam Deck 游戏模式下管理米哈游游戏的完整生命周期：下载官方启动器、安装游戏、添加到 Steam 库、设置封面美术资源，并通过 Proton 兼容层直接启动。

## 功能

- **环境管理** — 自动下载并安装 UMU 运行时和 GE-Proton 兼容层，带下载进度条
- **启动器管理** — 在插件内完成官方启动器的下载、安装、启动（国服/国际服 Switch 切换）
- **游戏检测** — 扫描 Wine 注册表，自动发现已安装的米哈游游戏
- **Steam 集成** — 一键创建非 Steam 快捷方式，自动下载并设置封面、横幅、Logo
- **直接启动** — 从 Decky 面板直接通过 Proton 启动游戏，无需切到桌面模式
- **环境清理** — 一键移除插件环境，或移除环境 + 游戏 + Steam 快捷方式
- **中英双语** — 界面自动跟随系统语言切换

## 支持的游戏

| 游戏 | 国服 | 国际服 |
|:-----|:----:|:------:|
| 原神 Genshin Impact | ✅ | ✅ |
| 崩坏：星穹铁道 Honkai: Star Rail | ✅ | ✅ |
| 绝区零 Zenless Zone Zero | ✅ | ✅ |
| 崩坏3 Honkai Impact 3rd | ✅ | ✅ |

> **注意**：米哈游游戏没有官方 Linux / SteamOS 支持。HoYoDeck 不会绕过反作弊、DRM 或地区限制，使用风险自负。

## 前置条件

- Steam Deck（SteamOS 3.x）
- [Decky Loader](https://decky.xyz/) 已安装并运行
- 网络连接（首次使用需下载运行时和启动器）

## 安装

### 方式一：从 Release 安装（推荐）

1. 前往 [Releases](../../releases) 页面下载最新的 `hoyodeck.zip`
2. 在 Steam Deck 的游戏模式下，打开 Decky Loader 侧边栏
3. 点击齿轮图标 → **开发者** → **从 ZIP 安装插件**
4. 选择下载的 `hoyodeck.zip`
5. 安装完成后 Decky Loader 会自动加载插件

### 方式二：从源码构建

```bash
git clone https://github.com/Java-Sama/HoYoDeck.git
cd HoYoDeck

# 安装前端依赖
pnpm install

# 构建前端 + 打包 ZIP
python3 scripts/build_plugin_zip.py

# 产物在 releases/hoyodeck.zip
```

然后按方式一的步骤 2-5 安装。

## 快速开始

### 第一步：安装运行时

打开 HoYoDeck 面板，展开「环境检查」：

1. **UMU Runtime** — 点击「安装」，自动下载 umu-launcher
2. **Proton 兼容层** — 点击「安装」，自动下载 GE-Proton（~540MB，有进度条）
3. **官方启动器** — 使用 Switch 切换国服/国际服：
   - 点击「下载」→ 自动下载官方安装包（有进度条）
   - 下载完成后点击「安装」→ 通过 Steam 启动安装器，按提示完成安装
   - 安装完成后按钮变为「打开」

### 第二步：安装游戏

切换到游戏列表，选择国服/国际服：

1. 点击游戏卡片上的「安装」→ 自动打开官方启动器
2. 在启动器中下载游戏
3. 下载完成后回到 HoYoDeck，游戏状态自动更新为「已安装」

### 第三步：启动游戏

- **方式 A**：在 HoYoDeck 中点击游戏卡片上的「启动」
- **方式 B**：点击「添加到 Steam」，然后在 Steam 库中启动

两种方式都通过 Proton 兼容层运行，无需切到桌面模式。

## 面板功能

| 区域 | 功能 |
|:-----|:-----|
| 环境检查（可折叠） | UMU、Proton、启动器状态；下载/安装/打开；Switch 切换国服/国际服 |
| 游戏统计 | 已安装游戏数 / 总游戏数 |
| 游戏列表 | 国服/国际服分段切换，网格布局的游戏卡片 |
| 游戏卡片 | 启动、安装、添加/移除 Steam 快捷方式、刷新封面 |
| 清理按钮 | 移除插件环境 / 移除环境 + 游戏 |

## 项目结构

```
HoYoDeck/
├── main.py                        # Decky 插件主入口（Python RPC 服务）
├── backend/
│   ├── launcher.py                # Steam 快捷方式调用的启动脚本
│   └── hoyodeck/                  # 后端核心包
│       ├── models.py              # 数据模型（GameInfo、Dashboard 等）
│       ├── games.py               # 游戏注册表（8 款游戏 + 启动器配置）
│       ├── detector.py            # Wine 注册表扫描、游戏安装检测
│       ├── compatibility.py       # UMU / Proton 兼容层管理（含中国镜像）
│       ├── launcher.py            # 游戏启动流程、Steam 快捷方式配置生成
│       ├── steam_shortcuts.py     # Steam shortcuts.vdf 二进制读写
│       └── artwork.py             # 封面美术资源下载与安装
├── src/                           # 前端源码（TypeScript + React）
│   ├── index.tsx                  # 插件入口
│   ├── api.ts                     # 后端 RPC 封装 + Steam 快捷方式启动
│   ├── types.ts                   # TypeScript 类型定义
│   ├── i18n.ts                    # 中英双语国际化
│   └── components/
│       ├── Dashboard.tsx          # 仪表盘（环境检查 + 游戏统计 + 清理）
│       ├── GameList.tsx           # 游戏网格列表
│       └── GameCard.tsx           # 单个游戏卡片
├── scripts/
│   └── build_plugin_zip.py        # 打包脚本
├── plugin.json                    # Decky 插件元数据
├── package.json                   # npm 依赖
├── tsconfig.json                  # TypeScript 配置
└── rollup.config.js               # Rollup 构建配置
```

## 工作原理

HoYoDeck 使用类似 [GameBridge](https://github.com/FelPikachu/GameBridge) 的架构，通过 Python 脚本桥接 Steam 和 Proton：

```
Steam 非Steam快捷方式
  exe: /usr/bin/python3                    ← 原生 Linux，不走 Proton
  args: "backend/launcher.py" --provider cn --game-id installer
        ↓
  launcher.py（Python 脚本）
  ├─ 设置环境变量:
  │   WINEPREFIX=~/.local/share/hoyodeck/prefixes/mihoyo-cn
  │   PROTONPATH=~/.local/share/Steam/compatibilitytools.d/GE-Proton11-7
  │   GAMEID=umu-default
  │   LANG=zh_CN.UTF-8
  │
  └─ subprocess.run(["umu-run", "game.exe"])
        ↓
  UMU Launcher
  ├─ 自动找到 Proton/Wine
  ├─ 初始化 Wine 前缀
  └─ 以正确的兼容层运行 Windows 程序
```

**核心组件：**

| 组件 | 作用 |
|:-----|:-----|
| **UMU Launcher** | Wine/Proton 统一启动器，自动处理环境配置 |
| **GE-Proton** | 社区 Proton 构建，兼容性好 |
| **launcher.py** | Steam 快捷方式入口，设置 Wine 环境并调用 umu-run |
| **shortcuts.vdf** | Steam 的二进制快捷方式配置文件 |

**数据目录：** `~/.local/share/hoyodeck/`

```
hoyodeck/
├── tools/              # UMU 可执行文件
├── prefixes/           # Wine 前缀（每个启动器独立）
│   ├── mihoyo-cn/      # 国服前缀
│   └── hoyoplay-global/ # 国际服前缀
└── installers/         # 下载的官方安装包
```

## 从源码构建

```bash
# 克隆仓库
git clone https://github.com/Java-Sama/HoYoDeck.git
cd HoYoDeck

# 安装依赖
pnpm install

# 构建（自动编译 TypeScript + 打包 ZIP）
python3 scripts/build_plugin_zip.py

# 产物:
#   releases/hoyodeck.zip       — 在线版（需联网下载运行时）
#   releases/hoyodeck-full.zip  — 离线版（含 GE-Proton，~540MB）

# 开发模式：构建并部署到本机
pnpm run build
cp dist/index.js /home/deck/homebrew/plugins/hoyodeck/dist/
cp main.py /home/deck/homebrew/plugins/hoyodeck/
cp -r backend/ /home/deck/homebrew/plugins/hoyodeck/
sudo systemctl restart plugin_loader   # 重启 Decky 加载插件
```

## 推荐的 Proton 版本

| Proton 版本 | 说明 |
|:------------|:-----|
| **DW-Proton** | 专门为米哈游游戏优化，推荐首选 |
| **GE-Proton** | 通用社区兼容层，HoYoDeck 自动下载此版本 |

## 故障排除

### 环境检查显示未就绪

- 点击各项的「安装」按钮，HoYoDeck 会自动下载所需组件
- 如果下载失败，检查网络连接；在中国大陆可能需要代理

### 启动器下载后闪退

- 首次安装时 Wine 前缀初始化需要 1-2 分钟，请耐心等待
- 确保 UMU 和 Proton 都已安装（环境检查全绿）

### 游戏无法启动

- 确认兼容层已就绪（环境检查中 UMU 和 Proton 显示 ✓）
- 确认启动器已安装且游戏已下载完成
- 尝试通过「打开」按钮先启动启动器确认其正常工作

### 封面不显示

- 点击游戏卡片上的「刷新封面」按钮
- 确认网络连接正常（封面从 CDN 下载）

### 重置环境

在面板底部有两个清理按钮：

- **移除插件环境** — 删除 UMU、Proton、Wine 前缀和安装包
- **移除环境 + 游戏** — 删除所有数据并移除 HoYoDeck 创建的 Steam 快捷方式

或手动操作：

```bash
# 完全重置
rm -rf ~/.local/share/hoyodeck/
```

## 反馈与贡献

- 🐛 Bug 报告：[Issues](../../issues)
- 💡 功能建议：[Discussions](../../discussions)
- 🔧 Pull Requests 欢迎

提交 Issue 时请尽量提供：
- HoYoDeck 版本
- SteamOS 版本
- 游戏名称和区域（国服 / 国际服）
- 问题复现步骤
- 相关日志（`journalctl -u plugin_loader --no-pager -n 50`）

## 致谢

- [Decky Loader](https://decky.xyz/) — Steam Deck 插件框架
- [UMU Launcher](https://github.com/Open-Wine-Components/umu-launcher) — Wine/Proton 统一启动器
- [GE-Proton](https://github.com/GloriousEggroll/proton-ge-custom) — 社区 Proton 构建
- [DW-Proton](https://github.com/InoriRyacom/DW-Proton) — 米哈游游戏专用 Proton 构建
- [GameBridge](https://github.com/FelPikachu/GameBridge) — 本项目的架构参考

## 许可证

[MIT License](LICENSE)

---

<p align="center">
  <sub>Made with ❤️ for Steam Deck & miHoYo gamers</sub>
</p>
