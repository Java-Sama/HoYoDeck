/**
 * HoYoDeck 后端 RPC 调用封装
 *
 * 所有函数通过 Decky 的 call() 与 Python 后端通信。
 * 后端方法定义在 main.py 的 Plugin 类中。
 */
import { call } from "@decky/api";
import type { Dashboard, GameInstallInfo, ShortcutResult, RuntimeStatus } from "./types";

// ─── 基础 API ─────────────────────────────────────────────

export async function getDashboard(): Promise<Dashboard> {
  return await call<[], Dashboard>("get_dashboard");
}

export async function getRuntimeStatus(): Promise<RuntimeStatus> {
  return await call<[], RuntimeStatus>("get_runtime_status");
}

export async function prepareCompatibility(): Promise<RuntimeStatus | { error: string }> {
  return await call<[], RuntimeStatus | { error: string }>("prepare_compatibility");
}

export async function getGames(): Promise<GameInstallInfo[]> {
  return await call<[], GameInstallInfo[]>("get_games");
}

export async function getGameDetails(gameId: string): Promise<GameInstallInfo> {
  return await call<[string], GameInstallInfo>("get_game_details", gameId);
}

export async function refreshGameStatus(gameId: string): Promise<GameInstallInfo> {
  return await call<[string], GameInstallInfo>("refresh_game_status", gameId);
}

export async function addToSteam(gameId: string): Promise<ShortcutResult> {
  return await call<[string], ShortcutResult>("add_to_steam", gameId);
}

export async function removeFromSteam(gameId: string): Promise<ShortcutResult> {
  return await call<[string], ShortcutResult>("remove_from_steam", gameId);
}

export async function refreshArtwork(gameId: string): Promise<{ success: boolean; installed?: Record<string, boolean>; error?: string }> {
  return await call<[string], { success: boolean; installed?: Record<string, boolean>; error?: string }>("refresh_artwork", gameId);
}

// ─── 启动配置（后端返回快捷方式参数） ─────────────────────

export type ShortcutConfig = {
  success: boolean;
  error?: string;
  game_id?: string;
  title?: string;
  exe: string;
  start_dir: string;
  launch_args: string;
  proton_tool: string;
  prefix: string;
  executable?: string;
  temporary?: boolean;
};

export async function launchGame(gameId: string): Promise<ShortcutConfig> {
  return await call<[string], ShortcutConfig>("launch_game", gameId);
}

export async function launchInstaller(region: string): Promise<ShortcutConfig> {
  return await call<[string], ShortcutConfig>("launch_installer", region);
}

// ─── 通过 Steam 非Steam快捷方式启动 ──────────────────────

// Steam 快捷方式的入口参数
// exe 是原生 Linux Python，不走 Proton；launcher.py 内部用 umu-run 启动游戏/安装器
const ENTRY_POINT = "/usr/bin/python3";
const PLUGIN_DIR = "/home/deck/homebrew/plugins/hoyodeck";

/**
 * 通过 Steam 快捷方式启动 HoYoDeck launcher.py（GameBridge 方式）
 * exe 是原生 Linux Python，不走 Proton；launcher.py 内部用 umu-run 启动游戏/安装器
 */
export async function launchViaScript(
  provider: "cn" | "global",
  gameId: string,
  label: string,
  temporary: boolean = false,
): Promise<{ success: boolean; error?: string }> {
  const apps = (window as any).SteamClient?.Apps;
  if (!apps?.AddShortcut) {
    return { success: false, error: "Steam API 不可用" };
  }

  const launchOptions = `"backend/launcher.py" --provider ${provider} --game-id ${gameId}`;

  try {
    // 1. 创建快捷方式（exe 是 Python，不走 Proton）
    const appId = await apps.AddShortcut(
      label,
      ENTRY_POINT,
      PLUGIN_DIR,
      launchOptions,
    );
    if (!appId) return { success: false, error: "创建快捷方式失败" };

    // 2. 设置属性
    apps.SetShortcutName(appId, label);
    apps.SetShortcutExe(appId, ENTRY_POINT);
    if (typeof apps.SetShortcutStartDir === "function") {
      apps.SetShortcutStartDir(appId, PLUGIN_DIR);
    }
    if (typeof apps.SetShortcutLaunchOptions === "function") {
      apps.SetShortcutLaunchOptions(appId, launchOptions);
    }
    // 不指定 Proton — Python 是原生 Linux 程序

    // 3. 等待就绪
    await new Promise((r) => setTimeout(r, 1500));

    // 4. 启动
    if (typeof apps.RunGame !== "function") {
      return { success: false, error: "Steam RunGame API 不可用" };
    }
    const overview = (window as any).appStore?.GetAppOverviewByAppID?.(appId);
    const runId = overview?.gameid || ((BigInt(appId) << 32n) | 0x02000000n).toString();
    await apps.RunGame(runId, "", -1, 100);

    // 5. 临时快捷方式：游戏退出后自动清理
    if (temporary) {
      let cleaned = false;
      const cleanup = () => {
        if (cleaned) return;
        cleaned = true;
        try { apps.RemoveShortcut?.(appId); } catch (_) {}
      };
      setTimeout(cleanup, 30 * 60 * 1000); // 30 分钟超时
      try {
        (window as any).SteamClient?.GameSessions?.RegisterForAppLifetimeNotifications?.(
          (event: any) => { if (event.unAppID === appId && !event.bRunning) cleanup(); }
        );
      } catch (_) {}
    }

    return { success: true };
  } catch (e) {
    return { success: false, error: String(e) };
  }
}

