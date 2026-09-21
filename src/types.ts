/**
 * HoYoDeck 前端类型定义
 *
 * 运行时类型（ShortcutConfig、EnvCheckItem 等）定义在 api.ts 中，
 * 此文件仅定义数据模型类型。
 */

export type RuntimeStatus = {
  umu_installed: boolean;
  umu_path: string | null;
  proton_layers: { name: string; path: string; recommended: boolean }[];
  ready: boolean;
};

export type GameInstallInfo = {
  game_id: string;
  title: string;
  region: string;
  status: "not_installed" | "installed" | "partial" | "update_available" | "unknown";
  installed: boolean;
  install_path: string | null;
  executable: string | null;
  installed_version: string | null;
  steam_app_id: number | null;
  has_steam_shortcut: boolean;
  artwork_url: string | null;
  artwork_urls?: Record<string, string | null>;
};

export type Dashboard = {
  version: string;
  game_count: number;
  installed_count: number;
  runtime: RuntimeStatus;
  games: GameInstallInfo[];
};

export type ShortcutResult = {
  success: boolean;
  app_id?: number;
  error?: string;
};
