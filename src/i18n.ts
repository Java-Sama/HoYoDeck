/** HoYoDeck 简单国际化 */
const zh: Record<string, string> = {
  // 通用
  appName: "HoYoDeck",
  loading: "加载中...",
  error: "错误",
  success: "成功",
  cancel: "取消",
  confirm: "确认",
  close: "关闭",
  retry: "重试",

  // 仪表盘
  dashboard: "仪表盘",
  compatibilityTools: "兼容层工具",
  runtimeReady: "运行时就绪",
  runtimeNotReady: "运行时未就绪",
  installRuntime: "安装兼容层",
  installingRuntime: "正在安装兼容层...",
  installedGames: "已安装游戏",
  totalGames: "游戏总数",

  // 游戏列表
  gameList: "游戏库",
  cnGames: "国服",
  globalGames: "国际服",
  allGames: "全部",
  noGamesInstalled: "暂无已安装的游戏",

  // 游戏操作
  install: "安装",
  launch: "启动",
  addToSteam: "添加到 Steam",
  removeFromSteam: "从 Steam 移除",
  refreshArtwork: "刷新封面",
  installed: "已安装",
  notInstalled: "未安装",
  partialInstall: "部分安装",
  version: "版本",
  installPath: "安装路径",
  steamShortcut: "Steam 快捷方式",

  // 提示
  confirmAddToSteam: "确定要将此游戏添加到 Steam 库吗？",
  confirmRemoveFromSteam: "确定要从 Steam 库移除此游戏吗？",
  addedToSteam: "已添加到 Steam 库",
  removedFromSteam: "已从 Steam 库移除",
  launchFailed: "启动失败",
  gameNotInstalled: "游戏未安装，请先通过官方启动器安装",
  runtimeRequired: "请先安装兼容层工具",
};

const en: Record<string, string> = {
  appName: "HoYoDeck",
  loading: "Loading...",
  error: "Error",
  success: "Success",
  cancel: "Cancel",
  confirm: "Confirm",
  close: "Close",
  retry: "Retry",
  dashboard: "Dashboard",
  compatibilityTools: "Compatibility Tools",
  runtimeReady: "Runtime Ready",
  runtimeNotReady: "Runtime Not Ready",
  installRuntime: "Install Runtime",
  installingRuntime: "Installing runtime...",
  installedGames: "Installed Games",
  totalGames: "Total Games",
  gameList: "Game Library",
  cnGames: "CN",
  globalGames: "Global",
  allGames: "All",
  noGamesInstalled: "No games installed yet",
  install: "Install",
  launch: "Launch",
  addToSteam: "Add to Steam",
  removeFromSteam: "Remove from Steam",
  refreshArtwork: "Refresh Artwork",
  installed: "Installed",
  notInstalled: "Not Installed",
  partialInstall: "Partial Install",
  version: "Version",
  installPath: "Install Path",
  steamShortcut: "Steam Shortcut",
  confirmAddToSteam: "Add this game to your Steam library?",
  confirmRemoveFromSteam: "Remove this game from your Steam library?",
  addedToSteam: "Added to Steam library",
  removedFromSteam: "Removed from Steam library",
  launchFailed: "Launch failed",
  gameNotInstalled: "Game not installed. Please install via the official launcher first.",
  runtimeRequired: "Please install compatibility tools first.",
};

const isChinese = (() => {
  const lang = document.documentElement.lang || navigator.language || "";
  return lang.includes("zh") || lang.includes("chinese");
})();

const strings = isChinese ? zh : en;

export function t(key: string, vars?: Record<string, string | number>): string {
  let text = strings[key] || zh[key] || key;
  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      text = text.replace(`{${k}}`, String(v));
    }
  }
  return text;
}