/**
 * 创建临时 Steam 快捷方式并通过 Steam 启动（用于已安装的启动器/游戏）
 * Steam 自动管理 Proton 兼容层和进程生命周期
 */
export async function launchThroughSteam(config: ShortcutConfig): Promise<{ success: boolean; error?: string }> {
  const apps = (window as any).SteamClient?.Apps;
  if (!apps?.AddShortcut) {
    return { success: false, error: "Steam API 不可用" };
  }

  try {
    // 1. 创建非Steam快捷方式
    const appId = await apps.AddShortcut(
      config.title || "HoYoDeck",
      config.exe,
      config.start_dir,
      config.launch_args,
    );
    if (!appId) return { success: false, error: "创建快捷方式失败" };

    // 2. 设置名称
    apps.SetShortcutName(appId, config.title || "HoYoDeck");

    // 3. 设置启动参数
    if (typeof apps.SetShortcutLaunchOptions === "function") {
      apps.SetShortcutLaunchOptions(appId, config.launch_args);
    }

    // 4. 指定 Proton 兼容层
    if (config.proton_tool && typeof apps.SpecifyCompatTool === "function") {
      apps.SpecifyCompatTool(appId, config.proton_tool);
    }

    // 5. 等待快捷方式就绪
    await new Promise((r) => setTimeout(r, 1500));

    // 6. 通过 Steam 启动
    if (typeof apps.RunGame === "function") {
      const overview = (window as any).appStore?.GetAppOverviewByAppID?.(appId);
      const gameId = overview?.gameid || ((BigInt(appId) << 32n) | 0x02000000n).toString();
      await apps.RunGame(gameId, "", -1, 100);

      // 7. 临时快捷方式：监听退出后自动清理
      if (config.temporary) {
        let cleaned = false;
        const cleanup = () => {
          if (cleaned) return;
          cleaned = true;
          try { apps.RemoveShortcut?.(appId); } catch (_) {}
        };
        setTimeout(cleanup, 10 * 60 * 1000);
        try {
          (window as any).SteamClient?.GameSessions?.RegisterForAppLifetimeNotifications?.(
            (event: any) => { if (event.unAppID === appId && !event.bRunning) cleanup(); }
          );
        } catch (_) {}
      }
    }

    return { success: true };
  } catch (e) {
    return { success: false, error: String(e) };
  }
}

// ─── 环境检查 ──────────────────────────────────────────────

export type EnvCheckItem = {
  name: string;
  ready: boolean;
  detail: string;
  count?: number;
};

export type EnvCheckResult = {
  umu: EnvCheckItem;
  proton: EnvCheckItem;
  launcher_cn: EnvCheckItem;
  launcher_global: EnvCheckItem;
  steam_compat_dir: EnvCheckItem;
};

export async function checkEnvironment(): Promise<EnvCheckResult> {
  return await call<[], EnvCheckResult>("check_environment");
}

export async function installComponent(component: string): Promise<{ success: boolean; detail: string }> {
  return await call<[string], { success: boolean; detail: string }>("install_component", component);
}

export async function getDownloadProgress(component: string): Promise<{ pct: number; downloaded_mb: number; total_mb: number; status: string; error?: string }> {
  return await call<[string], { pct: number; downloaded_mb: number; total_mb: number; status: string; error?: string }>("get_download_progress", component);
}

export async function cleanupEnvironment(): Promise<{ success: boolean; removed: string[]; detail: string }> {
  return await call<[], { success: boolean; removed: string[]; detail: string }>("cleanup_environment");
}

export async function cleanupAll(): Promise<{ success: boolean; removed_shortcuts: string[]; detail: string }> {
  return await call<[], { success: boolean; removed_shortcuts: string[]; detail: string }>("cleanup_all");
}
